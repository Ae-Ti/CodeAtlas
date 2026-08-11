#!/usr/bin/env python3
"""남은 미매핑 chunk 보강 — 참조 구현 저장소 추가 + 주제별 수동 매핑.

공식 저장소만으로는 대응이 안 되는 세 편에 널리 쓰이는 참조 구현을 COMMUNITY 로 붙입니다.
  ViT    : 공식(vit_jax)이 Flax 압축 구현이라 attention 내부가 한 메서드에 뭉쳐 있음
  ResNet : 공식 저장소가 Caffe prototxt 배포본뿐 (학습 코드 없음)
  U-Net  : 공식 구현이 없는 논문 (저자 배포본은 Caffe 바이너리)
YOLO 는 공식 darknet 안에서 심볼을 더 찾아 붙입니다.
"""
import json
import os
import sys

SC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SC)
from locate import Repo                                  # noqa: E402

ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'

SECONDARY = {
    'ViT2':    dict(slug='lucidrains/vit-pytorch', branch='main', stars=25477,
                    sha='bb13e27ee5b30ddd3e09c2e23c30ec2c17683d35', license='MIT',
                    lang='Python', relation='COMMUNITY'),
    'ResNet2': dict(slug='pytorch/vision', branch='main', stars=17857,
                    sha='0fba2e84fe255a2fcd81bd0b10c74d7fca99a89f', license='BSD-3-Clause',
                    lang='Python', relation='COMMUNITY'),
    'Unet2':   dict(slug='milesial/Pytorch-UNet', branch='master', stars=11590,
                    sha='21d7850f2af30a9695bbeea75f3136aa538cfc4a', license='GPL-3.0',
                    lang='Python', relation='COMMUNITY'),
}

