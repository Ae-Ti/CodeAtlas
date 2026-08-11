#!/usr/bin/env python3
"""라이선스 실측값 반영 + U-Net 참조 구현을 GPL → MIT 로 교체."""
import json, os, sys
SC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SC)
from locate import Repo

ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'

# LICENSE 파일 실측 결과
LICENSE = {
 'https://github.com/jadore801120/attention-is-all-you-need-pytorch': 'MIT',
 'https://github.com/mlfoundations/open_clip': 'MIT',
 'https://github.com/pjreddie/darknet': 'YOLO LICENSE v2 (public-domain style)',
 'https://github.com/meta-llama/llama3': 'Meta Llama 3 Community License',
 'https://github.com/Miltos-90/UNet_Biomedical_Image_Segmentation': 'NONE (라이선스 파일 없음)',
}

NEW = dict(slug='mateuszbuda/brain-segmentation-pytorch', branch='master', stars=775,
           sha='d45f8908ab2f0246ba204c702a6161c9eb25f902', license='MIT',
           lang='Python', relation='COMMUNITY')

# chunkIndex -> (경로, 심볼, 부모, 근거)
REMAP = {
 16: ('unet.py', 'forward', 'UNet', 'torch.cat 으로 contracting path 의 고해상도 feature 를 결합'),
 19: ('unet.py', '__init__', 'UNet', 'ConvTranspose2d 로 업샘플하며 채널을 늘리는 expansive path 구성'),
 20: ('unet.py', 'forward', 'UNet', 'encoder 4단계와 decoder 4단계가 대칭을 이루는 U 자 구조'),
 28: ('unet.py', '_block', 'UNet', '3x3 conv 두 개를 한 블록으로 묶어 전체 convolution 계층을 구성'),
 30: ('train.py', 'main', None, 'optimizer 를 만들고 epoch 루프를 도는 학습 진입점'),
 32: ('train.py', 'data_loaders', None, 'batch size 를 받아 DataLoader 를 만드는 부분'),
 34: ('loss.py', 'forward', 'DiceLoss', '픽셀 단위 확률 출력에 대한 손실 계산'),
}

def main():
    # 1) 라이선스
    n = 0
    for fn in os.listdir(ING):
        if not fn.endswith('_ingest.json'):
            continue
        path = os.path.join(ING, fn)
        doc = json.load(open(path, encoding='utf-8'))
        changed = False
        for r in doc['papers'][0]['repositories']:
            new = LICENSE.get(r['githubUrl'])
            if new and r.get('licenseName') != new:
                r['licenseName'] = new
                changed = True
                n += 1
        if changed:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2); f.write('\n')
    print(f'라이선스 갱신 {n}건')

    # 2) U-Net 참조 구현 교체
    path = os.path.join(ING, 'unet_ingest.json')
    doc = json.load(open(path, encoding='utf-8'))
    paper = doc['papers'][0]
    old_url = 'https://github.com/milesial/Pytorch-UNet'
    paper['repositories'] = [r for r in paper['repositories'] if r['githubUrl'] != old_url]
    for c in paper['chunks']:
        if c.get('mappedCode'):
            c['mappedCode'] = [m for m in c['mappedCode'] if m['githubUrl'] != old_url]
            if not c['mappedCode']:
                del c['mappedCode']

    repo = Repo(os.path.join(SC, 'src'), 'UnetBrain')
    owner, name = NEW['slug'].split('/')
    url = f'https://github.com/{NEW["slug"]}'
    target = {'githubUrl': url, 'ownerName': owner, 'repositoryName': name,
              'defaultBranch': NEW['branch'], 'commitHash': NEW['sha'],
              'licenseName': NEW['license'], 'primaryLanguage': NEW['lang'],
              'starCount': NEW['stars'], 'relationType': NEW['relation'],
              'isPrimary': False, 'codeBlocks': []}
    paper['repositories'].append(target)
    added = 0
    for cidx, (fp, sym, parent, reason) in sorted(REMAP.items()):
        hits = [s for s in repo.files[fp]['symbols']
                if s[0] == sym and (parent is None or s[2] == parent)]
        if len(hits) != 1:
            print(f'  ❌ chunk {cidx}: {fp} {parent}.{sym} 후보 {len(hits)}')
            continue
        nm, kind, par, st, en = hits[0]
        key = (fp, nm, st)
        if not any((b['filePath'], b['symbolName'], b['startLine']) == key
                   for b in target['codeBlocks']):
            target['codeBlocks'].append({
                'filePath': fp, 'symbolName': nm, 'symbolType': kind, 'parentSymbolName': par,
                'programmingLanguage': 'Python', 'startLine': st, 'endLine': en,
                'codeContent': repo.slice(fp, st, en),
                '_comment': f'Verbatim from {url} @ {NEW["sha"][:7]} — {fp}:{st}-{en}'})
        chunk = next(c for c in paper['chunks'] if c['chunkIndex'] == cidx)
        chunk.setdefault('mappedCode', []).append(
            {'githubUrl': url, 'filePath': fp, 'symbolName': nm, 'startLine': st, 'reason': reason})
        added += 1
    doc['_unresolved'].append({'chunk': '-', 'title': '라이선스 정리',
                               'issue': 'GPL-3.0 인 milesial/Pytorch-UNet 을 MIT 인 '
                                        'mateuszbuda/brain-segmentation-pytorch 로 교체'})
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2); f.write('\n')
    print(f'U-Net 참조 구현 교체: milesial(GPL-3.0) → brain-segmentation-pytorch(MIT), 매핑 {added}건')

main()
