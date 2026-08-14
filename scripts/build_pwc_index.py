#!/usr/bin/env python3
"""PWC 아카이브 → 논문↔저장소 링크 색인 (database/pwc/links.tsv.gz).

Papers with Code 는 2025-07 에 서비스가 종료됐지만 축적된 링크 데이터는
CC-BY-SA-4.0 으로 HuggingFace 에 남아 있습니다. 그 parquet 을 받아
`suggest_repos.py` 가 표준 라이브러리만으로 읽을 수 있는 형태로 줄입니다.

    arxiv_id \t owner/name \t 플래그(O=official P=논문언급 G=README언급)

색인을 저장소에 넣어 두는 이유는 재현성입니다 — datasets-server 는 실제로
작업 중에 500(`temporary internal issue`)을 냈습니다. 심사·검증 시점에 외부
서비스가 살아 있어야만 도는 기능이면 제10조① 을 만족하지 못합니다.

    pip install pyarrow          # 이 스크립트에만 필요합니다
    python3 scripts/build_pwc_index.py

갱신은 드물게 하면 됩니다. PWC 는 이미 종료돼 원본이 더 늘지 않습니다.
"""
import argparse
import gzip
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'database', 'pwc', 'links.tsv.gz')
PARQUET_URL = ('https://huggingface.co/datasets/pwc-archive/links-between-paper-and-code'
               '/resolve/main/data/train-00000-of-00001.parquet')

HEADER = (
    '# Papers with Code 아카이브에서 뽑은 논문↔저장소 링크 색인\n'
    '# 원본: https://huggingface.co/datasets/pwc-archive/links-between-paper-and-code\n'
    '# 라이선스: CC-BY-SA-4.0 — 이 파일은 원본의 부분집합(파생물)이므로 같은 조건으로 배포됩니다.\n'
    '#          출처 표기는 database/THIRD_PARTY_LICENSES.md 를 보세요.\n'
    '# 생성: scripts/build_pwc_index.py\n'
    '# 형식: arxiv_id <TAB> owner/name <TAB> 플래그(O=PWC official, P=논문이 언급, G=README가 언급)\n'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parquet', help='이미 받아둔 parquet 경로 (없으면 내려받습니다)')
    ap.add_argument('--out', default=OUT)
    args = ap.parse_args()

    try:
        import pyarrow.parquet as pq
    except ImportError:
        sys.exit('pyarrow 가 필요합니다:  pip install pyarrow\n'
                 '(이 스크립트에만 필요하고, suggest_repos.py 는 표준 라이브러리만 씁니다)')

    path = args.parquet
    if not path:
        path = os.path.join(os.path.dirname(args.out), '_pwc.parquet')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f'내려받는 중… {PARQUET_URL}')
        urllib.request.urlretrieve(PARQUET_URL, path)

    table = pq.read_table(path, columns=[
        'paper_arxiv_id', 'repo_url', 'is_official', 'mentioned_in_paper', 'mentioned_in_github'])
    rows = []
    for r in table.to_pylist():
        aid, url = r['paper_arxiv_id'], r['repo_url'] or ''
        if not aid or not url.startswith('https://github.com/'):
            continue
        slug = url[len('https://github.com/'):].strip('/')
        # PWC 에는 파일·디렉터리 링크가 섞여 있습니다 — 저장소 루트로 접습니다.
        parts = slug.split('/')
        if len(parts) < 2:
            continue
        slug = f'{parts[0]}/{parts[1].removesuffix(".git")}'
        flags = (('O' if r['is_official'] else '') + ('P' if r['mentioned_in_paper'] else '')
                 + ('G' if r['mentioned_in_github'] else ''))
        rows.append((aid, slug, flags))

    # arxiv_id 로 정렬해 두면 suggest_repos 가 이분 탐색 없이 순차로 읽어도 빠르고,
    # 갱신 시 diff 가 지역적으로만 생깁니다.
    rows = sorted(set(rows))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with gzip.open(args.out, 'wt', encoding='utf-8', compresslevel=9) as f:
        f.write(HEADER)
        for aid, slug, flags in rows:
            f.write(f'{aid}\t{slug}\t{flags}\n')

    size = os.path.getsize(args.out)
    papers = len({r[0] for r in rows})
    print(f'{args.out} — 링크 {len(rows):,}건 / 논문 {papers:,}편 / {size/1e6:.1f} MB')
    print(f'  official 표시 {sum(1 for r in rows if "O" in r[2]):,}건')


if __name__ == '__main__':
    main()
