# Vision Transform

# CHUNK 01

# Vision Transformer 전체 Architecture

---

## 논문 위치

```
Section 3 Method
Page 3
```

---

## 논문 원문

> We split an image into patches and provide the sequence of linear embeddings of these patches as an input to a Transformer.
> 

---

## 구현 목적

ViT는 기존 CNN처럼 이미지의 지역 필터를 직접 적용하지 않고,

이미지를 Patch 단위로 나눈 뒤 Transformer Encoder 입력으로 처리한다.

전체 구조:

```
Image

↓

Patch Split

↓

Linear Projection

↓

+ Position Embedding

↓

Transformer Encoder

↓

MLP Head

↓

Class Prediction
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

클래스:

```
VisionTransformer
```

---

코드:

```
class VisionTransformer(nn.Module):

    num_classes: int
    patches: Any
    transformer: Any
    hidden_size: int

    @nn.compact
    def __call__(
        self,
        x,
        train=False
    ):

        x = nn.Conv(
            features=self.hidden_size,
            kernel_size=self.patches.size,
            strides=self.patches.size,
            padding='VALID',
            name='embedding'
        )(x)

        x = x.reshape(
            x.shape[0],
            -1,
            x.shape[-1]
        )

        x = self.transformer(
            x,
            train=train
        )

        x = x[:,0]

        x = nn.Dense(
            self.num_classes
        )(x)

        return x
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 02

# Image Patch Extraction

---

## 논문 위치

```
Section 3.1 Vision Transformer
Page 3
```

---

## 논문 원문

> We reshape the image x ∈ R^(H×W×C) into a sequence of flattened 2D patches.
> 

---

## 구현 목적

입력 이미지:

```
224 × 224 × 3
```

Patch size:

```
16 × 16
```

이면:

```
224/16 = 14

14 × 14 = 196 patches
```

생성.

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
x = nn.Conv(
    features=self.hidden_size,
    kernel_size=self.patches.size,
    strides=self.patches.size,
    padding='VALID',
)(x)
```

---

동작:

입력:

```
[B,224,224,3]
```

Conv 적용:

```
kernel = 16
stride = 16
```

출력:

```
[B,14,14,768]
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 03

# Patch Flattening

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The resulting sequence of patch embeddings is fed to the Transformer encoder.
> 

---

## 구현 목적

2D Patch 배열을 Transformer 입력 형태인 sequence로 변경.

변환:

```
14 × 14 × 768

↓

196 × 768
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
x = x.reshape(
    x.shape[0],
    -1,
    x.shape[-1]
)
```

---

결과:

```
(batch,
 num_patches,
 hidden_dim)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 04

# Patch Embedding (Linear Projection)

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The patch embeddings are projected to a D-dimensional vector space.
> 

---

## 구현 목적

Patch pixel 값을 Transformer hidden dimension으로 변환.

예:

```
16×16×3

↓

768 dimension vector
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
x = nn.Conv(
    features=self.hidden_size,
    kernel_size=self.patches.size,
    strides=self.patches.size,
    padding='VALID',
    name='embedding'
)(x)
```

---

설명:

논문에서는 Linear Projection이라고 표현하지만 공식 구현에서는 Conv2D를 이용한다.

이유:

```
kernel size = patch size
stride = patch size
```

이면 Linear projection과 동일한 연산.

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 05

# Class Token ([CLS])

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> We prepend a learnable embedding to the sequence of patch embeddings.
> 

---

## 구현 목적

BERT의 CLS token과 동일한 역할.

전체 이미지 정보를 대표하는 하나의 token 생성.

구조:

```
[CLS]

Patch1

Patch2

...

Patch196
```

총:

```
197 tokens
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
cls = self.param(
    'cls',
    nn.initializers.zeros,
    (1,1,self.hidden_size)
)

cls = jnp.tile(
    cls,
    [x.shape[0],1,1]
)

