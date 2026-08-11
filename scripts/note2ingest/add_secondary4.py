#!/usr/bin/env python3
"""4차 보강 — 마지막으로 붙일 수 있는 chunk."""
import sys, os
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
import add_secondary as base
Y='YOLO'; R2='ResNet2'; A='Attn'
CFG='cfg/yolov1.cfg'; DL='src/detection_layer.c'; NW='src/network.c'
FR='torchvision/models/detection/faster_rcnn.py'
base.EXTRA = {
 'yolo_ingest.json': {
   3:  (Y, NW, 'forward_network', None, '이미지 한 장에 network 를 한 번만 통과시키는 경로'),
   20: (Y, CFG, 'detection[32]', None, 'side·num·classes 로 S×S×(B*5+C) 출력을 정의하는 [detection] 섹션'),
   23: (Y, CFG, 'net[0]', None, 'height=448 width=448 입력 크기'),
   29: (Y, CFG, 'net[0]', None, 'pretraining·학습 하이퍼파라미터가 모인 [net] 섹션'),
   31: (Y, CFG, 'net[0]', None, '검출 학습 시 입력 해상도를 448 로 두는 설정'),
   35: (Y, DL, 'forward_detection_layer', None, '예측과 정답의 차를 제곱해 더하는 sum-squared error'),
   42: (Y, CFG, 'net[0]', None, 'max_batches 로 학습 반복 횟수를 지정'),
   48: (Y, CFG, 'dropout[30]', None, 'probability=.5 인 [dropout] 계층'),
   49: (Y, CFG, 'net[0]', None, 'saturation·exposure 등 데이터 증강 파라미터'),
 },
 'resnet_ingest.json': {
   55: (R2, FR, '__init__', 'FasterRCNN', 'box_nms_thresh 로 NMS IoU 임계값을 두는 부분'),
   61: (R2, FR, '__init__', 'FasterRCNN', 'rpn_batch_size_per_image 와 positive_fraction 으로 anchor 를 표집'),
 },
 'attention_is_all_you_need_ingest.json': {
   35: (A, 'train.py', 'prepare_dataloaders_from_bpe_files', None, 'batch size 로 토큰 수를 맞춰 배치를 만드는 부분'),
   55: (A, 'transformer/SubLayers.py', 'forward', 'MultiHeadAttention', 'residual 합에 layer_norm 을 적용'),
 },
}
base.REPO_KEY_OF_PAPER = {}
base.main()
