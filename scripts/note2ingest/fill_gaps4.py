#!/usr/bin/env python3
"""4차 — 제목만 있는 잔여 chunk. 논문에서 찾을 구절을 직접 지정합니다."""
import json
import os, os, re, sys
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
from fill_gaps import PAGES, norm
ING = os.environ.get('CODEATLAS_INGEST_DIR') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'database', 'ingest')

# 파일 -> chunkIndex -> (arxivId, 논문에서 찾을 구절)
TARGET = {
 'llama3_ingest.json': {
   11: ('2407.21783', 'temperature'),
   12: ('2407.21783', 'sampling'),
 },
 'resnet_ingest.json': {
   10: ('1512.03385', 'building block de'),
   34: ('1512.03385', '152-layer'),
   36: ('1512.03385', 'zero-padding shortcuts'),
   39: ('1512.03385', 'plain/residual architectures follow the form'),
   40: ('1512.03385', 'weight decay of 0.0001 and momentum'),
   46: ('1512.03385', 'initialize the weights as in'),
   48: ('1512.03385', 'Caffe'),
 },
 'yolo_ingest.json': {
   19: ('1506.02640', 'conditional class proba'),
 },
}

def window(aid, phrase, want=700):
    for pi, txt in enumerate(PAGES[aid]):
        t = re.sub(r'-\n', '', txt)
        flat = norm(t)
        k = flat.lower().find(phrase.lower())
        if k < 0:
            continue
        sents = re.split(r'(?<=[.!?])\s+', flat)
        pos, start = 0, 0
        for i, s in enumerate(sents):
            if pos <= k < pos + len(s) + 1:
                start = max(0, i - 1); break
            pos += len(s) + 1
        w, j = '', start
        while j < len(sents) and len(w) < want:
            w += sents[j] + ' '; j += 1
        return w.strip(), pi + 1
    return None, None

n = 0
for fname, table in TARGET.items():
    path = os.path.join(ING, fname)
    doc = json.load(open(path, encoding='utf-8')); cs = doc['papers'][0]['chunks']
    for cidx, (aid, phrase) in sorted(table.items()):
        c = next(x for x in cs if x['chunkIndex'] == cidx)
        if '보강' in c.get('_comment', ''):
            continue
        w, pg = window(aid, phrase)
        if not w:
            print(f'  ❌ {fname} {cidx}: "{phrase}" 못 찾음'); continue
        c['content'] = c['content'].rstrip() + '\n\n' + w
        c['_comment'] = c.get('_comment', '') + f' | 논문 원문 보강 (PDF p.{pg}, 지정 구절 "{phrase}")'
        if c.get('pageStart') is None:
            c['pageStart'] = c['pageEnd'] = pg
        n += 1
    left = sum(1 for x in cs if '보강' not in x.get('_comment', ''))
    lp = sum(1 for x in cs if x.get('pageStart') is None)
    doc['_unresolved'] = [u for u in doc['_unresolved'] if u.get('title') != '잔여 누락']
    if left or lp:
        doc['_unresolved'].append({'chunk': '-', 'title': '잔여 누락',
                                   'issue': f'쪽 미확정 {lp}건 / 논문 원문 미보강 {left}건'})
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2); f.write('\n')
print(f'보강 +{n}')
