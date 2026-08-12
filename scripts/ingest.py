#!/usr/bin/env python3
"""
논문·코드 데이터 적재기 — JSON 한 파일을 Script-2 스키마에 맞게 넣어줍니다.

A의 Python 파이프라인은 이 JSON만 만들면 되고, FK 순서·JSONB·CHECK 제약·UNIQUE 키를
직접 신경 쓸 필요가 없습니다.

    python3 scripts/ingest.py database/ingest_example.json
    python3 scripts/ingest.py out.json --dry-run     # 검증만 하고 DB는 건드리지 않음
    python3 scripts/ingest.py out.json --print-sql   # 생성될 SQL을 눈으로 확인

    # 노트에서 분류한 단락↔코드를 함께 저장하고 정답셋까지 만들기
    python3 scripts/ingest.py out.json --insert-mappings --eval-csv database/eval_set.csv

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
      "pageStart": 4, "pageEnd": 5, "tokenCount": 96,

      // 선택 — 노트에서 이 단락에 분류해둔 코드. 맨 앞이 Top-1 정답.
      // codeBlocks에 정의된 코드를 (githubUrl, filePath, symbolName, startLine)로 가리킵니다.
      "mappedCode": [
        { "githubUrl": "...", "filePath": "...", "symbolName": "forward", "startLine": 42,
          "reason": "왜 이 코드인지 한 줄" }
      ]
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
        # 이 논문 안에서 정의된 코드 블록의 자연키 — mappedCode가 이 안을 가리키는지 확인용
        defined_blocks = {
            (r.get('githubUrl'), b.get('filePath'), b.get('symbolName'), b.get('startLine'))
            for r in (p.get('repositories') or [])
            for b in (r.get('codeBlocks') or [])
        }

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

            # 수동 분류(단락 ↔ 코드)는 같은 파일 안에 정의된 코드 블록만 가리킬 수 있습니다.
            # 오타로 엉뚱한 곳을 가리키면 조용히 매핑이 사라지므로 여기서 잡습니다.
            for mi, m in enumerate(c.get('mappedCode') or []):
                mw = f'{cw}.mappedCode[{mi}]'
                key = (m.get('githubUrl'), m.get('filePath'), m.get('symbolName'), m.get('startLine'))
                if None in (key[0], key[1]):
                    errors.append(f'{mw}: githubUrl 과 filePath 는 필수입니다.')
                elif key not in defined_blocks:
                    errors.append(f'{mw}: 이 논문의 codeBlocks 에 없는 코드를 가리킵니다 — '
                                  f'githubUrl/filePath/symbolName/startLine 이 정확히 일치해야 합니다. {key}')

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


# ── 경고 ──────────────────────────────────────────────────────
def warnings_for(doc):
    """
    적재 자체는 되지만 나중에 문제가 되는 것들. 차단하지 않고 알리기만 합니다.

    validate()가 "지금 실패할 것"을 잡는다면, 여기는 "다음 번에 실패할 것"과
    "조용히 데이터를 잃는 것"을 잡습니다.
    """
    warns = []

    for pi, p in enumerate(doc.get('papers') or []):
        where = f'papers[{pi}]'
        arxiv = p.get('arxivId')

        # papers는 arxiv_id로 UPSERT합니다. 빈 값으로 덮으면 이미 들어 있던 메타데이터가
        # 조용히 사라집니다 (lit()이 빈 문자열을 NULL로 바꿉니다).
        if not (p.get('abstract') or '').strip():
            warns.append(f'{where}: abstract 가 비어 있습니다 — 이미 적재된 논문이라면 '
                         f'기존 초록을 NULL로 덮어씁니다 (arxivId={arxiv})')
        if not (p.get('authors') or []):
            warns.append(f'{where}: authors 가 비어 있습니다 — 이미 적재된 논문이라면 '
                         f'기존 저자 목록을 []로 덮어씁니다 (arxivId={arxiv})')

        # 코드 검색은 그 논문에 연결된 저장소 안에서만 후보를 찾습니다(CodeSearchService).
        # 저장소가 하나도 없으면 스코프가 비어 전체 코퍼스로 폴백하는데, 그 결과는 정의상
        # 전부 '다른 논문의 구현'입니다. 적재 자체는 막지 않되 여기서 반드시 알립니다.
        if not (p.get('repositories') or []):
            warns.append(f'{where}: repositories 가 비어 있습니다 — 이 논문의 단락을 검색하면 '
                         f'연결된 저장소가 없어 다른 논문의 코드가 반환됩니다 (arxivId={arxiv})')
        elif not any((r.get('codeBlocks') or []) for r in p['repositories']):
            warns.append(f'{where}: 저장소는 있으나 codeBlocks 가 하나도 없습니다 — '
                         f'검색 후보가 비어 다른 논문의 코드가 반환됩니다 (arxivId={arxiv})')

        for ri, r in enumerate(p.get('repositories') or []):
            rw = f'{where}.repositories[{ri}]'
            blocks = r.get('codeBlocks') or []

            # uq_code_blocks_location 은 (repository_id, file_path, symbol_name, start_line) 인데
            # PostgreSQL의 UNIQUE는 NULL을 서로 다른 값으로 봅니다. start_line 이 NULL이면
            # ON CONFLICT 가 걸리지 않아 재적재 때마다 같은 블록이 새 행으로 쌓이고,
            # 그 다음 --insert-mappings 의 block_ref() 서브쿼리가 2행을 반환해 실패합니다.
            no_line = [bi for bi, b in enumerate(blocks) if b.get('startLine') is None]
            if no_line:
                warns.append(
                    f'{rw}: codeBlocks {len(no_line)}/{len(blocks)} 건에 startLine 이 없습니다 '
                    f'(index {fmt_idx(no_line)}) — uq_code_blocks_location 이 NULL을 서로 다른 값으로 '
                    f'취급하므로 ON CONFLICT 가 걸리지 않습니다. 두 번째 적재부터 code_blocks 가 '
                    f'중복되고 --insert-mappings 가 "more than one row returned by a subquery" 로 '
                    f'실패합니다.\n'
                    f'     → GitHub 원본 기준 startLine/endLine 을 채우거나, '
                    f'적재 전 scripts/reset_db.sh 로 초기화하세요.')

            no_symbol = [bi for bi, b in enumerate(blocks) if not b.get('symbolName')]
            if no_symbol:
                warns.append(
                    f'{rw}: codeBlocks {len(no_symbol)} 건에 symbolName 이 없습니다 '
                    f'(index {fmt_idx(no_symbol)}) — 자연키가 filePath 하나로 좁아져 '
                    f'같은 파일의 다른 심볼과 구분되지 않습니다.')

    return warns


def fmt_idx(idxs, limit=8):
    """인덱스 목록을 짧게 — 많으면 뒤를 생략합니다."""
    head = ', '.join(str(i) for i in idxs[:limit])
    return head if len(idxs) <= limit else f'{head}, … (+{len(idxs) - limit})'


# ── SQL 생성 ──────────────────────────────────────────────────
def build_sql(doc):
    out = ['BEGIN;']

    # 본문이 바뀐 chunk/코드블록의 AI 매핑은 여기서 지웁니다 — 아래 STALE_AI_CLEANUP 참고.
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

    out.append(STALE_AI_CLEANUP)
    out.append('\nCOMMIT;')
    return '\n'.join(out)


# ── 낡은 AI 매핑 정리 ─────────────────────────────────────────
#
# 위 UPSERT는 본문이 바뀐 chunk/코드블록의 embedding을 NULL로 되돌립니다.
# 그런데 paper_code_mappings의 'AI' 매핑(설명·근거)은 그대로 남습니다. 그러면:
#
#   본문 수정 → embedding=NULL → backfill로 다시 채움
#            → 큐레이션 pending 조건이 NOT EXISTS('AI' 매핑)이라 이 chunk를 건너뜀
#            → 옛 본문 기준으로 생성된 AI 설명이 화면에 계속 남음
#
# embedding IS NULL 이 곧 "본문이 방금 바뀌었다(또는 아직 임베딩 전이다)"는 표시이므로,
# 그 상태의 행에 붙어 있는 AI 매핑만 지우면 다음 큐레이션이 자동으로 다시 만듭니다.
#
# MANUAL 매핑은 건드리지 않습니다 — A가 손으로 검수한 정답이라 재생성 대상이 아닙니다.
# 새로 들어온 chunk/블록도 embedding이 NULL이지만 AI 매핑이 없으므로 아무 일도 일어나지 않습니다.
STALE_AI_CLEANUP = """
-- 본문이 바뀐 chunk의 AI 매핑 제거 (MANUAL은 유지)
DELETE FROM paper_code_mappings m
USING paper_chunks c
WHERE m.paper_chunk_id = c.id
  AND c.embedding IS NULL
  AND m.mapping_method = 'AI';

