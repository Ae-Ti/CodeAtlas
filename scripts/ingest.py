#!/usr/bin/env python3
"""
논문·코드 데이터 적재기 — JSON 한 파일을 Script-2 스키마에 맞게 넣어줍니다.

A의 Python 파이프라인은 이 JSON만 만들면 되고, FK 순서·JSONB·CHECK 제약·UNIQUE 키를
직접 신경 쓸 필요가 없습니다.

    python3 scripts/ingest.py database/ingest_example.json
    python3 scripts/ingest.py out.json --dry-run     # 검증만 하고 DB는 건드리지 않음
    python3 scripts/ingest.py out.json --print-sql   # 생성될 SQL을 눈으로 확인

추가 패키지가 필요 없습니다 (docker exec psql 사용).

── 입력 형식 (database/ingest_example.json 참고)
{
  "papers": [{
    "arxivId": "1706.03762",           // 필수 — 재적재 시 이 값으로 upsert
    "title": "...",                     // 필수
    "abstract": "...", "pdfUrl": "...", "publishedDate": "2017-06-12",
    "authors": ["Ashish Vaswani", ...],
    "chunks": [{
      "chunkIndex": 0,                  // 필수, 논문 안에서 0부터 순서대로
      "content": "...",                 // 필수
      "sectionTitle": "...", "subsectionTitle": null,
      "pageStart": 4, "pageEnd": 5, "tokenCount": 96
    }],
    "repositories": [{
      "githubUrl": "https://github.com/...",   // 필수 — 이 값으로 upsert
      "repositoryName": "...",                 // 필수
      "ownerName": "...", "defaultBranch": "main", "licenseName": "MIT",
      "primaryLanguage": "Python", "starCount": 6200,
      "relationType": "COMMUNITY", "isPrimary": true,
      "codeBlocks": [{
        "filePath": "...",              // 필수
        "symbolType": "METHOD",         // 필수 — FILE/CLASS/FUNCTION/METHOD/MODULE
        "codeContent": "...",           // 필수
        "symbolName": "forward", "parentSymbolName": "MultiHeadedAttention",
        "programmingLanguage": "Python", "startLine": 42, "endLine": 89
      }]
    }]
  }]
}

embedding은 넣지 않습니다. 적재 후 백엔드를 backfill 모드로 한 번 띄우면
B의 검색 코드와 동일한 방식으로 채워집니다.

    cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
"""
import argparse
import json
import subprocess
import sys

SYMBOL_TYPES = {'FILE', 'CLASS', 'FUNCTION', 'METHOD', 'MODULE'}
RELATION_TYPES = {'OFFICIAL', 'AUTHOR', 'COMMUNITY', 'REFERENCE'}


# ── SQL 리터럴 생성 ────────────────────────────────────────────
def lit(value):
    """
    문자열은 dollar-quoting으로 감쌉니다. 코드 본문에는 따옴표·백슬래시가 마구 들어 있어서
    일반 '' 이스케이프는 실수하기 쉽습니다. 내용에 태그가 이미 있으면 겹치지 않는 태그를 찾습니다.
    """
    if value is None or value == '':
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)

    text = str(value)
    tag = 'ca'
    n = 0
    while f'${tag}$' in text:
        n += 1
        tag = f'ca{n}'
    return f'${tag}${text}${tag}$'


def authors_jsonb(authors):
    """['이름', ...] → JSONB 배열 [{"name": "이름"}, ...] (Script-2의 authors 형식)"""
    payload = json.dumps([{'name': a} for a in (authors or [])], ensure_ascii=False)
    return f'{lit(payload)}::jsonb'


def date_lit(value):
    return 'NULL' if not value else f'DATE {lit(value)}'