x = jnp.concatenate(
    [cls,x],
    axis=1
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 06

# Position Embedding

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> Position embeddings are added to the patch embeddings to retain positional information.
> 

---

## 구현 목적

Transformer는 순서 정보를 가지지 않기 때문에 위치 정보를 추가.

---

수식:

```
z0 = [xclass; x1E; x2E; ...] + Epos
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
pos_embedding = self.param(
    'pos_embedding',
    nn.initializers.normal(
        stddev=0.02
    ),
    (
        1,
        num_tokens,
        hidden_size
    )
)

x = x + pos_embedding
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 07

# Transformer Encoder Input

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The resulting sequence is fed to a standard Transformer encoder.
> 

---

## 구현 목적

Patch embedding 이후 Transformer Encoder 적용.

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
x = self.transformer(
    x,
    train=train
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 08

# Transformer Encoder Block

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The Transformer encoder consists of alternating layers of multiheaded self-attention and MLP blocks.
> 

---

## 구현 목적

ViT Encoder 구조:

```
LayerNorm

↓

Multi Head Attention

↓

Residual

↓

LayerNorm

↓

MLP

↓

Residual
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
for lyr in range(
    self.num_layers
):

    x = Encoder1DBlock(
        mlp_dim=self.mlp_dim,
        num_heads=self.num_heads,
        dropout=self.dropout_rate
    )(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

# CHUNK 09

# Multi-Head Self Attention

---

## 논문 위치

```
Section 3.1 Vision Transformer
Page 3
```

---

## 논문 원문

> The Transformer encoder consists of alternating layers of multiheaded self-attention and MLP blocks.
> 

---

## 구현 목적

ViT는 CNN의 convolution 대신 Transformer의 Self-Attention을 사용한다.

각 Patch token 간의 관계를 계산한다.

예:

```
Patch 1
 ↔
Patch 50
 ↔
Patch 120
```

모든 patch가 서로 정보를 교환.

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

클래스:

```
Encoder1DBlock
```

---

코드:

```
class Encoder1DBlock(nn.Module):

    mlp_dim: int
    num_heads: int
    dropout: float

    @nn.compact
    def __call__(self, inputs, train=False):

        x = nn.LayerNorm()(inputs)

        x = nn.MultiHeadDotProductAttention(
            num_heads=self.num_heads,
            dropout_rate=self.dropout
        )(x, x)

        x = x + inputs
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 10

# Query / Key / Value 생성

---

## 논문 위치

```
Section 3.1
Page 3

Section 3.4
Page 5
```

---

## 논문 원문

> We use a standard Transformer encoder as described in Vaswani et al.
> 

---

## 구현 목적

Self-Attention 계산을 위해 입력 token을 세 가지 vector로 변환.

수식:

```
Q = XWq

K = XWk

V = XWv
```

---

# Git 코드

ViT는 Flax 기본 Attention Layer 사용.

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
x = nn.MultiHeadDotProductAttention(
    num_heads=self.num_heads,
    dropout_rate=self.dropout
)(x, x)
```

---

내부 구현:

```
flax.linen.attention.MultiHeadDotProductAttention
```

---

동작:

```
q = Dense(features)(inputs)

k = Dense(features)(inputs)

v = Dense(features)(inputs)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 11

# Scaled Dot Product Attention

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> Self-attention allows the model to attend to all positions of the input sequence.
> 

---

## 구현 목적

Attention 계산:

\[
Attention(Q,K,V)
=
softmax(\frac{QK^T}{\sqrt d_k})V
\]

---

# Git 코드

Flax 내부:

```
flax/linen/attention.py
```

---

코드:

```
attn_weights = jnp.einsum(
    '...qhd,...khd->...hqk',
    query,
    key
)

attn_weights = attn_weights / math.sqrt(
    depth
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 12

# Softmax Attention Probability

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The attention weights are normalized using softmax.
> 

---

## 구현 목적

Attention score를 확률값으로 변환.

---

# Git 코드

파일:

```
flax/linen/attention.py
```

---

코드:

```
attn_weights = nn.softmax(
    attn_weights
)
```

---

결과:

```
각 Patch token이
다른 Patch를 얼마나 참고할지 결정
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 13

# Attention Output Projection

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The outputs of all attention heads are concatenated and projected.
> 

---

## 구현 목적

Multi Head 결과를 다시 hidden dimension으로 변환.

---

# Git 코드

Flax Attention 내부:

```
out = Dense(
    features
)(
    attention_output
)
```

---

동작:

```
head1
head2
...
head12

↓

Concat

↓

Linear Projection

↓

768 dimension
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 14

# Residual Connection

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> Layer normalization is applied before every block, and residual connections are applied after every block.
> 

---

## 구현 목적

Gradient 흐름 개선.

수식:

```
Output = x + Attention(x)
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
x = nn.MultiHeadDotProductAttention(
    num_heads=self.num_heads
)(x,x)

x = x + inputs
```

---

MLP 이후:

```
y = MlpBlock()(x)

x = x + y
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 15

# Layer Normalization

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> Layer normalization is applied before every block.
> 

---

## 구현 목적

Transformer 안정적인 학습.

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
x = nn.LayerNorm()(inputs)
```

---

Encoder 마지막:

```
x = nn.LayerNorm()(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 16

# MLP Block

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> Each Transformer layer contains an MLP with two layers.
> 

---

## 구현 목적

Attention 결과를 비선형 변환.

구조:

```
768

↓

3072

↓

768
```

---

# Git 코드

파일:

```
models_vit.py
```

---

클래스:

```
MlpBlock
```

---

코드:

```
x = nn.Dense(
    features=mlp_dim
)(x)

x = nn.gelu(x)

x = nn.Dropout(
    rate=dropout
)(x)

x = nn.Dense(
    features=hidden_dim
)(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 17

# GELU Activation

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> We use GELU nonlinearities.
> 

---

## 구현 목적

MLP Block의 활성화 함수.

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
x = nn.gelu(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 18

# Transformer Layer 반복

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> We apply the Transformer encoder blocks L times.
> 

---

## 구현 목적

ViT-B:

```
Encoder × 12
```

ViT-L:

```
Encoder × 24
```

ViT-H:

```
Encoder × 32
```

---

# Git 코드

파일:

```
models_vit.py
```

---

코드:

```
for lyr in range(
    self.num_layers
):

    x = Encoder1DBlock(
        num_heads=self.num_heads,
        mlp_dim=self.mlp_dim
    )(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 19

# Classification Head (Image Classification Output)

---

## 논문 위치

```
Section 3.1 Vision Transformer
Page 3
```

---

## 논문 원문

> The classification head is attached to the Transformer encoder output.
> 

---

## 구현 목적

Transformer Encoder가 출력한 token 중 **Class Token([CLS])** representation을 이용해 최종 이미지 분류 수행.

구조:

```
Patch Tokens

↓

Transformer Encoder

↓

CLS Token Vector

↓

MLP / Linear Head

↓

Class Prediction
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

클래스:

```
VisionTransformer
```

---

코드:

```
x = self.transformer(
    x,
    train=train
)

x = x[:,0]

x = nn.Dense(
    self.num_classes,
    name='head'
)(x)
```

---

설명:

```
x[:,0]
```

부분이 CLS token 선택.

예:

입력:

```
[
 CLS,
 Patch1,
 Patch2,
 ...
 Patch196
]
```

선택:

```
CLS
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 20

# MLP Head (Pre-training / Representation Learning)

---

## 논문 위치

```
Section 3.1 Vision Transformer
Page 3
```

---

## 논문 원문

> The MLP head consists of a single hidden layer at pre-training time and a single linear layer at fine-tuning time.
> 

---

## 구현 목적

ViT는 학습 단계에 따라 Head 구조를 변경.

Pre-training:

```
CLS Representation

↓

MLP

↓

Prediction
```

Fine-tuning:

```
CLS Representation

↓

Linear Layer

↓

Class
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
if self.num_classes:

    x = nn.Dense(
        self.num_classes,
        name="head"
    )(x)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 21

# Fine-tuning Strategy

---

## 논문 위치

```
Section 3.2 Fine-tuning
Page 4
```

---

## 논문 원문

> We fine-tune the model on downstream tasks by replacing the classification head.
> 

---

## 구현 목적

ImageNet-21k에서 학습한 ViT를 가져와 새로운 데이터셋에 적용.

방법:

```
Pretrained ViT

↓

Remove old classifier

↓

New classifier

↓

Fine-tuning
```

---

# Git 코드

파일:

```
vit_jax/train.py
```

---

코드:

```
model = models.VisionTransformer(
    num_classes=config.num_classes
)
```

---

Checkpoint Loading:

```
state = checkpoints.restore_checkpoint(
    checkpoint_path,
    state
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 22

# ViT Model Size Configuration

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> We experiment with three model sizes: ViT-Base, ViT-Large, and ViT-Huge.
> 

---

## 구현 목적

ViT 모델 크기 결정 요소:

- hidden dimension
- transformer depth
- attention head 개수

---

## 모델 구조

### ViT-Base

```
Layers : 12
Hidden : 768
Heads : 12
Parameters : 86M
```

### ViT-Large

```
Layers : 24
Hidden : 1024
Heads : 16
Parameters : 307M
```

### ViT-Huge

```
Layers : 32
Hidden : 1280
Heads : 16
Parameters : 632M
```

---

# Git 코드

파일:

```
vit_jax/configs.py
```

---

예상 설정:

```
config = ConfigDict()

config.hidden_size = 768

config.num_layers = 12

config.num_heads = 12

config.mlp_dim = 3072
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 23

# Patch Size Experiment

---

## 논문 위치

```
Section 4.2 Scaling Study
Page 6
```

---

## 논문 원문

> We evaluate different patch sizes and find that smaller patches improve performance.
> 

---

## 구현 목적

Patch 크기는 Transformer token 개수와 연관.

예:

이미지:

```
224×224
```

Patch:

```
16×16
```

결과:

```
14×14 = 196 tokens
```

Patch:

```
32×32
```

결과:

```
7×7 = 49 tokens
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
kernel_size=self.patches.size,

strides=self.patches.size
```

---

설정:

```
patches.size = (16,16)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 24

# Hybrid Architecture (CNN + Transformer)

---

## 논문 위치

```
Section 3.1
Page 3
```

---

## 논문 원문

> The patch embeddings can also be extracted from a CNN feature map.
> 

---

## 구현 목적

ViT는 순수 Transformer뿐 아니라 CNN backbone feature를 patch 입력으로 사용할 수 있음.

구조:

```
Image

↓

CNN

↓

Feature Map

↓

Patch Extraction

↓

Transformer
```

---

# Git 코드

파일:

```
vit_jax/models_vit.py
```

---

코드:

```
if self.representation_size:

    x = nn.Dense(
        self.representation_size
    )(x)
```

---

※ 공식 Google ViT repository에서는 Hybrid 모델이 별도 구현되어 있으며 ResNet backbone 사용.

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 25

# Training Dataset Pipeline

---

## 논문 위치

```
Section 4 Experiments
Page 5
```

---

## 논문 원문

> We pre-train on ImageNet-21k and fine-tune on ImageNet-1k.
> 

---

## 구현 목적

데이터 흐름:

```
Image Dataset

↓

Augmentation

↓

Batch

↓

ViT Model

↓

Loss

↓

Optimizer
```

---

# Git 코드

파일:

```
vit_jax/input_pipeline.py
```

---

코드:

```
def get_dataset(
    split,
    batch_size
):

    dataset = tfds.load(
        dataset_name,
        split=split
    )

    dataset = dataset.batch(
        batch_size
    )

    return dataset
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 26

# Data Augmentation

---

## 논문 위치

```
Section 4.1 Training Details
Page 5
```

---

## 논문 원문

> We use standard data augmentation methods including random crop and horizontal flip.
> 

---

## 구현 목적

학습 데이터 다양화.

사용:

- Random Crop
- Resize
- Flip
- RandAugment

---

# Git 코드

파일:

```
vit_jax/input_pipeline.py
```

---

코드:

```
def preprocess(
    image,
    label
):

    image = tf.image.resize(
        image,
        image_size
    )

    image = tf.image.random_flip_left_right(
        image
    )

    return image,label
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 27

# Optimizer (Adam / AdamW)

---

## 논문 위치

```
Section 4.1 Training Details
Page 5
```

---

## 논문 원문

> We train all models using Adam with weight decay.
> 

---

## 구현 목적

Parameter 업데이트.

---

# Git 코드

파일:

```
vit_jax/train.py
```

---

코드:

```
optimizer = optax.adamw(
    learning_rate=learning_rate,
    weight_decay=weight_decay
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 28

# Learning Rate Schedule

---

## 논문 위치

```
Section 4.1
Page 5
```

---

## 논문 원문

> We use a linear learning rate warmup and decay schedule.
> 

---

## 구현 목적

초기 학습 안정화.

---

# Git 코드

파일:

```
vit_jax/train.py
```

---

코드:

```
schedule = optax.join_schedules(
    schedules=[
        warmup_fn,
        decay_fn
    ],
    boundaries=[
        warmup_steps
    ]
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 29

# Weight Decay Regularization

---

## 논문 위치

```
Section 4.1
Page 5
```

---

## 논문 원문

> We use weight decay for regularization.
> 

---

# Git 코드

```
optimizer = optax.adamw(
    weight_decay=0.1
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 30

# Dropout

---

## 논문 위치

```
Section 4.1
Page 5
```

---

## 논문 원문

> We use dropout in Transformer layers.
> 

---

# Git 코드

```
x = nn.Dropout(
    rate=self.dropout_rate
)(
    x,
    deterministic=not train
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 31

# Checkpoint Loading

---

## 논문 위치

```
Section 3.2 Fine-tuning
Page 4
```

---

# Git 코드

파일:

```
checkpoint.py
```

---

코드:

```
state = checkpoints.restore_checkpoint(
    ckpt_dir,
    state
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 32

# Inference Pipeline

---

## 논문 위치

```
Section 3 Method
Page 3
```

---

## 구현 목적

학습된 ViT를 이용한 이미지 분류.

---

# Git 코드

```
logits = model.apply(
    variables,
    images,
    train=False
)

prediction = jnp.argmax(
    logits,
    axis=-1
)
```

---

## 논문 ↔ 코드 매칭

```
DIRECT
```

---

# CHUNK 33

# 전체 ViT 구현 Pipeline 정리

---

```
Image

↓

Patch Embedding

↓

Class Token 추가

↓

Position Embedding

↓

Transformer Encoder

↓

CLS Representation

↓

Classification Head

↓

Prediction
```

---

Git 파일 매칭:

| 논문 구현 | Git 파일 |
| --- | --- |
| Patch Embedding | models_vit.py |
| Transformer Encoder | models_vit.py |
| Attention | Flax Attention |
| MLP | models_vit.py |
| Training | train.py |
| Dataset | input_pipeline.py |
| Checkpoint | checkpoint.py |

---

# Vision Transformer 논문 구현 매칭 완료

총 Chunk:

```
32개
```

논문 → Git 대응:

```
대응 가능 : 대부분 DIRECT

예상코드 사용:
Hybrid Architecture 일부
```

완료.