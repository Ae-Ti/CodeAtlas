#!/usr/bin/env python3
"""2차 보강 — BERT / CLIP / SAM / Latent Diffusion 의 남은 미매핑 chunk."""
import sys, os
SC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SC)
import add_secondary as base

base.SECONDARY['CLIP2'] = dict(slug='mlfoundations/open_clip', branch='main', stars=14055,
                               sha='602d4af74f86df6f2ff81ba0f0a847b0b70ad2e5',
                               license='NOASSERTION', lang='Python', relation='REFERENCE')

base.EXTRA = {
 'bert_ingest.json': {
   14: ('BERT', 'modeling.py', 'gelu', None, 'tanh 근사식으로 GELU 를 구현한 함수'),
   20: ('BERT', 'create_pretraining_data.py', 'create_masked_lm_predictions', None,
        '토큰을 15% 확률로 골라 [MASK]·랜덤·원본으로 바꾸고 정답 라벨을 남기는 부분'),
   24: ('BERT', 'run_pretraining.py', 'get_masked_lm_output', None,
        '마스킹된 위치의 출력으로 log softmax 를 취해 MLM 손실을 계산'),
   27: ('BERT', 'modeling.py', 'BertConfig', None,
        'hidden_size·num_hidden_layers·num_attention_heads 로 Base/Large 를 구분하는 설정 클래스'),
   33: ('BERT', 'run_classifier.py', 'create_model', None,
        '[CLS] pooled output 에 분류층을 얹고 cross entropy 손실을 계산'),
   34: ('BERT', 'run_squad.py', 'create_model', None,
        'sequence output 에서 start/end logit 을 뽑는 SQuAD 파인튜닝 헤드'),
   36: ('BERT', 'run_pretraining.py', 'main', None,
        'MLM 과 NSP 를 함께 도는 사전학습 전체 실행 경로'),
 },
 'clip_ingest.json': {
   1:  ('CLIP', 'clip/model.py', '__init__', 'VisionTransformer',
        'CLIP 의 이미지 인코더로 쓰이는 ViT 정의'),
   3:  ('CLIP', 'clip/model.py', 'forward', 'VisionTransformer',
        'conv1 출력을 reshape·permute 해 patch 시퀀스로 펼치는 부분'),
   4:  ('CLIP', 'clip/model.py', '__init__', 'VisionTransformer',
        'class_embedding 을 학습 파라미터로 두는 지점'),
   5:  ('CLIP', 'clip/model.py', '__init__', 'VisionTransformer',
        'positional_embedding 을 학습 파라미터로 두는 지점'),
   13: ('CLIP', 'clip/model.py', '__init__', 'VisionTransformer',
        'proj 로 이미지 표현을 공통 임베딩 차원으로 사영'),
   15: ('CLIP', 'clip/model.py', 'forward', 'CLIP',
        '이미지·텍스트 feature 를 각각 L2 정규화하는 부분'),
   16: ('CLIP', 'clip/model.py', 'forward', 'CLIP',
        '정규화된 두 feature 의 내적으로 유사도 행렬을 만드는 부분'),
   17: ('CLIP', 'clip/model.py', '__init__', 'CLIP',
        'logit_scale 을 학습 가능한 temperature 로 두는 지점'),
   18: ('CLIP2', 'src/open_clip/loss.py', 'forward', 'ClipLoss',
        '이미지→텍스트, 텍스트→이미지 양방향 대조 손실'),
   19: ('CLIP2', 'src/open_clip/loss.py', 'get_ground_truth', 'ClipLoss',
        '대각선을 정답으로 두는 대칭 cross entropy 의 라벨 생성'),
   20: ('CLIP2', 'src/open_clip_train/data.py', 'get_data', None,
        '학습·검증 데이터로더를 구성하는 파이프라인'),
   21: ('CLIP', 'clip/clip.py', '_transform', None,
        'Resize·CenterCrop·Normalize 로 이미지를 전처리'),
   22: ('CLIP', 'clip/clip.py', 'tokenize', None,
        'BPE 로 텍스트를 토큰화하고 컨텍스트 길이에 맞추는 부분'),
   23: ('CLIP', 'clip/model.py', 'encode_text', 'CLIP',
        'class 이름 프롬프트를 텍스트 임베딩으로 바꿔 zero-shot 분류에 쓰는 경로'),
   24: ('CLIP2', 'src/open_clip_train/train.py', 'train_one_epoch', None,
        '한 epoch 학습 루프 — 대조 손실 계산과 파라미터 갱신'),
   29: ('CLIP', 'clip/model.py', 'encode_image', 'CLIP',
        '추론 시 이미지를 임베딩으로 바꾸는 진입점'),
   30: ('CLIP', 'clip/model.py', 'build_model', None,
        '체크포인트 state_dict 로 전체 CLIP 모델을 조립하는 부분'),
 },
 'segment_anything_ingest.json': {
   22: ('Segment', 'segment_anything/automatic_mask_generator.py', 'postprocess_small_regions', 'SamAutomaticMaskGenerator',
        'batched_nms 로 겹치는 마스크를 정리하는 부분'),
   23: ('Segment', 'segment_anything/automatic_mask_generator.py', 'generate', 'SamAutomaticMaskGenerator',
        '전체 이미지에 격자 프롬프트를 자동 생성해 마스크를 뽑는 실행 전략'),
   28: ('Segment', 'segment_anything/predictor.py', 'predict', 'SamPredictor',
        '점·박스 프롬프트만으로 새로운 대상에 마스크를 내는 zero-shot 추론 경로'),
 },
 'latent_diffusion_ingest.json': {
   11: ('Stable', 'ldm/modules/encoders/modules.py', 'FrozenCLIPTextEmbedder', None,
        'CLIP 텍스트 인코더를 고정한 채 conditioning 임베딩을 만드는 부분'),
   12: ('Stable', 'ldm/modules/diffusionmodules/openaimodel.py', 'forward', 'TimestepEmbedSequential',
        'timestep 임베딩을 각 residual block 에 전달하는 부분'),
   16: ('Stable', 'ldm/models/diffusion/ddim.py', 'sample', 'DDIMSampler',
        'DDIM 역방향 샘플링 알고리즘 진입점'),
   23: ('Stable', 'scripts/txt2img.py', 'load_model_from_config', None,
        'text-to-image 생성 스크립트에서 모델을 올리는 부분'),
 },
}
base.main()