# ── 검증 ──────────────────────────────────────────────────────
def validate(doc):
    """DB에 넣기 전에 잡을 수 있는 오류를 전부 모아서 한 번에 보고합니다."""
    errors = []
    papers = doc.get('papers')
    if not isinstance(papers, list) or not papers:
        return ['최상위에 papers 배열이 필요합니다.']

    seen_arxiv, seen_repo = set(), set()

    for pi, p in enumerate(papers):
        where = f'papers[{pi}]'
        arxiv = p.get('arxivId')
        if not arxiv:
            errors.append(f'{where}: arxivId 가 필요합니다 (재적재 시 upsert 키로 씁니다).')
        elif arxiv in seen_arxiv:
            errors.append(f'{where}: arxivId 중복 — {arxiv}')
        else:
            seen_arxiv.add(arxiv)
        if not p.get('title'):
            errors.append(f'{where}: title 이 필요합니다.')

        indexes = set()
        for ci, c in enumerate(p.get('chunks') or []):
            cw = f'{where}.chunks[{ci}]'
            if c.get('chunkIndex') is None:
                errors.append(f'{cw}: chunkIndex 가 필요합니다.')
            elif c['chunkIndex'] in indexes:
                errors.append(f'{cw}: chunkIndex 중복 — {c["chunkIndex"]} '
                              f'(uq_paper_chunks_order 위반)')
            else:
                indexes.add(c['chunkIndex'])
            if not c.get('content'):
                errors.append(f'{cw}: content 가 필요합니다.')
            ps, pe = c.get('pageStart'), c.get('pageEnd')
            if ps is not None and pe is not None and pe < ps:
                errors.append(f'{cw}: pageEnd({pe}) < pageStart({ps}) — ck_paper_chunks_page 위반')

        for ri, r in enumerate(p.get('repositories') or []):
            rw = f'{where}.repositories[{ri}]'
            url = r.get('githubUrl')
            if not url:
                errors.append(f'{rw}: githubUrl 이 필요합니다 (upsert 키).')
            elif url in seen_repo and r.get('_shared') is not True:
                # 같은 repo를 여러 논문이 참조하는 건 정상 — 경고만 남기지 않고 통과시킵니다
                pass
            else:
                seen_repo.add(url)
            if not r.get('repositoryName'):
                errors.append(f'{rw}: repositoryName 이 필요합니다.')
            if r.get('starCount') is not None and r['starCount'] < 0:
                errors.append(f'{rw}: starCount 는 0 이상이어야 합니다 (ck_repositories_star_count).')
            rel = r.get('relationType', 'COMMUNITY')
            if rel not in RELATION_TYPES:
                errors.append(f'{rw}: relationType 은 {sorted(RELATION_TYPES)} 중 하나 — 받은 값 {rel!r}')

            locations = set()
            for bi, b in enumerate(r.get('codeBlocks') or []):
                bw = f'{rw}.codeBlocks[{bi}]'
                if not b.get('filePath'):
                    errors.append(f'{bw}: filePath 가 필요합니다.')
                if not b.get('codeContent'):
                    errors.append(f'{bw}: codeContent 가 필요합니다.')
                st = b.get('symbolType')
                if st not in SYMBOL_TYPES:
                    errors.append(f'{bw}: symbolType 은 {sorted(SYMBOL_TYPES)} 중 하나 — 받은 값 {st!r}')
                sl, el = b.get('startLine'), b.get('endLine')
                if sl is not None and el is not None and el < sl:
                    errors.append(f'{bw}: endLine({el}) < startLine({sl}) — ck_code_blocks_lines 위반')
                key = (b.get('filePath'), b.get('symbolName'), sl)
                if key in locations:
                    errors.append(f'{bw}: 같은 (filePath, symbolName, startLine) 중복 '
                                  f'— uq_code_blocks_location 위반: {key}')
                locations.add(key)

    return errors