# 파일: chunkIndex -> (저장소키, 경로, 심볼, 부모, 근거)
EXTRA = {
 'vision_transformer_ingest.json': {
   2:  ('ViT2', 'vit_pytorch/vit.py', '__init__', 'ViT',
        'Rearrange 로 이미지를 patch 단위로 잘라 1차원으로 펼치는 부분'),
   5:  ('Vision', 'vit_jax/models_vit.py', '__call__', 'AddPositionEmbs',
        '학습 가능한 위치 임베딩을 patch 임베딩에 더하는 전용 모듈'),
   6:  ('ViT2', 'vit_pytorch/vit.py', 'forward', 'ViT',
        'patch 임베딩 + cls token + 위치 임베딩을 만들어 Transformer 에 넣는 입력 구성'),
   9:  ('ViT2', 'vit_pytorch/vit.py', '__init__', 'Attention',
        'to_qkv 하나로 Q·K·V 를 한 번에 projection 하도록 정의'),
   10: ('ViT2', 'vit_pytorch/vit.py', 'forward', 'Attention',
        'QK^T 를 scale 로 나누고 softmax 후 V 와 곱하는 scaled dot-product attention'),
   11: ('ViT2', 'vit_pytorch/vit.py', 'forward', 'Attention',
        'attend(=Softmax) 로 attention 확률을 만드는 지점'),
   12: ('ViT2', 'vit_pytorch/vit.py', '__init__', 'Attention',
        'to_out 으로 head 를 합친 뒤 최종 projection 을 정의'),
   14: ('ViT2', 'vit_pytorch/vit.py', '__init__', 'Transformer',
        'block 마다 LayerNorm 을 두는 pre-norm 구조'),
   16: ('ViT2', 'vit_pytorch/vit.py', '__init__', 'FeedForward',
        'MLP 안에서 GELU 를 활성함수로 사용'),
   21: ('ViT2', 'vit_pytorch/vit.py', '__init__', 'ViT',
        'dim·depth·heads·mlp_dim 을 인자로 받아 Base/Large/Huge 구성을 만드는 지점'),
   24: ('Vision', 'vit_jax/input_pipeline.py', 'get_datasets', None,
        '학습·평가 데이터셋을 구성하는 입력 파이프라인'),
   25: ('Vision', 'vit_jax/input_pipeline.py', 'get_data', None,
        'crop·flip 등 전처리와 배치 구성을 담당'),
   26: ('Vision', 'vit_jax/train.py', 'make_update_fn', None,
        'optimizer 로 파라미터를 갱신하는 학습 스텝 정의'),
   27: ('Vision', 'vit_jax/train.py', 'train_and_evaluate', None,
        'warmup·decay 를 포함한 learning rate schedule 이 설정되는 학습 루프'),
   30: ('Vision', 'vit_jax/checkpoint.py', 'load_pretrained', None,
        '사전학습 체크포인트를 불러오고 위치 임베딩을 보간해 맞추는 부분'),
 },
 'resnet_ingest.json': {
   11: ('ResNet2', 'torchvision/models/resnet.py', 'forward', 'BasicBlock',
        'conv→bn→relu 두 계층을 지난 출력에 identity 를 더하는 residual function'),
   16: ('ResNet2', 'torchvision/models/resnet.py', '_make_layer', 'ResNet',
        'stride 로 feature map 을 줄이면서 채널을 2배로 늘리는 plain network 설계 규칙'),
   21: ('ResNet2', 'torchvision/models/resnet.py', '__init__', 'BasicBlock',
        '차원이 다를 때 downsample 로 shortcut 을 맞추는 부분'),
   26: ('ResNet2', 'torchvision/models/resnet.py', '__init__', 'ResNet',
        'kaiming_normal_ 로 전체 conv 가중치를 초기화'),
   33: ('ResNet2', 'torchvision/models/resnet.py', 'resnet101', None,
        'Bottleneck 을 [3,4,23,3] 으로 쌓는 ResNet-101 구성'),
   34: ('ResNet2', 'torchvision/models/resnet.py', 'resnet152', None,
        'Bottleneck 을 [3,8,36,3] 으로 쌓는 ResNet-152 구성'),
   35: ('ResNet2', 'torchvision/models/resnet.py', 'resnet18', None,
        'BasicBlock 을 [2,2,2,2] 로 쌓는 ResNet-18 구성'),
   36: ('ResNet2', 'torchvision/models/resnet.py', '_make_layer', 'ResNet',
        'shortcut 차원이 다를 때만 1x1 conv 를 두는 Option B 방식'),
   38: ('ResNet2', 'torchvision/models/resnet.py', '__init__', 'Bottleneck',
        '1x1 로 차원을 줄이고 3x3 을 거친 뒤 1x1 로 다시 확장하는 구조'),
 },
 'unet_ingest.json': {
   16: ('Unet2', 'unet/unet_parts.py', 'forward', 'Up',
        'contracting path 의 고해상도 feature 를 잘라 붙여(concat) 결합'),
   19: ('Unet2', 'unet/unet_parts.py', '__init__', 'Up',
        'upsample 후 채널 수를 유지한 채 conv 를 두는 expansive path 구성'),
   20: ('Unet2', 'unet/unet_model.py', 'forward', 'UNet',
        'down 4단계와 up 4단계가 대칭을 이루는 U 자 구조'),
   28: ('Unet2', 'unet/unet_model.py', '__init__', 'UNet',
        'DoubleConv·Down·Up·OutConv 로 전체 convolution 계층을 구성'),
   30: ('Unet2', 'train.py', 'train_model', None,
        'optimizer 와 학습 루프가 정의된 부분'),
   32: ('Unet2', 'train.py', 'get_args', None,
        'batch size 등 학습 하이퍼파라미터를 받는 지점'),
   34: ('Unet2', 'utils/dice_score.py', 'dice_loss', None,
        'softmax 출력에 대한 픽셀 단위 손실 계산'),
 },
 'yolo_ingest.json': {
   10: ('YOLO', 'src/detection_layer.c', 'make_detection_layer', None,
        'side(S)·n(B)·classes 로 S×S grid 검출 계층을 만드는 부분'),
   12: ('YOLO', 'src/detection_layer.c', 'make_detection_layer', None,
        'cell 당 n 개 box 와 confidence 를 두도록 출력 크기를 잡는 부분'),
   13: ('YOLO', 'src/detection_layer.c', 'forward_detection_layer', None,
        '예측 box 와 정답의 IoU 를 confidence 목표값으로 쓰는 부분'),
   14: ('YOLO', 'src/detection_layer.c', 'forward_detection_layer', None,
        'x·y·w·h 와 confidence 다섯 값에 대해 delta 를 계산'),
   19: ('YOLO', 'src/detection_layer.c', 'get_detection_detections', None,
        'class 확률과 box confidence 를 곱해 class-specific confidence 를 만드는 부분'),
   33: ('YOLO', 'src/activations.c', 'get_activation', None,
        'linear 를 포함한 활성함수 종류를 문자열로 선택'),
   34: ('YOLO', 'src/activations.c', 'activate', None,
        'LEAKY 분기에서 기울기 0.1 을 적용'),
   38: ('YOLO', 'src/detection_layer.c', 'forward_detection_layer', None,
        'IoU 가 가장 큰 predictor 를 골라 그 box 에만 좌표 손실을 주는 부분'),
   51: ('YOLO', 'src/network.c', 'forward_network', None,
        '이미지 한 장을 network 에 한 번 통과시키는 단일 평가 경로'),
   52: ('YOLO', 'src/detection_layer.c', 'make_detection_layer', None,
        'S×S×B 개 box 가 한 번에 나오는 출력 크기'),
   53: ('YOLO', 'src/box.c', 'do_nms_sort', None,
        'IoU 기준으로 겹치는 box 를 제거하는 non-maximal suppression'),
   54: ('YOLO', 'src/box.c', 'do_nms_sort', None,
        'NMS 로 중복 검출을 정리해 정확도를 올리는 부분'),
 },
}

REPO_KEY_OF_PAPER = {'vision_transformer_ingest.json': 'Vision', 'resnet_ingest.json': 'ResNet',
                     'unet_ingest.json': 'U-net', 'yolo_ingest.json': 'YOLO'}


