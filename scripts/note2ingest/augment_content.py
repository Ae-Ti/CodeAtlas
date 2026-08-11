#!/usr/bin/env python3
"""문제 3 — chunk content 를 논문 원문 문단으로 보강.

검수 리포트 §5에서 Attention 논문에 적용한 것과 같은 처리입니다.
  · 노트 인용문이 있으면 → 논문 원문에서 그 문단을 찾아 덧붙임
  · 인용문이 없으면    → 노트의 '논문 위치'(Section) 로 해당 절의 첫 문단을 붙임
아무 것도 못 찾으면 손대지 않고 _unresolved 에 남깁니다.
"""
import collections
import html
import json
import os
import re
import sys

SC = os.path.dirname(os.path.abspath(__file__))
ING = os.environ.get('CODEATLAS_INGEST_DIR') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'database', 'ingest')

FILES = {
    'bert_ingest.json': '1810.04805', 'clip_ingest.json': '2103.00020',
    'llama3_ingest.json': '2407.21783', 'resnet_ingest.json': '1512.03385',
    'segment_anything_ingest.json': '2304.02643', 'latent_diffusion_ingest.json': '2112.10752',
    'unet_ingest.json': '1505.04597', 'vision_transformer_ingest.json': '2010.11929',
    'yolo_ingest.json': '1506.02640',
}


def plain(h):
    h = re.sub(r'<math[^>]*alttext="([^"]*)"[^>]*>.*?</math>',
               lambda m: ' ' + html.unescape(m.group(1)) + ' ', h, flags=re.S)
    h = re.sub(r'<(script|style)\b.*?</\1>', '', h, flags=re.S)
    h = re.sub(r'<[^>]+>', '', h)
    return re.sub(r'[ \t]+', ' ', html.unescape(h)).strip()


def load_paper(arxiv):
    src = open(os.path.join(SC, 'papers', arxiv + '.html'), encoding='utf-8').read()
    secs = [(m.start(), plain(m.group(2))) for m in re.finditer(
        r'<h([2-5])[^>]*class="ltx_title ltx_title_(?:section|subsection|subsubsection|paragraph)"'
        r'[^>]*>(.*?)</h\1>', src, re.S)]
    paras = [(m.start(), plain(m.group(1)))
             for m in re.finditer(r'<p [^>]*class="ltx_p"[^>]*>(.*?)</p>', src, re.S)]
    paras = [(p, t) for p, t in paras if len(t) > 60]

    def sec_of(pos):
        cur = 'Abstract'
        for sp, st in secs:
            if sp < pos:
                cur = st
            else:
                break
        return cur
    return [{'pos': p, 'section': sec_of(p), 'text': t} for p, t in paras], secs


def norm(s):
    s = s.replace('“', '"').replace('”', '"').replace('’', "'")
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def find_para(quote, nparas):
    words = norm(quote).split()
    if len(words) < 5:
        return None
    for n in range(min(12, len(words)), 4, -1):
        for i in range(len(words) - n + 1):
            sh = ' '.join(words[i:i + n])
            hits = [j for j, p in enumerate(nparas) if sh in p]
            if hits:
                return hits[0], n
    return None


SECNUM = re.compile(r'(?:Section|Sec\.?|§)\s*([0-9]+(?:\.[0-9]+)*)', re.I)


def section_paras(loc, paras):
    """'Section 3.2' → 그 절에 속한 문단 인덱스 전부."""
    if not loc:
        return []
    m = SECNUM.search(loc)
    if not m:
        return []
    num = m.group(1)
    out = [i for i, p in enumerate(paras)
           if p['section'].strip().startswith(num + ' ')
           or p['section'].strip().startswith(num + '.')
           or p['section'].strip() == num]
    if not out:                       # 3.2.1 처럼 더 깊은 절만 있는 경우 상위 번호로 재시도
        out = [i for i, p in enumerate(paras) if p['section'].strip().startswith(num)]
    return out


def main():
    total = collections.Counter()
    for fname, arxiv in FILES.items():
        path = os.path.join(ING, fname)
        doc = json.load(open(path, encoding='utf-8'))
        paras, _ = load_paper(arxiv)
        nparas = [norm(p['text']) for p in paras]
        p0 = doc['papers'][0]
        added = sec_added = missed = 0

        pending = []                     # 절 단위 보강 대기 (같은 절끼리 문단을 나눠 씁니다)
        for c in p0['chunks']:
            cmt = c.get('_comment', '')
            hit = None if 'content=구현 설명' in cmt else find_para(c['content'], nparas)
            if hit:
                j, _n = hit
                if paras[j]['text'] not in c['content']:
                    c['content'] = c['content'].rstrip() + '\n\n' + paras[j]['text']
                    c['sectionTitle'] = paras[j]['section'][:255]
                    c['_comment'] = cmt + f' | 논문 원문 문단 보강 (ar5iv {arxiv})'
                    added += 1
                continue
            pending.append(c)

        # 같은 절을 가리키는 chunk 들에 그 절의 문단을 순서대로 배분
        by_sec = collections.OrderedDict()
        for c in pending:
            key = c.get('sectionTitle', '')
            by_sec.setdefault(key, []).append(c)
        for key, group in by_sec.items():
            idxs = section_paras(key, paras)
            if not idxs:
                missed += len(group)
                continue
            for k, c in enumerate(group):
                j = idxs[k % len(idxs)]
                c['content'] = c['content'].rstrip() + '\n\n' + paras[j]['text']
                c['sectionTitle'] = paras[j]['section'][:255]
                c['_comment'] = (c.get('_comment', '')
                                 + f' | 논문 원문 절 문단으로 보강 (ar5iv {arxiv}, 인용문 없음)')
                sec_added += 1

        doc['_unresolved'] = [u for u in doc['_unresolved']
                              if '논문 원문 인용이 없어' not in u['issue']]
        if missed:
            doc['_unresolved'].append({
                'chunk': '-', 'title': 'content 보강',
                'issue': f'{missed}개 chunk 는 노트 인용문·절 번호 어느 쪽으로도 논문 원문을 '
                         f'특정하지 못해 노트 설명을 그대로 둠'})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        L = sorted(len(c['content']) for c in p0['chunks'])
        total['added'] += added
        total['sec'] += sec_added
        total['missed'] += missed
        print(f'{fname.replace("_ingest.json",""):20} 인용매칭 {added:3}  절보강 {sec_added:3}  '
              f'미보강 {missed:3}   content 중앙값 {L[len(L)//2]:5}자')
    print(f'\n합계 — 인용매칭 {total["added"]} / 절보강 {total["sec"]} / 미보강 {total["missed"]}')


if __name__ == '__main__':

    main()