# ── SQL 생성 ──────────────────────────────────────────────────
def build_sql(doc):
    out = ['BEGIN;']

    for p in doc['papers']:
        arxiv = lit(p['arxivId'])
        out.append(f"""
-- ── {p['title'][:70]}
INSERT INTO papers (title, abstract, arxiv_id, doi, pdf_url, source_url, published_date, authors, processing_status)
VALUES ({lit(p['title'])}, {lit(p.get('abstract'))}, {arxiv}, {lit(p.get('doi'))},
        {lit(p.get('pdfUrl'))}, {lit(p.get('sourceUrl'))}, {date_lit(p.get('publishedDate'))},
        {authors_jsonb(p.get('authors'))}, {lit(p.get('processingStatus', 'COMPLETED'))})
ON CONFLICT (arxiv_id) DO UPDATE SET
    title = EXCLUDED.title, abstract = EXCLUDED.abstract, pdf_url = EXCLUDED.pdf_url,
    published_date = EXCLUDED.published_date, authors = EXCLUDED.authors,
    processing_status = EXCLUDED.processing_status, updated_at = CURRENT_TIMESTAMP;""")

        paper_id = f'(SELECT id FROM papers WHERE arxiv_id = {arxiv})'

        for c in p.get('chunks') or []:
            out.append(f"""
INSERT INTO paper_chunks (paper_id, section_title, subsection_title, chunk_index, content, page_start, page_end, token_count)
VALUES ({paper_id}, {lit(c.get('sectionTitle'))}, {lit(c.get('subsectionTitle'))},
        {c['chunkIndex']}, {lit(c['content'])},
        {lit(c.get('pageStart'))}, {lit(c.get('pageEnd'))}, {lit(c.get('tokenCount'))})
ON CONFLICT (paper_id, chunk_index) DO UPDATE SET
    section_title = EXCLUDED.section_title, subsection_title = EXCLUDED.subsection_title,
    content = EXCLUDED.content, page_start = EXCLUDED.page_start,
    page_end = EXCLUDED.page_end, token_count = EXCLUDED.token_count,
    -- 본문이 바뀌면 기존 embedding은 무효 → 비워서 backfill 대상으로 되돌림
    embedding = CASE WHEN paper_chunks.content IS DISTINCT FROM EXCLUDED.content
                     THEN NULL ELSE paper_chunks.embedding END;""")

        for r in p.get('repositories') or []:
            url = lit(r['githubUrl'])
            out.append(f"""
INSERT INTO repositories (github_url, owner_name, repository_name, default_branch, commit_hash,
                          license_name, primary_language, star_count, processing_status)
VALUES ({url}, {lit(r.get('ownerName'))}, {lit(r['repositoryName'])}, {lit(r.get('defaultBranch'))},
        {lit(r.get('commitHash'))}, {lit(r.get('licenseName'))}, {lit(r.get('primaryLanguage'))},
        {r.get('starCount') or 0}, {lit(r.get('processingStatus', 'COMPLETED'))})
ON CONFLICT (github_url) DO UPDATE SET
    owner_name = EXCLUDED.owner_name, repository_name = EXCLUDED.repository_name,
    default_branch = EXCLUDED.default_branch, license_name = EXCLUDED.license_name,
    primary_language = EXCLUDED.primary_language, star_count = EXCLUDED.star_count,
    processing_status = EXCLUDED.processing_status, updated_at = CURRENT_TIMESTAMP;

INSERT INTO paper_repositories (paper_id, repository_id, relation_type, is_primary)
VALUES ({paper_id}, (SELECT id FROM repositories WHERE github_url = {url}),
        {lit(r.get('relationType', 'COMMUNITY'))}, {lit(bool(r.get('isPrimary', False)))})
ON CONFLICT (paper_id, repository_id) DO UPDATE SET
    relation_type = EXCLUDED.relation_type, is_primary = EXCLUDED.is_primary;""")

            repo_id = f'(SELECT id FROM repositories WHERE github_url = {url})'
            for b in r.get('codeBlocks') or []:
                out.append(f"""
INSERT INTO code_blocks (repository_id, file_path, symbol_name, symbol_type, programming_language,
                         start_line, end_line, code_content, parent_symbol_name)
VALUES ({repo_id}, {lit(b['filePath'])}, {lit(b.get('symbolName'))}, {lit(b['symbolType'])},
        {lit(b.get('programmingLanguage'))}, {lit(b.get('startLine'))}, {lit(b.get('endLine'))},
        {lit(b['codeContent'])}, {lit(b.get('parentSymbolName'))})
ON CONFLICT (repository_id, file_path, symbol_name, start_line) DO UPDATE SET
    symbol_type = EXCLUDED.symbol_type, programming_language = EXCLUDED.programming_language,
    end_line = EXCLUDED.end_line, code_content = EXCLUDED.code_content,
    parent_symbol_name = EXCLUDED.parent_symbol_name,
    embedding = CASE WHEN code_blocks.code_content IS DISTINCT FROM EXCLUDED.code_content
                     THEN NULL ELSE code_blocks.embedding END;""")

    out.append('\nCOMMIT;')
    return '\n'.join(out)


