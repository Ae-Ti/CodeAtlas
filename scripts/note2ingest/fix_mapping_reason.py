#!/usr/bin/env python3
"""매핑 근거(mappedCode[].reason)에 남은 마크다운 잔재를 걷어냅니다.

노트의 '⑦ 논문 ↔ 코드' 절은 산문이 아니라 ``` 펜스로 감싼 대응표인데,
build_all.py 가 그 본문을 공백만 접어서 reason 으로 썼습니다. 그래서
화면의 '매칭 근거' 자리에 이런 문자열이 그대로 떴습니다.

    ``` DIRECT ``` ---
    ``` DIRECT ``` --- 논문: > perceptual loss > ↓ 코드: ``` self.perceptual_loss() ``` ---

정보가 든 칸은 parse_md.clean_match 로 다시 읽어 쓰고, 판정 라벨(DIRECT 등)뿐이라
근거로 쓸 내용이 없는 칸은 경로·심볼로 만든 문장으로 바꿉니다.
근본 원인은 parse_md.parse_format_a 에서 고쳤으므로 새 노트에는 재발하지 않습니다.

    python3 scripts/note2ingest/fix_mapping_reason.py --dry-run   # 바뀔 내용만 출력
    python3 scripts/note2ingest/fix_mapping_reason.py             # ingest JSON 갱신
    python3 scripts/note2ingest/fix_mapping_reason.py --sql out.sql  # DB 갱신용 SQL
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_md import clean_match  # noqa: E402

ING = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'database', 'ingest')
ING = os.path.normpath(ING)

DIRTY = re.compile(r'```|---|^\s*>|↓')


def fallback(block):
    """근거로 쓸 문장이 없을 때 — 어느 코드가 이 단락의 구현인지만 사실대로 적습니다."""
    sym = block.get('symbolName')
    where = '%s:%s' % (block['filePath'], block['startLine'])
    return '%s 의 %s 이 이 단락의 구현' % (where, sym) if sym else '%s 이 이 단락의 구현' % where


def repair(reason, block):
    if not reason or not DIRTY.search(reason):
        return None                                  # 이미 멀쩡한 산문 — 손대지 않습니다
    return clean_match(reason) or fallback(block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sql', metavar='PATH', help='DB 갱신용 UPDATE 문을 이 파일로 씁니다')
    args = ap.parse_args()

    changed = kept = 0
    updates = []
    for path in sorted(glob.glob(os.path.join(ING, '*_ingest.json'))):
        doc = json.load(open(path, encoding='utf-8'))
        name = os.path.basename(path).replace('_ingest.json', '')
        n = 0
        for paper in doc['papers']:
            for chunk in paper['chunks']:
                for m in chunk.get('mappedCode') or []:
                    new = repair(m.get('reason'), m)
                    if new is None or new == m.get('reason'):
                        kept += 1
                        continue
                    if args.dry_run:
                        print('  [%s] chunk %s' % (name, chunk['chunkIndex']))
                        print('    - %s' % m['reason'][:110])
                        print('    + %s' % new[:110])
                    updates.append((paper['arxivId'], chunk['chunkIndex'],
                                    m['githubUrl'], m['filePath'], m['symbolName'],
                                    m['startLine'], new))
                    m['reason'] = new
                    n += 1
                    changed += 1
        if not args.dry_run and n:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write('\n')
        print('%-24s 고침 %3d' % (name, n))

    print('\n합계 — 고침 %d / 그대로 %d' % (changed, kept))

    if args.sql:
        with open(args.sql, 'w', encoding='utf-8') as f:
            f.write('-- mappedCode[].reason 의 마크다운 잔재 제거분을 DB 에 반영합니다.\n')
            f.write('-- MANUAL 행만 대상입니다 (AI 행의 mapping_reason 은 배치가 쓴 TACC 요약).\n')
            f.write('BEGIN;\n')
            for aid, idx, url, fp, sym, line, new in updates:
                f.write(
                    "UPDATE paper_code_mappings m SET mapping_reason = %s\n"
                    "  FROM paper_chunks pc, papers p, code_blocks cb, repositories r\n"
                    " WHERE m.paper_chunk_id = pc.id AND pc.paper_id = p.id\n"
                    "   AND m.code_block_id = cb.id AND cb.repository_id = r.id\n"
                    "   AND m.mapping_method = 'MANUAL'\n"
                    "   AND p.arxiv_id = %s AND pc.chunk_index = %s\n"
                    "   AND r.github_url = %s AND cb.file_path = %s\n"
                    "   AND cb.symbol_name %s AND cb.start_line = %s;\n"
                    % (lit(new), lit(aid), idx, lit(url), lit(fp),
                       ('IS NULL' if sym is None else '= ' + lit(sym)), line))
            f.write('COMMIT;\n')
        print('SQL → %s (%d 문)' % (args.sql, len(updates)))


def lit(s):
    return "'" + str(s).replace("'", "''") + "'"


if __name__ == '__main__':
    main()