-- 코드가 바뀐 블록을 가리키는 AI 매핑 제거 — 설명이 옛 코드를 서술하고 있으므로 무효
DELETE FROM paper_code_mappings m
USING code_blocks cb
WHERE m.code_block_id = cb.id
  AND cb.embedding IS NULL
  AND m.mapping_method = 'AI';"""


def chunk_ref(arxiv_id, chunk_index):
    return (f"(SELECT id FROM paper_chunks WHERE chunk_index = {chunk_index}"
            f" AND paper_id = (SELECT id FROM papers WHERE arxiv_id = {lit(arxiv_id)}))")


def block_ref(m):
    """
    코드 블록을 자연키로 가리킵니다. symbol_name/start_line은 NULL일 수 있어
    = 대신 IS NOT DISTINCT FROM 을 씁니다 (NULL = NULL 은 참이 아니라 NULL이라서).
    """
    return (f"(SELECT id FROM code_blocks"
            f" WHERE repository_id = (SELECT id FROM repositories WHERE github_url = {lit(m['githubUrl'])})"
            f"   AND file_path = {lit(m['filePath'])}"
            f"   AND symbol_name IS NOT DISTINCT FROM {lit(m.get('symbolName'))}"
            f"   AND start_line IS NOT DISTINCT FROM {lit(m.get('startLine'))})")


def iter_manual_mappings(doc):
    """(arxivId, chunkIndex, mappedCode) 를 순회합니다."""
    for p in doc['papers']:
        for c in p.get('chunks') or []:
            for m in c.get('mappedCode') or []:
                yield p['arxivId'], c['chunkIndex'], m


def build_manual_mapping_sql(doc):
    """
    A가 손으로 분류한 단락↔코드를 mapping_method='MANUAL', is_verified=TRUE 로 저장합니다.
    AI 큐레이션(mapping_method='AI')과 별개 행이므로 둘이 공존하며,
    CurationBatchService는 'AI' 매핑이 없는 chunk를 계속 대상으로 삼습니다.
    """
    rows = list(iter_manual_mappings(doc))
    if not rows:
        return None

    out = ['BEGIN;']
    for arxiv_id, chunk_index, m in rows:
        out.append(f"""
