#!/usr/bin/env python3
"""정답셋을 DB 자동증가 ID 대신 안정 키로 보관하고, 평가 직전에 ID 로 되돌립니다.

DB surrogate ID 는 적재 순서·이력에 따라 달라져서 깨끗한 DB 에 클론하면 어긋납니다
(운영규정 제10조① 심사·검증 가능한 상태). 그래서 커밋되는 정답셋은 안정 키로 두고,
평가 직전 이 스크립트로 eval_retrieval.py 가 받는 (chunk_id, code_block_id) CSV 를 만듭니다.

    # 커밋용 안정 키 정답셋 생성 (ingest JSON 만 있으면 됨, DB 불필요)
    python3 scripts/note2ingest/eval_set_tool.py export              # 대안 정답 포함 (multi-gold)
    python3 scripts/note2ingest/eval_set_tool.py export --top1-only  # chunk 당 1개만

    # 평가 직전 현재 DB 기준 ID CSV 로 변환
    python3 scripts/note2ingest/eval_set_tool.py resolve database/eval_set_bert.csv /tmp/bert_ids.csv
    python3 scripts/eval_retrieval.py /tmp/bert_ids.csv
"""
import csv
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ING = os.environ.get('CODEATLAS_INGEST_DIR') or os.path.join(ROOT, 'database', 'ingest')
DB = os.path.join(ROOT, 'database')
COLS = ['arxiv_id', 'chunk_index', 'github_url', 'file_path', 'symbol_name', 'start_line']


def export(top1_only=False):
    for path in sorted(glob.glob(os.path.join(ING, '*_ingest.json'))):
        doc = json.load(open(path, encoding='utf-8'))
        p = doc['papers'][0]
        rows = []
        for c in p['chunks']:
            # mappedCode 전체를 내보냅니다. 맨 앞이 Top-1 이고 나머지는 대안 정답인데,
            # 한 단락이 두 코드에 대응하는 건 실제 사실이라 하나만 남기면 제품을
            # 실제보다 나쁘게 재게 됩니다. 단일 정답으로 재려면 --top1-only 를 쓰세요.
            for m in (c.get('mappedCode') or [])[:1 if top1_only else None]:
                rows.append([p['arxivId'], c['chunkIndex'], m['githubUrl'], m['filePath'],
                             m['symbolName'] or '', m['startLine'] if m['startLine'] is not None else ''])
        name = os.path.basename(path).replace('_ingest.json', '')
        if name == 'attention_is_all_you_need':
            name = 'attention'
        out = os.path.join(DB, f'eval_set_{name}.csv')
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerows(rows)
        print(f'  {os.path.basename(out):34} {len(rows)}행')


def psql(sql):
    r = subprocess.run(['docker', 'exec', 'codeatlas-postgres', 'psql', '-U', 'codeatlas',
                        '-d', 'codeatlas', '-tAc', sql], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return [l for l in r.stdout.splitlines() if l.strip()]


def resolve(src, dst):
    rows = list(csv.DictReader(open(src, newline='', encoding='utf-8')))
    if rows and 'chunk_id' in rows[0]:
        sys.exit(f'{src} 는 이미 ID 형식입니다.')
    chunks, blocks = {}, {}
    for l in psql("SELECT p.arxiv_id||'|'||c.chunk_index||'|'||c.id FROM paper_chunks c "
                  "JOIN papers p ON p.id = c.paper_id"):
        a, i, cid = l.split('|')
        chunks[(a, int(i))] = int(cid)
    for l in psql("SELECT r.github_url||'|'||cb.file_path||'|'||coalesce(cb.symbol_name,'')||'|'"
                  "||coalesce(cb.start_line::text,'')||'|'||cb.id "
                  "FROM code_blocks cb JOIN repositories r ON r.id = cb.repository_id"):
        u, fp, sn, sl, bid = l.split('|')
        blocks[(u, fp, sn, sl)] = int(bid)
    out, miss = [], []
    for r in rows:
        cid = chunks.get((r['arxiv_id'], int(r['chunk_index'])))
        bid = blocks.get((r['github_url'], r['file_path'], r['symbol_name'], str(r['start_line'])))
        (out if cid and bid else miss).append((cid, bid) if cid and bid else r)
    with open(dst, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['chunk_id', 'code_block_id'])
        w.writerows(out)
    print(f'{os.path.basename(src)} → {dst}: {len(out)}행 해석' + (f' / 미해석 {len(miss)}행' if miss else ''))
    for r in miss[:5]:
        print('   ❌', r['arxiv_id'], r['chunk_index'], r['file_path'], r['symbol_name'])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'export':
        export(top1_only='--top1-only' in sys.argv)
    elif len(sys.argv) == 4 and sys.argv[1] == 'resolve':
        resolve(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
