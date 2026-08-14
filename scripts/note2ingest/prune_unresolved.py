#!/usr/bin/env python3
"""`_unresolved` 기록을 현재 데이터와 다시 맞춥니다.

`_unresolved` 는 "확신이 없어 손대지 않은 것"을 남기는 판단 기록입니다. 그런데
저장소 원문 교체·보조 저장소 추가·빈틈 채우기를 여러 번 돌면서, **나중에 해결된
항목이 기록에는 그대로 남았습니다.** ingest JSON 은 제출물이라 이 상태로 두면
심사자가 파일을 열었을 때 해결된 항목까지 미해결로 읽습니다
(Attention 은 83건이 남아 있는데 실제로는 정답셋 61쌍이 나온 가장 잘 정리된 논문입니다).

판정 규칙은 하나입니다 — **그 chunk 에 지금 mappedCode 가 있으면 해결된 것**입니다.
모든 항목이 "코드를 붙이지 못했다"는 내용이라 이 하나로 갈립니다.

    python3 scripts/note2ingest/prune_unresolved.py --dry-run
    python3 scripts/note2ingest/prune_unresolved.py

남는 항목은 영어로 적힌 초기 기록도 우리말로 통일합니다 — 나머지가 전부 우리말이라
섞여 있으면 두 사람이 다른 도구로 만든 것처럼 보입니다.
"""
import argparse
import collections
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ING = os.path.join(ROOT, 'database', 'ingest')

#: 초기 적재 때 영어로 남은 문구 → 우리말
REWRITE = [
    (re.compile(r'Excluded actual code from codeBlocks because the section did not provide a '
                r'GitHub file path\.?', re.I),
     '노트에 GitHub 파일 경로가 없어 코드 블록으로 만들지 않음'),
    (re.compile(r'Excluded expected code block; not treated as repository codeBlock\.?', re.I),
     '노트가 (예상코드)로 표시한 블록 — 저장소에 실제로 없는 코드'),
    (re.compile(r"Excluded duplicate natural key \(([^)]*)\)[^.]*\.?", re.I),
     r'같은 위치(\1)가 중복돼 한 건만 남김'),
    (re.compile(r'Excluded[^.]*\.?', re.I),
     '초기 적재에서 제외한 블록'),
]


def find_chunk(paper, entry):
    """_unresolved 항목이 가리키는 chunk 를 찾습니다.

    두 서식이 섞여 있습니다 — Attention 은 `section`(1부터), 나머지는 `chunk`(노트 태그).
    """
    chunks = paper['chunks']
    if entry.get('section') is not None:
        idx = int(entry['section']) - 1
        return chunks[idx] if 0 <= idx < len(chunks) else None

    tag = str(entry.get('chunk') or '').strip()
    if not tag or tag == '-':
        return None
    # '노트 15' 가 '노트 1' 에 걸리지 않도록 경계를 둡니다.
    pat = re.compile(r'노트\s+' + re.escape(tag) + r'(?![0-9A-Za-z\-])')
    for c in chunks:
        if pat.search(c.get('_comment') or ''):
            return c
    return None


def normalize(issue):
    for pat, repl in REWRITE:
        if pat.search(issue):
            return pat.sub(repl, issue).strip()
    return issue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    stat = collections.Counter()
    for path in sorted(glob.glob(os.path.join(ING, '*_ingest.json'))):
        doc = json.load(open(path, encoding='utf-8'))
        name = os.path.basename(path).replace('_ingest.json', '')
        paper = doc['papers'][0]
        kept, dropped, unmatched, rewritten = [], 0, 0, 0

        for entry in doc.get('_unresolved') or []:
            chunk = find_chunk(paper, entry)
            if chunk is None:
                # 가리키는 chunk 를 못 찾으면 지우지 않습니다 — 판단 기록을 잃는 쪽이 더 나쁩니다.
                unmatched += 1
            elif chunk.get('mappedCode'):
                dropped += 1
                continue
            new_issue = normalize(str(entry.get('issue') or ''))
            if new_issue != entry.get('issue'):
                entry['issue'] = new_issue
                rewritten += 1
            kept.append(entry)

        before = len(doc.get('_unresolved') or [])
        doc['_unresolved'] = kept
        if not args.dry_run:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write('\n')

        stat['before'] += before
        stat['after'] += len(kept)
        stat['dropped'] += dropped
        stat['unmatched'] += unmatched
        stat['rewritten'] += rewritten
        print(f'{name:24} {before:3} → {len(kept):3}  '
              f'(해결됨 -{dropped:3} / 우리말 정리 {rewritten:3} / chunk 미확인 {unmatched:2})')

    print(f'\n합계 {stat["before"]} → {stat["after"]}  '
          f'해결분 {stat["dropped"]}건 제거 · 문구 {stat["rewritten"]}건 정리 · '
          f'chunk 못 찾아 보존 {stat["unmatched"]}건')
    if args.dry_run:
        print('--dry-run 이라 파일은 그대로입니다.')


if __name__ == '__main__':
    main()
