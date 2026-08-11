#!/usr/bin/env python3
"""누락 채우기 — page 번호와 논문 원문 content.

논문 PDF(arXiv 공식 배포본)에서 쪽별 텍스트를 뽑아 두고,
  · pageStart/pageEnd 가 없는 chunk → 본문이 실린 쪽을 찾아 채움
  · 논문 원문이 안 붙은 chunk       → 그 쪽에서 해당 문단을 찾아 붙임
확신이 없으면 손대지 않고 _unresolved 에 남깁니다.
"""
import collections
import json
import os
import re

SC = os.path.dirname(os.path.abspath(__file__))
ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'
PAGES = json.load(open(os.path.join(SC, 'pdf_pages.json'), encoding='utf-8'))

FILES = {
    'attention_is_all_you_need_ingest.json': '1706.03762',
    'bert_ingest.json': '1810.04805', 'clip_ingest.json': '2103.00020',
    'llama3_ingest.json': '2407.21783', 'resnet_ingest.json': '1512.03385',
    'segment_anything_ingest.json': '2304.02643',
    'latent_diffusion_ingest.json': '2112.10752',
    'vision_transformer_ingest.json': '2010.11929', 'yolo_ingest.json': '1506.02640',
}

STOP = set('the a an of and or to in for with on is are be we our this that as by at from it its '
           'can will using use used which not have has more than then also such each other'.split())


def tokens(s):
    """검색 키 — 영문 기술어와 숫자만 남깁니다(한국어 제목에서도 잘 나옵니다)."""
    s = re.sub(r'[^A-Za-z0-9_.\-]+', ' ', s)
    out = []
    for t in s.split():
        t = t.strip('.-_').lower()
        if len(t) < 3 or t in STOP:
            continue
        out.append(t)
    return out


def page_text(aid, i):
    return PAGES[aid][i]


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def best_page(aid, query_tokens):
    """토큰 겹침이 가장 큰 쪽. (쪽번호, 점수, 2위점수)"""
    if not query_tokens:
        return None, 0, 0
    q = collections.Counter(query_tokens)
    scores = []
    for i, txt in enumerate(PAGES[aid]):
        low = txt.lower()
        s = sum(c for t, c in q.items() if t in low)
        # 흔한 토큰은 가중치를 낮춘다
        rare = sum(1 for t in q if t in low and sum(1 for p in PAGES[aid] if t in p.lower()) <= 3)
        scores.append((s + rare * 2, i))
    scores.sort(reverse=True)
    top, second = scores[0], scores[1] if len(scores) > 1 else (0, -1)
    return top[1] + 1, top[0], second[0]


def extract_para(aid, page_no, query_tokens, want=700):
    """해당 쪽에서 질의 토큰이 가장 몰려 있는 구간을 문장 단위로 잘라 옵니다."""
    txt = page_text(aid, page_no - 1)
    txt = re.sub(r'-\n', '', txt)              # 줄 끝 하이픈 이어붙이기
    sents = re.split(r'(?<=[.!?])\s+', norm(txt))
    if not sents:
        return None
    q = set(query_tokens)
    best, bi = -1, 0
    for i in range(len(sents)):
        window, j = '', i
        while j < len(sents) and len(window) < want:
            window += sents[j] + ' '
            j += 1
        low = window.lower()
        score = sum(1 for t in q if t in low)
        if score > best:
            best, bi = score, i
    window, j = '', bi
    while j < len(sents) and len(window) < want:
        window += sents[j] + ' '
        j += 1
    window = window.strip()
    return window if len(window) > 120 and best >= 2 else None


def main():
    tot = collections.Counter()
    for fname, aid in FILES.items():
        path = os.path.join(ING, fname)
        doc = json.load(open(path, encoding='utf-8'))
        p = doc['papers'][0]
        n_page = n_content = n_skip = 0

        for c in p['chunks']:
            note = c['content'].split('\n\n논문 원문')[0]
            lead = c['content'].split('\n\n')[0]        # 보강 전 노트 텍스트
            q = tokens(lead) + tokens(c['subsectionTitle']) + tokens(c['sectionTitle'])
            q = [t for t in q if t]

            # ① 쪽 번호
            if c.get('pageStart') is None:
                pg, s1, s2 = best_page(aid, q)
                if pg and s1 >= 6 and s1 >= s2 + 3:      # 2위와 뚜렷이 벌어질 때만
                    c['pageStart'] = c['pageEnd'] = pg
                    c['_comment'] = c.get('_comment', '') + f' | 쪽 번호 PDF 대조로 채움(p.{pg})'
                    n_page += 1
                else:
                    n_skip += 1

            # ② 논문 원문 보강
            if '보강' not in c.get('_comment', ''):
                pg = c.get('pageStart')
                if pg is None:
                    pg, s1, s2 = best_page(aid, q)
                    if not (pg and s1 >= 6):
                        continue
                para = extract_para(aid, pg, q)
                if para and norm(para)[:60] not in c['content']:
                    c['content'] = c['content'].rstrip() + '\n\n' + para
                    c['_comment'] = c.get('_comment', '') + f' | 논문 원문 보강 (PDF p.{pg})'
                    n_content += 1

        doc['_unresolved'] = [u for u in doc['_unresolved'] if 'content 보강' not in u.get('title', '')]
        if n_skip:
            doc['_unresolved'].append({
                'chunk': '-', 'title': '쪽 번호 보강',
                'issue': f'{n_skip}개 chunk 는 PDF 대조로도 쪽을 특정하지 못해 비워 둠'})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        L = sorted(len(c['content']) for c in p['chunks'])
        tot['page'] += n_page
        tot['content'] += n_content
        tot['skip'] += n_skip
        print(f'{fname.replace("_ingest.json",""):24} 쪽 +{n_page:3}  원문 +{n_content:3}  '
              f'미확정 {n_skip:3}   content 중앙값 {L[len(L)//2]:5}자')
    print(f'\n합계 — 쪽 +{tot["page"]} / 원문 +{tot["content"]} / 미확정 {tot["skip"]}')


if __name__ == '__main__':
    main()
