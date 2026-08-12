# 제3자 코드 라이선스 고지 (THIRD-PARTY NOTICES)

CodeAtlas는 논문 단락과 실제 구현 코드를 연결해 보여주는 카탈로그입니다.
그 과정에서 아래 저장소들의 **소스 코드 일부를 원문 그대로** 데이터베이스에 저장하고
화면에 표시하며, `database/ingest/*_ingest.json` 파일 형태로 이 저장소에 함께 배포합니다.

따라서 이 배포는 각 저장소 라이선스가 말하는 **재배포(redistribution)** 에 해당하며,
이 문서는 그에 필요한 저작권 표시·라이선스 고지를 제공합니다.

- 인용 코드는 **수정하지 않았습니다.** 각 블록은 지정된 커밋의 해당 줄 범위와 바이트 단위로 일치합니다.
- 각 블록의 출처(저장소·커밋·파일·줄 번호)는 `code_blocks` 테이블과
  `database/seed_manifest.csv` 에 기록돼 있습니다.
- 라이선스 전문은 `database/licenses/` 에 저장소별 원본 그대로 두었습니다.
## 인용 현황

| 저장소 | 커밋 | 라이선스 | 블록 | 줄수 |
|---|---|---|---:|---:|
| [`google-research/bert`](https://github.com/google-research/bert) | `eedf571` | Apache-2.0 | 18 | 1331 |
| [`CompVis/latent-diffusion`](https://github.com/CompVis/latent-diffusion) | `a506df5` | MIT | 18 | 1163 |
| [`facebookresearch/segment-anything`](https://github.com/facebookresearch/segment-anything) | `dca509f` | Apache-2.0 | 16 | 1049 |
| [`meta-llama/llama3`](https://github.com/meta-llama/llama3) | `a0940f9` | Meta Llama 3 Community License | 10 | 729 |
| [`google-research/vision_transformer`](https://github.com/google-research/vision_transformer) | `64801f1` | Apache-2.0 | 10 | 564 |
| [`jadore801120/attention-is-all-you-need-pytorch`](https://github.com/jadore801120/attention-is-all-you-need-pytorch) | `132907d` | MIT | 33 | 491 |
| [`pjreddie/darknet`](https://github.com/pjreddie/darknet) | `f6afaab` | YOLO LICENSE v2 (public-domain style) | 14 | 476 |
| [`openai/CLIP`](https://github.com/openai/CLIP) | `d05afc4` | MIT | 13 | 398 |
| [`mlfoundations/open_clip`](https://github.com/mlfoundations/open_clip) | `602d4af` | MIT | 4 | 264 |
| [`pytorch/vision`](https://github.com/pytorch/vision) | `0fba2e8` | BSD-3-Clause | 8 | 243 |
| [`KaimingHe/deep-residual-networks`](https://github.com/KaimingHe/deep-residual-networks) | `a7026cb` | MIT | 14 | 148 |
| [`lucidrains/vit-pytorch`](https://github.com/lucidrains/vit-pytorch) | `bb13e27` | MIT | 6 | 105 |

## 별도 조건이 붙는 저장소


### Meta Llama 3 Community License — `meta-llama/llama3`

이 라이선스는 "Meta Llama 3"의 정의에 **inference-enabling code**를 포함하므로
`llama/model.py`·`generation.py`·`tokenizer.py` 인용분이 그 대상입니다.
§1.b 가 요구하는 세 가지를 다음과 같이 이행합니다.

| 조항 | 요구 | 이행 |
|---|---|---|
| §1.b.i (A) | Agreement 사본 동봉 | [`database/licenses/meta-llama_llama3.txt`](licenses/meta-llama_llama3.txt) |
| §1.b.i (B) | "Built with Meta Llama 3" 표시 | 웹 UI 푸터 및 이 문서 |
| §1.b.iii | Notice 파일에 attribution 문구 | 저장소 루트 [`NOTICE`](../NOTICE) |

> **Built with Meta Llama 3**
>
> Meta Llama 3 is licensed under the Meta Llama 3 Community License,
> Copyright © Meta Platforms, Inc. All Rights Reserved.

CodeAtlas는 Llama 3 모델을 학습·파인튜닝하거나 서비스에 탑재하지 않습니다.
논문 「The Llama 3 Herd of Models」(arXiv:2407.21783)의 서술과 공식 저장소 구현을
대조해 보여주기 위해 코드 일부를 인용할 뿐입니다. §2의 월간 활성 사용자 7억 명
조건은 해당하지 않습니다.

## 저장소별 고지

### `google-research/bert`

- 커밋: `eedf5716ce1268e56f0a50264a88cafad334ac61`  (기본 브랜치 `master`)
- 라이선스: **Apache-2.0** — 전문: [`database/licenses/google-research_bert.txt`](licenses/google-research_bert.txt)
- 저작권: Copyright 2018 The Google AI Language Team Authors
- 사용 논문: BERT: Pre-training of Deep Bidirectional Tra
- 인용 파일: `create_pretraining_data.py`, `modeling.py`, `optimization.py`, `run_classifier.py`, `run_pretraining.py`, `run_squad.py`

### `CompVis/latent-diffusion`

- 커밋: `a506df5756472e2ebaf9078affdde2c4f1502cd4`  (기본 브랜치 `main`)
- 라이선스: **MIT** — 전문: [`database/licenses/CompVis_latent-diffusion.txt`](licenses/CompVis_latent-diffusion.txt)
- 저작권: Copyright (c) 2022 Machine Vision and Learning Group, LMU Munich
- 사용 논문: High-Resolution Image Synthesis with Latent 
- 인용 파일: `ldm/models/autoencoder.py`, `ldm/models/diffusion/ddim.py`, `ldm/models/diffusion/ddpm.py`, `ldm/modules/attention.py`, `ldm/modules/diffusionmodules/openaimodel.py`, `ldm/modules/distributions/distributions.py`, `ldm/modules/encoders/modules.py`, `ldm/modules/losses/vqperceptual.py` 외 1개

### `facebookresearch/segment-anything`

- 커밋: `dca509fe793f601edb92606367a655c15ac00fdf`  (기본 브랜치 `main`)
- 라이선스: **Apache-2.0** — 전문: [`database/licenses/facebookresearch_segment-anything.txt`](licenses/facebookresearch_segment-anything.txt)
- 저작권: Copyright (c) Meta Platforms, Inc. and affiliates.
- 사용 논문: Segment Anything
- 인용 파일: `segment_anything/automatic_mask_generator.py`, `segment_anything/modeling/image_encoder.py`, `segment_anything/modeling/mask_decoder.py`, `segment_anything/modeling/prompt_encoder.py`, `segment_anything/modeling/sam.py`, `segment_anything/modeling/transformer.py`, `segment_anything/predictor.py`, `segment_anything/utils/amg.py`

### `meta-llama/llama3`

- 커밋: `a0940f9cf7065d45bb6675660f80d305c041a754`  (기본 브랜치 `main`)
- 라이선스: **Meta Llama 3 Community License** — 전문: [`database/licenses/meta-llama_llama3.txt`](licenses/meta-llama_llama3.txt)
- 저작권: Copyright © Meta Platforms, Inc. All Rights Reserved.
- 사용 논문: The Llama 3 Herd of Models
- 인용 파일: `llama/generation.py`, `llama/model.py`, `llama/tokenizer.py`

### `google-research/vision_transformer`

- 커밋: `64801f1b3b367b3611cc27a3d45cc22870a36fb3`  (기본 브랜치 `main`)
- 라이선스: **Apache-2.0** — 전문: [`database/licenses/google-research_vision_transformer.txt`](licenses/google-research_vision_transformer.txt)
- 저작권: Copyright 2021 Google LLC
- 사용 논문: An Image is Worth 16x16 Words: Transformers 
- 인용 파일: `vit_jax/checkpoint.py`, `vit_jax/input_pipeline.py`, `vit_jax/models_vit.py`, `vit_jax/train.py`

### `jadore801120/attention-is-all-you-need-pytorch`

- 커밋: `132907dd272e2cc92e3c10e6c4e783a87ff8893d`  (기본 브랜치 `master`)
- 라이선스: **MIT** — 전문: [`database/licenses/jadore801120_attention-is-all-you-need-pytorch.txt`](licenses/jadore801120_attention-is-all-you-need-pytorch.txt)
- 저작권: Copyright (c) 2017 Victor Huang
- 사용 논문: Attention Is All You Need
- 인용 파일: `train.py`, `transformer/Layers.py`, `transformer/Models.py`, `transformer/Modules.py`, `transformer/Optim.py`, `transformer/SubLayers.py`, `transformer/Translator.py`, `translate.py`

### `pjreddie/darknet`

- 커밋: `f6afaabcdf85f77e7aff2ec55c020c0e297c77f9`  (기본 브랜치 `master`)
- 라이선스: **YOLO LICENSE v2 (public-domain style)** — 전문: [`database/licenses/pjreddie_darknet.txt`](licenses/pjreddie_darknet.txt)
- 저작권: (YOLO LICENSE v2 — 저작권 표시 줄 없음)
- 사용 논문: You Only Look Once: Unified, Real-Time Objec
- 인용 파일: `cfg/t1.test.cfg`, `cfg/tiny.cfg`, `cfg/yolov1-tiny.cfg`, `cfg/yolov1.cfg`, `cfg/yolov3-openimages.cfg`, `examples/detector.c`, `src/activations.c`, `src/box.c` 외 2개

### `openai/CLIP`

- 커밋: `d05afc436d78f1c48dc0dbf8e5980a9d471f35f6`  (기본 브랜치 `main`)
- 라이선스: **MIT** — 전문: [`database/licenses/openai_CLIP.txt`](licenses/openai_CLIP.txt)
- 저작권: Copyright (c) 2021 OpenAI
- 사용 논문: Learning Transferable Visual Models From Nat
- 인용 파일: `clip/clip.py`, `clip/model.py`, `clip/simple_tokenizer.py`

### `mlfoundations/open_clip`

- 커밋: `602d4af74f86df6f2ff81ba0f0a847b0b70ad2e5`  (기본 브랜치 `main`)
- 라이선스: **MIT** — 전문: [`database/licenses/mlfoundations_open_clip.txt`](licenses/mlfoundations_open_clip.txt)
- 저작권: Copyright (c) 2012-2021 Gabriel Ilharco, Mitchell Wortsman, Nicholas Carlini, Rohan Taori, Achal Dave, Vaishaal Shankar, John Miller, Hongseok Namkoong, Hannaneh Hajishirzi, Ali Farhadi, Ludwig Schmidt
- 사용 논문: Learning Transferable Visual Models From Nat
- 인용 파일: `src/open_clip/loss.py`, `src/open_clip_train/data.py`, `src/open_clip_train/train.py`

### `pytorch/vision`

- 커밋: `0fba2e84fe255a2fcd81bd0b10c74d7fca99a89f`  (기본 브랜치 `main`)
- 라이선스: **BSD-3-Clause** — 전문: [`database/licenses/pytorch_vision.txt`](licenses/pytorch_vision.txt)
- 저작권: Copyright (c) Soumith Chintala 2016, All rights reserved.
- 사용 논문: Deep Residual Learning for Image Recognition
- 인용 파일: `torchvision/models/resnet.py`

### `KaimingHe/deep-residual-networks`

- 커밋: `a7026cb6d478e131b765b898c312e25f9f6dc031`  (기본 브랜치 `master`)
- 라이선스: **MIT** — 전문: [`database/licenses/KaimingHe_deep-residual-networks.txt`](licenses/KaimingHe_deep-residual-networks.txt)
- 저작권: Copyright (c) 2016 Shaoqing Ren
- 사용 논문: Deep Residual Learning for Image Recognition
- 인용 파일: `prototxt/ResNet-101-deploy.prototxt`

### `lucidrains/vit-pytorch`

- 커밋: `bb13e27ee5b30ddd3e09c2e23c30ec2c17683d35`  (기본 브랜치 `main`)
- 라이선스: **MIT** — 전문: [`database/licenses/lucidrains_vit-pytorch.txt`](licenses/lucidrains_vit-pytorch.txt)
- 저작권: Copyright (c) 2020 Phil Wang
- 사용 논문: An Image is Worth 16x16 Words: Transformers 
- 인용 파일: `vit_pytorch/vit.py`