def psql(container, db, user, sql, tuples_only=False):
    cmd = ['docker', 'exec', '-i', container, 'psql', '-U', user, '-d', db, '-v', 'ON_ERROR_STOP=1', '-q']
    if tuples_only:
        # -tA: 헤더/정렬 없이 값만 — 결과를 그대로 출력할 때 사용
        cmd += ['-tA']
    return subprocess.run(cmd, input=sql, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description='CodeAtlas 논문·코드 데이터 적재기')
    parser.add_argument('json_file', help='적재할 JSON 파일')
    parser.add_argument('--dry-run', action='store_true', help='검증만 하고 DB는 건드리지 않음')
    parser.add_argument('--print-sql', action='store_true', help='생성된 SQL을 출력')
    parser.add_argument('--container', default='codeatlas-postgres')
    parser.add_argument('--db', default='codeatlas')
    parser.add_argument('--user', default='codeatlas')
    args = parser.parse_args()

    with open(args.json_file, encoding='utf-8') as f:
        doc = json.load(f)

    errors = validate(doc)
    if errors:
        print(f'❌ 검증 실패 — {len(errors)}건\n', file=sys.stderr)
        for e in errors:
            print(f'  · {e}', file=sys.stderr)
        sys.exit(1)

    papers = doc['papers']
    chunks = sum(len(p.get('chunks') or []) for p in papers)
    repos = sum(len(p.get('repositories') or []) for p in papers)
    blocks = sum(len(b.get('codeBlocks') or [])
                 for p in papers for b in (p.get('repositories') or []))
    print(f'✅ 검증 통과 — 논문 {len(papers)} / chunk {chunks} / repo {repos} / code_block {blocks}')

    sql = build_sql(doc)
    if args.print_sql:
        print(sql)
    if args.dry_run:
        print('   --dry-run 이라 DB에는 쓰지 않았습니다.')
        return

    result = psql(args.container, args.db, args.user, sql)
    if result.returncode != 0:
        print(f'\n❌ 적재 실패\n{result.stderr}', file=sys.stderr)
        sys.exit(1)

    summary = psql(args.container, args.db, args.user, """
SELECT '  DB 총계: papers ' || (SELECT count(*) FROM papers)
    || ' / chunks ' || (SELECT count(*) FROM paper_chunks)
    || ' / repos ' || (SELECT count(*) FROM repositories)
    || ' / code_blocks ' || (SELECT count(*) FROM code_blocks)
UNION ALL
SELECT '  embedding 미완료: chunk ' || (SELECT count(*) FROM paper_chunks WHERE embedding IS NULL)
    || ' / code_block ' || (SELECT count(*) FROM code_blocks WHERE embedding IS NULL);
""", tuples_only=True)
    print('✅ 적재 완료')
    print(summary.stdout.rstrip())
    print('\n다음 단계: 임베딩 채우기')
    print('  cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run')


if __name__ == '__main__':
    main()