INSERT INTO paper_code_mappings (paper_chunk_id, code_block_id, mapping_method, mapping_reason, is_verified)
VALUES ({chunk_ref(arxiv_id, chunk_index)}, {block_ref(m)}, 'MANUAL', {lit(m.get('reason'))}, TRUE)
ON CONFLICT (paper_chunk_id, code_block_id) DO UPDATE SET
    mapping_method = 'MANUAL', mapping_reason = EXCLUDED.mapping_reason,
    is_verified = TRUE, updated_at = CURRENT_TIMESTAMP;""")
    out.append('\nCOMMIT;')
    return '\n'.join(out)


def build_eval_query(doc, include_alternates=False):
    """
    정답셋 CSV(chunk_id,code_block_id)를 만들기 위한 조회 쿼리.

    각 단락의 mappedCode 중 **첫 번째**가 Top-1 정답입니다 —
    노트에 적을 때 가장 정확한 코드를 맨 앞에 두세요.

    include_alternates=True 면 mappedCode 전체를 내보냅니다. 같은 chunk 가 여러 행이
    되는데, eval_retrieval.py 는 첫 행을 Top-1 정답으로 보고 나머지는 --multi-gold
    일 때만 인정합니다. 즉 한 파일로 엄격/완화 두 기준을 다 잴 수 있습니다.

    순서가 의미를 가지므로(첫 행 = Top-1) 정렬 키를 함께 실어 보냅니다 —
    UNION ALL 의 행 순서는 보장되지 않습니다.
    """
    order, seq = {}, {}      # chunk 등장 순서 / chunk 안에서의 순번(0 = Top-1)
    selects = []
    for arxiv_id, chunk_index, m in iter_manual_mappings(doc):
        key = (arxiv_id, chunk_index)
        if key not in order:
            order[key], seq[key] = len(order), 0
        elif include_alternates:
            seq[key] += 1
        else:
            continue
        selects.append((order[key], seq[key], arxiv_id, chunk_index, m))

    if not selects:
        return None
    return '\nUNION ALL\n'.join(
        f"SELECT {ci} || '|' || {sq} || '|' || {chunk_ref(a, i)} || ',' || {block_ref(m)}"
        for ci, sq, a, i, m in selects)


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
    parser.add_argument('--insert-mappings', action='store_true',
                        help="chunks[].mappedCode 를 paper_code_mappings에 MANUAL/검증완료로 저장")
    parser.add_argument('--eval-csv', metavar='PATH',
                        help='chunks[].mappedCode 로 정답셋 CSV 생성 (eval_retrieval.py 입력). '
                             '⚠️ 출력이 DB surrogate ID(chunk_id,code_block_id)라 적재 이력이 다른 '
                             'DB에서는 어긋납니다. 커밋할 정답셋은 안정 키를 쓰는 '
                             'scripts/note2ingest/eval_set_tool.py 로 만드세요. 이건 로컬 즉석 측정용입니다.')
    parser.add_argument('--eval-all', action='store_true',
                        help='--eval-csv 에 mappedCode 전체를 기록 (chunk 당 여러 행, 첫 행이 Top-1). '
                             'eval_retrieval.py --multi-gold 로 완화 기준을 잴 수 있습니다')
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
    manual = len(list(iter_manual_mappings(doc)))
    print(f'✅ 검증 통과 — 논문 {len(papers)} / chunk {chunks} / repo {repos} / code_block {blocks}'
          + (f' / 수동매핑 {manual}' if manual else ''))

    # 경고는 적재를 막지 않습니다 — 종료 코드도 바꾸지 않습니다.
    warns = warnings_for(doc)
    if warns:
        print(f'\n⚠️  경고 {len(warns)}건 (적재는 진행됩니다)')
        for w in warns:
            print(f'  · {w}')
        print()

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

    print('✅ 적재 완료')

    if args.insert_mappings:
        mapping_sql = build_manual_mapping_sql(doc)
        if mapping_sql is None:
            print('   --insert-mappings 를 줬지만 mappedCode 가 하나도 없습니다.')
        else:
            r = psql(args.container, args.db, args.user, mapping_sql)
            if r.returncode != 0:
                print(f'\n❌ 수동 매핑 저장 실패\n{r.stderr}', file=sys.stderr)
                sys.exit(1)
            print(f'✅ 수동 매핑 {manual}건 저장 (mapping_method=MANUAL, is_verified=TRUE)')

    if args.eval_csv:
        query = build_eval_query(doc, include_alternates=args.eval_all)
        if query is None:
            print('   --eval-csv 를 줬지만 mappedCode 가 하나도 없습니다.')
        else:
            r = psql(args.container, args.db, args.user, query, tuples_only=True)
            if r.returncode != 0:
                print(f'\n❌ 정답셋 생성 실패\n{r.stderr}', file=sys.stderr)
                sys.exit(1)
            # 'chunk순서|chunk내순번|chunk_id,block_id' — 순서가 의미를 가지므로 정렬 후 키를 뗍니다.
            rows = []
            for ln in r.stdout.splitlines():
                parts = ln.strip().split('|')
                if len(parts) == 3 and ',' in parts[2]:
                    rows.append((int(parts[0]), int(parts[1]), parts[2]))
            rows.sort()
            chunks = len({r[0] for r in rows})
            with open(args.eval_csv, 'w', encoding='utf-8') as f:
                f.write('chunk_id,code_block_id\n')
                f.write('\n'.join(pair for _, _, pair in rows) + '\n')
            note = ' (mappedCode 전체)' if args.eval_all else ' (chunk 당 Top-1만)'
            print(f'✅ 정답셋 chunk {chunks}개 / {len(rows)}행{note} → {args.eval_csv}')

    summary = psql(args.container, args.db, args.user, """
SELECT '  DB 총계: papers ' || (SELECT count(*) FROM papers)
    || ' / chunks ' || (SELECT count(*) FROM paper_chunks)
    || ' / repos ' || (SELECT count(*) FROM repositories)
    || ' / code_blocks ' || (SELECT count(*) FROM code_blocks)
UNION ALL
SELECT '  embedding 미완료: chunk ' || (SELECT count(*) FROM paper_chunks WHERE embedding IS NULL)
    || ' / code_block ' || (SELECT count(*) FROM code_blocks WHERE embedding IS NULL);
""", tuples_only=True)
    print(summary.stdout.rstrip())
    print('\n다음 단계: 임베딩 채우기')
    print('  cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run')


if __name__ == '__main__':
    main()
