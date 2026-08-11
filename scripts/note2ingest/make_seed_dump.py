#!/usr/bin/env python3
"""database/seed_dump.sql 생성 — 클론 후 동일 DB 상태 재현용 (운영규정 제10조①).

Script-2 → Script-3 으로 스키마를 만든 뒤 이 파일 하나를 넣으면 카탈로그가 그대로 복원됩니다.

    ./scripts/reset_db.sh
    docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas < database/seed_dump.sql

기본은 embedding 을 빼고 뜹니다. 벡터는 텍스트로 직렬화하면 파일의 90%를 차지하는데
`nomic-embed-text` 만 있으면 1분 안에 다시 채울 수 있기 때문입니다. 반대로 AI 설명은
qwen3:8b 로 100분 넘게 걸리므로 **항상 포함**합니다 — 재현 비용이 가장 큰 부분입니다.

    python3 scripts/note2ingest/make_seed_dump.py                    # 기본
    python3 scripts/note2ingest/make_seed_dump.py --with-embeddings  # 벡터까지 (Ollama 없이 검색 가능)
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'database', 'seed_dump.sql')

TABLES = [
    ('papers', 'id, title, abstract, arxiv_id, doi, pdf_url, source_url, published_date, '
               'authors, processing_status, created_at, updated_at'),
    ('repositories', 'id, github_url, owner_name, repository_name, default_branch, commit_hash, '
                     'license_name, primary_language, star_count, processing_status, '
                     'last_synced_at, created_at, updated_at'),
    ('paper_repositories', 'paper_id, repository_id, relation_type, is_primary, created_at'),
    ('paper_chunks', 'id, paper_id, section_title, subsection_title, chunk_index, content, '
                     'page_start, page_end, token_count, created_at, embedding, embedding_model'),
    ('code_blocks', 'id, repository_id, file_path, symbol_name, symbol_type, programming_language, '
                    'start_line, end_line, code_content, parent_symbol_name, created_at, '
                    'embedding, embedding_model'),
    ('paper_code_mappings', 'id, paper_chunk_id, code_block_id, similarity_score, mapping_method, '
                            'mapping_reason, explanation, is_verified, created_at, updated_at'),
]
SEQ = ['papers', 'repositories', 'paper_chunks', 'code_blocks', 'paper_code_mappings']


def psql(sql, tuples_only=True):
    cmd = ['docker', 'exec', '-i', 'codeatlas-postgres', 'psql', '-U', 'codeatlas',
           '-d', 'codeatlas', '-v', 'ON_ERROR_STOP=1']
    cmd += ['-tAc', sql] if tuples_only else ['-c', sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return r.stdout


def dump_table(table, cols, with_emb):
    if not with_emb:
        cols = ', '.join(c for c in (x.strip() for x in cols.split(','))
                         if c not in ('embedding', 'embedding_model'))
    # COPY ... TO STDOUT 대신 pg_catalog 의 텍스트 표현을 그대로 쓰는 INSERT 문을 만듭니다.
    # 코드 본문에 따옴표·백슬래시·$ 가 섞여 있어 dollar-quoting 이 필요한데,
    # quote_literal 은 E'' 이스케이프로 안전하게 처리해 줍니다.
    exprs = ', '.join(f"coalesce(quote_literal({c}::text), 'NULL')" for c in
                      (x.strip() for x in cols.split(',')))
    order = 'paper_id, repository_id' if table == 'paper_repositories' else 'id'
    # 값 안에 줄바꿈이 들어 있으므로(논문 본문·코드) 행 단위로 읽지 않고
    # 서버에서 한 덩어리로 이어붙여 받습니다. 클라이언트에서 줄로 자르면 값이 깨집니다.
    body = psql(f"SELECT string_agg('  (' || concat_ws(', ', {exprs}) || ')', E',\n' "
                f"ORDER BY {order}) FROM {table}").rstrip('\n')
    n = int(psql(f'SELECT count(*) FROM {table}').strip())
    if not n:
        return f'-- {table}: 행 없음\n'
    return (f'\n-- {table} ({n}행)\n'
            f'INSERT INTO {table} ({cols}) OVERRIDING SYSTEM VALUE VALUES\n{body};\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--with-embeddings', action='store_true',
                    help='벡터까지 포함 (파일이 커지지만 Ollama 없이도 검색이 됩니다)')
    args = ap.parse_args()

    counts = {t: int(psql(f'SELECT count(*) FROM {t}').strip()) for t, _ in TABLES}
    head = [
        '/* =========================================================',
        '   seed_dump.sql — 카탈로그 재현용 데이터',
        '',
        '   사용법:',
        '     ./scripts/reset_db.sh          # Script-2 → Script-3 로 스키마 생성',
        '     docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas \\',
        '         < database/seed_dump.sql',
        '',
        '   수록: ' + ' / '.join(f'{t} {counts[t]}' for t, _ in TABLES),
        '   embedding: ' + ('포함' if args.with_embeddings else
                            '미포함 — 아래 backfill 로 1분이면 채워집니다'),
        '',
        '   embedding 을 빼고 뜬 이유는 벡터를 텍스트로 적으면 파일의 90%를 차지하는데',
        '   nomic-embed-text 로 금방 복원되기 때문입니다. 반대로 AI 설명(explanation)은',
        '   qwen3:8b 로 100분 넘게 걸리므로 이 파일에 항상 들어 있습니다.',
        '',
        '     cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run',
        '',
        '   출처·라이선스는 database/seed_manifest.csv 와',
        '   database/THIRD_PARTY_LICENSES.md 를 보세요.',
        '   ========================================================= */',
        '', 'BEGIN;', '']
    body = [dump_table(t, c, args.with_embeddings) for t, c in TABLES]
    tail = ['', '-- identity 시퀀스를 현재 최대값으로 맞춥니다 (이후 적재가 이어지도록)']
    for t in SEQ:
        tail.append(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                    f"coalesce((SELECT max(id) FROM {t}), 1));")
    tail += ['', 'COMMIT;', '']
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(head) + ''.join(body) + '\n'.join(tail))
    size = os.path.getsize(OUT)
    print(f'{OUT} — {size/1024:.0f} KB')
    for t, _ in TABLES:
        print(f'   {t:24} {counts[t]:5}행')


if __name__ == '__main__':
    main()
