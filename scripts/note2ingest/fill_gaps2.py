#!/usr/bin/env python3
"""2차 채우기 — 절 제목 위치 + 이웃 chunk 보간.

노트는 논문을 앞에서 뒤로 훑으며 작성돼 있어 쪽 번호가 단조 증가합니다.
그 성질을 이용해 남은 구멍을 메웁니다.
"""
import json, os, re, collections
SC = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, SC)
from fill_gaps import FILES, PAGES, tokens, best_page, extract_para, norm

ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'
SECNUM = re.compile(r'^\s*(?:Section\s*)?([0-9]+(?:\.[0-9]+)*)')


def section_page(aid, section_title):
    """'3.2 Attention' 같은 절 제목이 처음 나오는 쪽."""
    m = SECNUM.search(section_title or '')
    if not m:
        return None
    num = m.group(1)
    name = re.sub(r'^\s*(?:Section\s*)?[0-9.]+\s*', '', section_title).strip()
    pat = re.compile(r'\b' + re.escape(num) + r'[.\s]{1,3}' + re.escape(name[:18]), re.I) \
        if name else re.compile(r'^\s*' + re.escape(num) + r'\s', re.M)
    for i, txt in enumerate(PAGES[aid]):
        if pat.search(txt):
            return i + 1
    return None


def main():
    tot = collections.Counter()
    for fname, aid in FILES.items():
        path = os.path.join(ING, fname)
        doc = json.load(open(path, encoding='utf-8'))
        cs = doc['papers'][0]['chunks']
        n_sec = n_interp = n_content = 0

        # ① 절 제목으로
        for c in cs:
            if c.get('pageStart') is not None:
                continue
            pg = section_page(aid, c.get('sectionTitle', ''))
            if pg:
                c['pageStart'] = c['pageEnd'] = pg
                c['_comment'] = c.get('_comment', '') + f' | 쪽 번호 절 제목 위치로 채움(p.{pg})'
                n_sec += 1

        # ② 앞뒤 chunk 로 보간 (노트가 논문 순서를 따르므로)
        for i, c in enumerate(cs):
            if c.get('pageStart') is not None:
                continue
            prev = next((cs[j]['pageStart'] for j in range(i - 1, -1, -1)
                         if cs[j].get('pageStart') is not None), None)
            nxt = next((cs[j]['pageStart'] for j in range(i + 1, len(cs))
                        if cs[j].get('pageStart') is not None), None)
            pg = None
            if prev is not None and nxt is not None and 0 <= nxt - prev <= 2:
                pg = prev
            elif prev is not None and nxt is None:
                pg = prev
            elif nxt is not None and prev is None:
                pg = nxt
            if pg:
                c['pageStart'] = c['pageEnd'] = pg
                c['_comment'] = c.get('_comment', '') + f' | 쪽 번호 인접 chunk 로 보간(p.{pg})'
                n_interp += 1

        # ③ 남은 원문 보강 — 이제 쪽을 알므로 그 쪽에서 다시 시도
        for c in cs:
            if '보강' in c.get('_comment', '') or c.get('pageStart') is None:
                continue
            lead = c['content'].split('\n\n')[0]
            q = tokens(lead) + tokens(c['subsectionTitle']) + tokens(c['sectionTitle'])
            para = extract_para(aid, c['pageStart'], q)
            if para and norm(para)[:60] not in c['content']:
                c['content'] = c['content'].rstrip() + '\n\n' + para
                c['_comment'] = c.get('_comment', '') + f" | 논문 원문 보강 (PDF p.{c['pageStart']})"
                n_content += 1

        left_pg = sum(1 for c in cs if c.get('pageStart') is None)
        left_ct = sum(1 for c in cs if '보강' not in c.get('_comment', ''))
        doc['_unresolved'] = [u for u in doc['_unresolved'] if '쪽 번호 보강' not in u.get('title', '')]
        if left_pg or left_ct:
            doc['_unresolved'].append({'chunk': '-', 'title': '잔여 누락',
                                       'issue': f'쪽 미확정 {left_pg}건 / 논문 원문 미보강 {left_ct}건'})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2); f.write('\n')
        tot['sec'] += n_sec; tot['interp'] += n_interp; tot['content'] += n_content
        tot['left_pg'] += left_pg; tot['left_ct'] += left_ct
        print(f'{fname.replace("_ingest.json",""):24} 절제목 +{n_sec:2}  보간 +{n_interp:2}  '
              f'원문 +{n_content:2}   남은 쪽 {left_pg:2} / 원문 {left_ct:2}')
    print(f"\n합계 — 절제목 +{tot['sec']} / 보간 +{tot['interp']} / 원문 +{tot['content']}"
          f"  |  남은 쪽 {tot['left_pg']} / 원문 {tot['left_ct']}")


main()