def resolve_overlaps(paper):
    """§4 규칙 3 — 자식이 인덱싱된 부모 블록을 지우고 그 정답을 자식으로 재지정."""
    dropped = []
    for r in paper['repositories']:
        bs = r['codeBlocks']
        parents = [a for a in bs if any(
            b is not a and b['filePath'] == a['filePath']
            and a['startLine'] <= b['startLine'] and a['endLine'] >= b['endLine'] for b in bs)]
        for a in parents:
            kids = [b for b in bs if b is not a and b not in parents
                    and b['filePath'] == a['filePath']
                    and a['startLine'] <= b['startLine'] and a['endLine'] >= b['endLine']]
            if not kids:
                continue
            best = min(kids, key=lambda b: b['endLine'] - b['startLine'])
            for c in paper['chunks']:
                for m in c.get('mappedCode') or []:
                    if m['filePath'] == a['filePath'] and m['startLine'] == a['startLine']:
                        m['symbolName'], m['startLine'] = best['symbolName'], best['startLine']
            dropped.append(a['symbolName'])
            bs.remove(a)
        # 재지정으로 생긴 중복 mappedCode 정리
        for c in paper['chunks']:
            seen, keep = set(), []
            for m in c.get('mappedCode') or []:
                k = (m['githubUrl'], m['filePath'], m['symbolName'], m['startLine'])
                if k not in seen:
                    seen.add(k)
                    keep.append(m)
            if 'mappedCode' in c:
                c['mappedCode'] = keep
    return dropped


def main():
    repos = {}
    for fname, table in EXTRA.items():
        path = os.path.join(ING, fname)
        doc = json.load(open(path, encoding='utf-8'))
        paper = doc['papers'][0]
        added_blocks = added_maps = skipped = 0

        for cidx, (rkey, fp, sym, parent, reason) in sorted(table.items()):
            if rkey not in repos:
                repos[rkey] = Repo(os.path.join(SC, 'src'), rkey)
            repo = repos[rkey]
            if fp not in repo.files:
                print(f'  ❌ {fname} chunk {cidx}: {fp} 없음')
                skipped += 1
                continue
            hits = [s for s in repo.files[fp]['symbols']
                    if s[0] == sym and (parent is None or s[2] == parent)]
            if len(hits) != 1:
                print(f'  ❌ {fname} chunk {cidx}: {fp} 의 {parent}.{sym} 후보 {len(hits)}개')
                skipped += 1
                continue
            name, kind, par, st, en = hits[0]

            if rkey in SECONDARY:
                info = SECONDARY[rkey]
                url = f'https://github.com/{info["slug"]}'
                target = next((r for r in paper['repositories'] if r['githubUrl'] == url), None)
                if target is None:
                    owner, rname = info['slug'].split('/')
                    target = {'githubUrl': url, 'ownerName': owner, 'repositoryName': rname,
                              'defaultBranch': info['branch'], 'commitHash': info['sha'],
                              'licenseName': info['license'], 'primaryLanguage': info['lang'],
                              'starCount': info['stars'], 'relationType': info['relation'],
                              'isPrimary': False, 'codeBlocks': []}
                    paper['repositories'].append(target)
                sha = info['sha']
            else:
                target = paper['repositories'][0]
                sha = target['commitHash']

            key = (fp, name, st)
            if not any((b['filePath'], b['symbolName'], b['startLine']) == key
                       for b in target['codeBlocks']):
                target['codeBlocks'].append({
                    'filePath': fp, 'symbolName': name,
                    'symbolType': kind, 'parentSymbolName': par,
                    'programmingLanguage': repo.lang(fp), 'startLine': st, 'endLine': en,
                    'codeContent': repo.slice(fp, st, en),
                    '_comment': f'Verbatim from {target["githubUrl"]} @ {sha[:7]} — {fp}:{st}-{en}',
                })
                added_blocks += 1

            chunk = next(c for c in paper['chunks'] if c['chunkIndex'] == cidx)
            entry = {'githubUrl': target['githubUrl'], 'filePath': fp, 'symbolName': name,
                     'startLine': st, 'reason': reason}
            chunk.setdefault('mappedCode', [])
            if not any(m['filePath'] == fp and m['startLine'] == st
                       for m in chunk['mappedCode']):
                chunk['mappedCode'].append(entry)
                added_maps += 1

        dropped = resolve_overlaps(paper)
        if dropped:
            doc['_unresolved'].append({
                'chunk': '-', 'title': '입도 정리 (§4 규칙 3)',
                'issue': f'자식 심볼이 인덱싱된 부모 블록 {len(dropped)}개를 제거하고 정답 재지정: '
                         f'{sorted(dropped)}'})

        doc['_unresolved'].append({
            'chunk': '-', 'title': '참조 구현 보강',
            'issue': f'공식 저장소로 대응이 안 되는 chunk {added_maps}건을 참조 구현/추가 심볼로 매핑'})
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        mapped = sum(1 for c in paper['chunks'] if c.get('mappedCode'))
        nb = sum(len(r['codeBlocks']) for r in paper['repositories'])
        print(f'{fname.replace("_ingest.json",""):20} 저장소 {len(paper["repositories"])}  '
              f'블록 +{added_blocks} → {nb}  매핑 chunk {mapped}/{len(paper["chunks"])}  '
              f'실패 {skipped}')


if __name__ == '__main__':
    main()
