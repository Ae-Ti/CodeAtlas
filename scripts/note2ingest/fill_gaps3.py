#!/usr/bin/env python3
"""3차 — 제목만 있는 chunk. 제목 키워드로 논문 전체를 훑어 해당 대목을 찾습니다."""
import json, os, re, sys, collections
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
from fill_gaps import FILES, PAGES, tokens, norm
ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'

def find_window(aid, q, want=650, min_hit=2):
    best = (0, None, None)
    for pi, txt in enumerate(PAGES[aid]):
        t = re.sub(r'-\n', '', txt)
        sents = re.split(r'(?<=[.!?])\s+', norm(t))
        for i in range(len(sents)):
            w, j = '', i
            while j < len(sents) and len(w) < want:
                w += sents[j] + ' '; j += 1
            low = w.lower()
            score = sum(1 for x in set(q) if x in low)
            if score > best[0]:
                best = (score, w.strip(), pi + 1)
    return best if best[0] >= min_hit and best[1] and len(best[1]) > 120 else (0, None, None)

tot = collections.Counter()
for fname, aid in FILES.items():
    path = os.path.join(ING, fname)
    doc = json.load(open(path, encoding='utf-8')); cs = doc['papers'][0]['chunks']
    n = 0
    for c in cs:
        if '보강' in c.get('_comment', ''):
            continue
        title = c['subsectionTitle']
        # 참고문헌 chunk 는 저자명이 키 (Kingma, Sennrich, Szegedy …)
        q = tokens(title) + tokens(c['content'])
        q = [t for t in q if t not in ('reference', 'equation', 'option')]
        score, win, pg = find_window(aid, q)
        if win:
            c['content'] = c['content'].rstrip() + '\n\n' + win
            c['_comment'] = c.get('_comment', '') + f' | 논문 원문 보강 (PDF p.{pg}, 제목 키워드 대조)'
            if c.get('pageStart') is None:
                c['pageStart'] = c['pageEnd'] = pg
            n += 1
    left = sum(1 for c in cs if '보강' not in c.get('_comment', ''))
    doc['_unresolved'] = [u for u in doc['_unresolved'] if u.get('title') != '잔여 누락']
    lp = sum(1 for c in cs if c.get('pageStart') is None)
    if left or lp:
        doc['_unresolved'].append({'chunk': '-', 'title': '잔여 누락',
                                   'issue': f'쪽 미확정 {lp}건 / 논문 원문 미보강 {left}건 '
                                            f'(논문에 대응 서술이 없는 항목)'})
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2); f.write('\n')
    tot['n'] += n; tot['left'] += left; tot['lp'] += lp
    print(f'{fname.replace("_ingest.json",""):24} 보강 +{n:2}   남은 원문 {left:2} / 쪽 {lp}')
print(f"\n합계 — 보강 +{tot['n']}  |  남은 원문 {tot['left']} / 쪽 {tot['lp']}")
