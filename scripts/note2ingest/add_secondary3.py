#!/usr/bin/env python3
"""3차 보강 — 남은 미매핑 chunk 를 주제별로 붙입니다."""
import sys, os
SC = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, SC)
import add_secondary as base

Y='YOLO'; R2='ResNet2'; V='Vision'; V2='ViT2'; C2='CLIP2'; S='Stable'; A='Attn'
base.SECONDARY['ResNet2']['relation']='COMMUNITY'
CFG='cfg/yolov1.cfg'; DL='src/detection_layer.c'; NW='src/network.c'
FR='torchvision/models/detection/faster_rcnn.py'; RT='references/classification/train.py'
PS='torchvision/transforms/_presets.py'

base.EXTRA = {
 'yolo_ingest.json': {
   1:  (Y, NW, 'train_network', None, 'detection 전체를 하나의 network 로 두고 end-to-end 로 학습시키는 루프'),
   2:  (Y, CFG, 'net[0]', None, 'width=448 height=448 로 입력 해상도를 지정'),
   9:  (Y, DL, 'make_detection_layer', None, 'box 좌표·confidence·class 를 한 계층의 출력으로 통합'),
   11: (Y, DL, 'forward_detection_layer', None, '객체 중심이 속한 cell 만 책임지도록 delta 를 주는 부분'),
   15: (Y, DL, 'forward_detection_layer', None, 'x·y 를 cell 기준 offset 으로 다루는 부분'),
   16: (Y, DL, 'get_detection_detections', None, 'w·h 를 전체 이미지 비율로 되돌려 box 를 만드는 부분'),
   17: (Y, DL, 'get_detection_detections', None, 'cell 의 class 확률과 box confidence 를 곱하는 부분'),
   18: (Y, DL, 'make_detection_layer', None, 'class 확률을 box 별이 아니라 cell 당 한 세트로 잡는 출력 크기'),
   20: (Y, DL, 'make_detection_layer', None, 'S×S×(B*5+C) 크기의 출력 텐서를 만드는 부분'),
   25: (Y, CFG, 'maxpool[2]', None, 'size=2 stride=2 max pooling 계층'),
   28: (Y, CFG, 'net[0]', None, 'pretraining 해상도와 학습 하이퍼파라미터가 모여 있는 [net] 섹션'),
   32: (Y, DL, 'forward_detection_layer', None, 'w·h 를 0~1 범위로 다루며 손실을 계산하는 부분'),
   37: (Y, DL, 'forward_detection_layer', None, 'w·h 에 제곱근을 취해 크기 차이를 완화하는 부분'),
   40: (Y, DL, 'forward_detection_layer', None, '객체가 있는 cell 에만 classification 손실을 주는 부분'),
   41: (Y, DL, 'forward_detection_layer', None, 'IoU 가 가장 큰 predictor 에만 좌표 손실을 주는 부분'),
   44: (Y, CFG, 'net[0]', None, 'batch=64 등 학습 배치 설정'),
   45: (Y, CFG, 'net[0]', None, 'momentum=0.9 설정'),
   46: (Y, CFG, 'net[0]', None, 'decay=0.0005 (weight decay) 설정'),
 },
 'resnet_ingest.json': {
   2:  (R2, 'torchvision/models/resnet.py', 'resnet152', None, 'Bottleneck 을 [3,8,36,3] 으로 쌓아 152층을 구성'),
   8:  (R2, RT, 'train_one_epoch', None, 'SGD 로 역전파해 전체 network 를 end-to-end 로 갱신하는 루프'),
   24: (R2, PS, '__init__', 'ImageClassification', 'resize·crop 크기를 지정하는 전처리 프리셋'),
   25: (R2, PS, 'forward', 'ImageClassification', 'crop 후 정규화(mean subtraction)를 적용하는 부분'),
   27: (R2, RT, 'main', None, 'batch size 와 optimizer 를 설정해 학습을 시작하는 진입점'),
   28: (R2, RT, 'get_args_parser', None, 'learning rate·weight decay·momentum 기본값이 정의된 곳'),
   49: (R2, FR, '__init__', 'FasterRCNN', 'backbone 을 RPN 과 head 가 공유하도록 구성'),
   50: (R2, FR, '_default_anchorgen', None, 'RPN 이 쓸 anchor 를 생성하는 부분'),
   51: (R2, FR, 'forward', 'TwoMLPHead', 'RoI pooling 결과를 받아 head 를 태우는 부분'),
   60: (R2, FR, 'forward', 'FastRCNNPredictor', 'class 별 분류와 box regression 을 동시에 출력'),
 },
 'vision_transformer_ingest.json': {
   20: (V, 'vit_jax/models.py', 'get_model', None, '사전학습 모델을 이름으로 불러와 파인튜닝에 쓰는 진입점'),
   23: (V, 'vit_jax/models_resnet.py', '__call__', 'ResNetStage', 'CNN stage 를 앞단에 두는 hybrid 구성'),
   28: (V, 'vit_jax/train.py', 'make_update_fn', None, 'weight decay 를 포함한 파라미터 갱신 정의'),
   31: (V, 'vit_jax/models.py', 'get_model', None, '추론 시 모델을 구성하는 경로'),
   32: (V2, 'vit_pytorch/vit.py', 'forward', 'ViT', 'patch→embedding→Transformer→head 전체 흐름'),
 },
 'clip_ingest.json': {
   25: (C2, 'src/open_clip_train/train.py', 'train_one_epoch', None, 'optimizer step 과 scheduler 가 도는 학습 루프'),
   26: (C2, 'src/open_clip_train/train.py', 'train_one_epoch', None, 'autocast 로 mixed precision 을 적용하는 부분'),
   27: ('CLIP', 'clip/clip.py', 'tokenize', None, '프롬프트 문장을 토큰화해 텍스트 인코더에 넣는 부분'),
 },
 'latent_diffusion_ingest.json': {
   24: (S, 'ldm/models/diffusion/ddim.py', 'p_sample_ddim', 'DDIMSampler', '초기 latent 를 주고 역방향 스텝을 도는 image-to-image 경로'),
   25: (S, 'scripts/inpaint.py', 'make_batch', None, '마스크와 원본을 묶어 inpainting 입력을 만드는 부분'),
   26: (S, 'ldm/data/imagenet.py', '_load', 'ImageNetBase', '학습 데이터셋을 읽어 들이는 부분'),
 },
 'attention_is_all_you_need_ingest.json': {
   25: (A, 'transformer/Models.py', '__init__', 'Transformer', 'trg_word_prj 로 decoder 출력을 vocabulary 로 사영'),
   27: (A, 'transformer/Models.py', '__init__', 'Transformer', 'emb_src_trg_weight_sharing 으로 source·target embedding 을 공유'),
   47: (A, 'transformer/Translator.py', '_get_the_best_score_and_idx', 'Translator', '누적 점수로 상위 후보를 고르는 beam search 채점부'),
   54: (A, 'transformer/Models.py', 'forward', 'Transformer', 'trg_word_prj 를 거쳐 최종 출력 확률을 만드는 부분'),
   56: (A, 'transformer/Optim.py', '__init__', 'ScheduledOptim', 'Adam optimizer 를 감싸 학습률을 조절'),
   57: (A, 'train.py', 'cal_loss', None, 'label smoothing 을 적용한 손실 계산'),
   58: (A, 'train.py', 'prepare_dataloaders_from_bpe_files', None, 'BPE 로 만든 vocabulary 를 읽어 오는 부분'),
 },
}
base.REPO_KEY_OF_PAPER = {}
base.main()
