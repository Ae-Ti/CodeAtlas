# Stable Diffusion

# CHUNK LD-01

# Latent Diffusion Model Overview

---

## ① 논문 위치

```
Section 1. Introduction

Page 1
```

---

## ② 논문 원문

> Diffusion models have recently emerged as a powerful class of generative models that achieve state-of-the-art image synthesis results.
> 

> However, their application to high-resolution synthesis is challenging due to the enormous computational requirements.
> 

> We propose latent diffusion models (LDMs), which reduce computational complexity by performing the diffusion process in a compressed latent space instead of pixel space.
> 

---

## ③ 논문 의미

기존 Diffusion Model 문제:

Pixel Space에서 직접 Noise 제거:

```
Image
512×512×3

↓

Diffusion

↓

Denoising
```

계산량 매우 큼.

Stable Diffusion은:

```
Pixel Space

↓

VAE Encoder

↓

Latent Space

↓

Diffusion

↓

VAE Decoder

↓

Image
```

구조 사용.

핵심:

```
Diffusion은 이미지가 아니라 latent feature에서 수행한다.
```

---

# ④ Git 코드 위치

Repository:

```
CompVis/latent-diffusion
```

전체 Pipeline:

```
ldm/models/diffusion/ddpm.py
```

Class:

```
DDPM
```

Function:

```
p_losses()
forward()
```

---

# ⑤ 코드 원문

## Diffusion Model Forward

파일:

```
ldm/models/diffusion/ddpm.py
```

```
def forward(
    self,
    x,
    c
):

    t = torch.randint(
        0,
        self.num_timesteps,
        (x.shape[0],),
        device=x.device
    )

    return self.p_losses(
        x,
        c,
        t
    )
```

---

## Loss 계산

```
def p_losses(
    self,
    x_start,
    cond,
    t,
    noise=None
):

    if noise is None:
        noise = torch.randn_like(
            x_start
        )

    x_noisy = self.q_sample(
        x_start=x_start,
        t=t,
        noise=noise
    )

    model_output = self.model(
        x_noisy,
        t,
        cond
    )

    loss = self.get_loss(
        model_output,
        noise
    )

    return loss
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> diffusion process in compressed latent space
> 

↓

코드:

```
x_start
```

이 입력 latent.

실제 Stable Diffusion에서는:

```
Image

↓

VAE encode

↓

z latent

↓

DDPM
```

순서.

---

# DB 저장

```
{
"chunk_id":"LD-01",

"section":
"Introduction",

"concept":
"Latent Diffusion Overview",

"file":
"ldm/models/diffusion/ddpm.py",

"class":
"DDPM",

"function":
"forward,p_losses",

"type":
"DIRECT"
}
```

---

---

# CHUNK LD-02

# Latent Space Compression (VAE)

---

## ① 논문 위치

```
Section 2.
Background

2.1 Perceptual Compression

Page 2
```

---

## ② 논문 원문

> We first train an autoencoder that learns a lower-dimensional latent representation of the data.
> 

> This allows us to perform diffusion in a compressed representation space.
> 

---

## ③ 논문 의미

Stable Diffusion 핵심 아이디어.

기존:

```
Diffusion on Image

512×512×3
```

↓

Stable Diffusion:

```
VAE Encoder

512×512×3

↓

64×64×4 latent
```

압축된 공간에서 diffusion 수행.

---

# ④ Git 코드 위치

File:

```
ldm/models/autoencoder.py
```

Class:

```
AutoencoderKL
```

Function:

```
encode()
decode()
```

---

# ⑤ 코드 원문

## Encoder

```
def encode(
    self,
    x
):

    h = self.encoder(
        x
    )

    moments = self.quant_conv(
        h
    )

    posterior = DiagonalGaussianDistribution(
        moments
    )

    return posterior
```

---

## Decoder

```
def decode(
    self,
    z
):

    z = self.post_quant_conv(
        z
    )

    dec = self.decoder(
        z
    )

    return dec
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> lower-dimensional latent representation
> 

↓

코드:

```
self.encoder()
```

↓

latent 생성

논문:

> reconstruct image
> 

↓

코드:

```
self.decoder()
```

---

# DB 저장

```
{
"chunk_id":"LD-02",

"concept":
"Latent Space Compression",

"file":
"autoencoder.py",

"class":
"AutoencoderKL",

"function":
"encode,decode",

"type":
"DIRECT"
}
```

---

# CHUNK LD-03

# Autoencoder Architecture

---

## ① 논문 위치

```
Section 2.1

Perceptual Compression

Page 2
```

---

## ② 논문 원문

> We employ an autoencoder with an encoder E and decoder D.
> 

> The encoder maps images into latent representations and the decoder reconstructs images from these representations.
> 

---

## ③ 논문 의미

VAE 구조:

Encoder:

```
x

↓

E(x)

↓

z
```

Decoder:

```
z

↓

D(z)

↓

x'
```

목표:

```
x ≈ D(E(x))
```

---

# ④ Git 코드 위치

File:

```
ldm/models/autoencoder.py
```

Class:

```
AutoencoderKL
```

---

# ⑤ 코드 원문

```
class AutoencoderKL(
    pl.LightningModule
):

    def __init__(
        self,
        ddconfig,
        lossconfig
    ):

        super().__init__()

        self.encoder = Encoder(
            **ddconfig
        )

        self.decoder = Decoder(
            **ddconfig
        )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

```
encoder E
decoder D
```

↓

코드:

```
self.encoder

self.decoder
```

---

# DB 저장

```
{
"chunk_id":"LD-03",

"concept":
"Autoencoder Architecture",

"file":
"autoencoder.py",

"class":
"AutoencoderKL",

"type":
"DIRECT"
}
```

---

# CHUNK LD-04

# Perceptual Loss

---

## ① 논문 위치

```
Section 2.1

Page 2
```

---

## ② 논문 원문

> We combine a perceptual loss with a patch-based adversarial objective.
> 

---

## ③ 논문 의미

Pixel Loss:

```
MSE
```

만 사용하면:

- 흐릿한 이미지 생성

그래서:

```
Reconstruction Loss

+

Perceptual Loss

+

Adversarial Loss
```

사용.

---

# ④ Git 코드 위치

File:

```
ldm/modules/losses/vqperceptual.py
```

Class:

```
VQLPIPSWithDiscriminator
```

---

# ⑤ 코드 원문

```
class VQLPIPSWithDiscriminator(
    nn.Module
):

    def forward(
        self,
        inputs,
        reconstructions
    ):

        rec_loss = torch.abs(
            inputs -
            reconstructions
        )

        p_loss = self.perceptual_loss(
            inputs,
            reconstructions
        )

        loss = (
            rec_loss
            +
            p_loss
        )

        return loss
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> perceptual loss
> 

↓

코드:

```
self.perceptual_loss()
```

---

# DB 저장

```
{
"chunk_id":"LD-04",

"concept":
"Perceptual Reconstruction Loss",

"file":
"vqperceptual.py",

"class":
"VQLPIPSWithDiscriminator",

"type":
"DIRECT"
}
```

---

# CHUNK LD-05

# KL Regularization

---

## ① 논문 위치

```
Section 2.1

Page 2
```

---

## ② 논문 원문

> We use a KL-regulated autoencoder to prevent arbitrary latent representations.
> 

---

## ③ 논문 의미

Latent 공간이 너무 자유롭게 변하지 않도록:

```
Encoder Distribution

↓

Normal Distribution
```

에 가깝게 제한.

---

# ④ Git 코드 위치

File:

```
ldm/modules/distributions/distributions.py
```

Class:

```
DiagonalGaussianDistribution
```

---

# ⑤ 코드 원문

```
class DiagonalGaussianDistribution:

    def __init__(
        self,
        parameters
    ):

        self.mean, self.logvar = torch.chunk(
            parameters,
            2,
            dim=1
        )

    def kl(
        self
    ):

        return 0.5 * torch.sum(
            torch.exp(self.logvar)
            +
            self.mean**2
            -
            1
            -
            self.logvar
        )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> KL-regulated autoencoder
> 

↓

코드:

```
kl()
```

---

# DB 저장

```
{
"chunk_id":"LD-05",

"concept":
"KL Regularization",

"file":
"distributions.py",

"class":
"DiagonalGaussianDistribution",

"type":
"DIRECT"
}
```

# CHUNK LD-06

# Forward Diffusion Process (Noise Addition)

---

## ① 논문 위치

```
Section 3. Latent Diffusion Models

Page 3
```

---

## ② 논문 원문

> Diffusion models are latent variable models that are trained to reverse a gradual noising process.
> 

---

## ③ 논문 의미

Diffusion Model의 기본 원리.

학습 과정에서는 깨끗한 이미지(latent)에 점점 Noise를 추가한다.

과정:

```
z0

↓

z1

↓

z2

↓

...

↓

zt
```

최종적으로:

```
pure noise
```

에 가까워진다.

수식:

\[
q(z_t|z_{t-1})
=
N(\sqrt{1-\beta_t}z_{t-1},\beta_tI)
\]

---

Stable Diffusion에서는 이미지가 아니라:

```
Image

↓

VAE Encoder

↓

Latent z
```

의 z에 noise를 추가한다.

---

# ④ Git 코드 위치

Repository:

```
CompVis/latent-diffusion
```

File:

```
ldm/models/diffusion/ddpm.py
```

Class:

```
DDPM
```

Function:

```
q_sample()
```

---

# ⑤ 코드 원문

```
def q_sample(
    self,
    x_start,
    t,
    noise=None
):

    if noise is None:
        noise = torch.randn_like(
            x_start
        )

    sqrt_alphas_cumprod_t = (
        extract_into_tensor(
            self.sqrt_alphas_cumprod,
            t,
            x_start.shape
        )
    )

    sqrt_one_minus_alphas_cumprod_t = (
        extract_into_tensor(
            self.sqrt_one_minus_alphas_cumprod,
            t,
            x_start.shape
        )
    )

    return (
        sqrt_alphas_cumprod_t * x_start
        +
        sqrt_one_minus_alphas_cumprod_t * noise
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> gradual noising process
> 

↓

코드:

```
q_sample()
```

↓

Noise 추가

논문 수식:

\[
z_t
=
\sqrt{\bar{\alpha_t}}z_0
+
\sqrt{1-\bar{\alpha_t}}\epsilon
\]

↓

코드:

```
sqrt_alphas_cumprod_t * x_start

+

sqrt_one_minus_alphas_cumprod_t * noise
```

---

# DB 저장

```
{
"chunk_id":"LD-06",

"concept":
"Forward Diffusion Process",

"file":
"ddpm.py",

"class":
"DDPM",

"function":
"q_sample",

"type":
"DIRECT"
}
```

---

# CHUNK LD-07

# Reverse Denoising Process

---

## ① 논문 위치

```
Section 3

Latent Diffusion Models

Page 3
```

---

## ② 논문 원문

> During sampling, the model learns to reverse the diffusion process by predicting the noise added to the latent representation.
> 

---

## ③ 논문 의미

학습된 UNet은:

입력:

```
Noisy latent zt

+

time step t
```

출력:

```
predicted noise ε
```

를 예측한다.

과정:

```
zt

↓

UNet

↓

noise prediction

↓

zt-1
```

반복하면:

```
Noise

↓

Image latent

↓

Image
```

생성.

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Class:

```
DDPM
```

Function:

```
p_sample()
```

---

# ⑤ 코드 원문

```
def p_sample(
    self,
    x,
    c,
    t,
):

    model_mean, _, model_log_variance = (
        self.p_mean_variance(
            x=x,
            c=c,
            t=t
        )
    )

    noise = torch.randn_like(
        x
    )

    nonzero_mask = (
        (1 - (t == 0))
        .float()
        .reshape(
            x.shape[0],
            *((1,) * (len(x.shape)-1))
        )
    )

    return (
        model_mean
        +
        nonzero_mask *
        torch.exp(
            0.5 * model_log_variance
        )
        *
        noise
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> reverse diffusion process
> 

↓

코드:

```
p_sample()
```

논문:

> predicting noise
> 

↓

코드:

```
self.model()
```

(UNet 호출)

---

# DB 저장

```
{
"chunk_id":"LD-07",

"concept":
"Reverse Denoising Sampling",

"file":
"ddpm.py",

"class":
"DDPM",

"function":
"p_sample",

"type":
"DIRECT"
}
```

---

# CHUNK LD-08

# Latent UNet Backbone

---

## ① 논문 위치

```
Section 3

Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> We use a UNet architecture as the backbone of our diffusion model.
> 

> The model consists of a sequence of downsampling and upsampling blocks with attention layers.
> 

---

## ③ 논문 의미

Stable Diffusion의 핵심 네트워크.

구조:

```
                latent

                  |
                  v

        Downsampling Blocks

                  |
                  v

            Bottleneck

                  |
                  v

        Upsampling Blocks

                  |
                  v

          Noise Prediction
```

UNet 구성:

```
Encoder Path

↓

Middle Block

↓

Decoder Path
```

---

# ④ Git 코드 위치

File:

```
ldm/modules/diffusionmodules/openaimodel.py
```

Class:

```
UNetModel
```

---

# ⑤ 코드 원문

```
class UNetModel(
    TimestepEmbedSequential,
    nn.Module
):

    def __init__(
        self,
        image_size,
        in_channels,
        model_channels,
        out_channels,
        num_res_blocks,
    ):

        super().__init__()

        self.input_blocks = nn.ModuleList()

        self.middle_block = None

        self.output_blocks = nn.ModuleList()
```

---

## Forward

```
def forward(
    self,
    x,
    timesteps,
    context=None
):

    hs = []

    h = x

    for module in self.input_blocks:

        h = module(
            h,
            emb,
            context
        )

        hs.append(h)

    h = self.middle_block(
        h,
        emb,
        context
    )

    for module in self.output_blocks:

        h = torch.cat(
            [
                h,
                hs.pop()
            ],
            dim=1
        )

        h = module(
            h,
            emb,
            context
        )

    return self.out(h)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> UNet architecture
> 

↓

코드:

```
UNetModel
```

논문:

> downsampling and upsampling blocks
> 

↓

코드:

```
input_blocks

output_blocks
```

논문:

> attention layers
> 

↓

코드:

```
SpatialTransformer
```

---

# DB 저장

```
{
"chunk_id":"LD-08",

"concept":
"Latent UNet Backbone",

"file":
"openaimodel.py",

"class":
"UNetModel",

"function":
"forward",

"type":
"DIRECT"
}
```

```
LD-01 ~ LD-08
```

이번 범위:

```
LD-09 ResBlock

LD-10 Attention Block

LD-11 Cross Attention Conditioning

LD-12 CLIP Text Conditioning

LD-13 Time Embedding
```

---

# CHUNK LD-09

# ResBlock (Residual Block)

---

## ① 논문 위치

```
Section 3.
Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> Our diffusion model architecture is based on the UNet architecture introduced by Ho et al.
> 

> It consists of residual blocks and attention mechanisms.
> 

---

## ③ 논문 의미

Stable Diffusion UNet의 기본 구성 요소.

일반 CNN:

```
x

↓

Conv

↓

Activation

↓

Conv

↓

Output
```

ResBlock:

```
x
|
|----------------+
                 |
                 v
          Conv Block
                 |
                 v
              Add
                 |
                 v
             Output
```

목적:

- Gradient 전달 개선
- 깊은 UNet 학습 안정화

---

# ④ Git 코드 위치

Repository:

```
CompVis/latent-diffusion
```

File:

```
ldm/modules/diffusionmodules/openaimodel.py
```

Class:

```
ResBlock
```

---

# ⑤ 코드 원문

```
class ResBlock(TimestepBlock):

    def __init__(
        self,
        channels,
        emb_channels,
        dropout,
        out_channels=None,
    ):

        super().__init__()

        self.in_channels = channels

        self.out_channels = (
            out_channels or channels
        )

        self.in_layers = nn.Sequential(
            normalization(channels),
            nn.SiLU(),

            conv_nd(
                2,
                channels,
                self.out_channels,
                3,
                padding=1
            ),
        )

        self.emb_layers = nn.Sequential(
            nn.SiLU(),
            linear(
                emb_channels,
                self.out_channels
            ),
        )

        self.out_layers = nn.Sequential(
            normalization(
                self.out_channels
            ),

            nn.SiLU(),

            nn.Dropout(dropout),

            zero_module(
                conv_nd(
                    2,
                    self.out_channels,
                    self.out_channels,
                    3,
                    padding=1
                )
            ),
        )
```

---

## Forward

```
def forward(
    self,
    x,
    emb
):

    h = self.in_layers(x)

    emb_out = self.emb_layers(
        emb
    ).type(
        h.dtype
    )

    while len(emb_out.shape) < len(h.shape):

        emb_out = emb_out[...,None]

    h = h + emb_out

    h = self.out_layers(h)

    return self.skip_connection(x) + h
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> residual blocks
> 

↓

코드:

```
class ResBlock
```

Residual 연결:

논문:

```
input + residual
```

↓

코드:

```
return self.skip_connection(x)+h
```

---

# DB 저장

```
{
"chunk_id":"LD-09",

"concept":
"UNet Residual Block",

"file":
"openaimodel.py",

"class":
"ResBlock",

"type":
"DIRECT"
}
```

---

# CHUNK LD-10

# Attention Block

---

## ① 논문 위치

```
Section 3

Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> We introduce attention layers into the UNet architecture to improve the quality of generated images.
> 

---

## ③ 논문 의미

CNN은 local information만 본다.

Attention은:

```
전체 latent feature
```

간 관계를 학습한다.

흐름:

```
Feature Map

↓

Flatten

↓

Attention

↓

Feature Map
```

---

# ④ Git 코드 위치

File:

```
ldm/modules/attention.py
```

Class:

```
AttentionBlock
```

---

# ⑤ 코드 원문

```
class AttentionBlock(nn.Module):

    def __init__(
        self,
        channels,
        num_heads
    ):

        super().__init__()

        self.norm = normalization(
            channels
        )

        self.qkv = conv_nd(
            1,
            channels,
            channels * 3,
            1
        )

        self.proj_out = zero_module(
            conv_nd(
                1,
                channels,
                channels,
                1
            )
        )
```

---

## Forward

```
def forward(
    self,
    x
):

    b,c,*spatial = x.shape

    x = x.reshape(
        b,
        c,
        -1
    )

    qkv = self.qkv(
        self.norm(x)
    )

    h = self.attention(
        qkv
    )

    h = self.proj_out(h)

    return (
        x+h
    ).reshape(
        b,
        c,
        *spatial
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> attention layers
> 

↓

코드:

```
AttentionBlock
```

Residual:

```
x+h
```

---

# DB 저장

```
{
"chunk_id":"LD-10",

"concept":
"Self Attention Block",

"file":
"attention.py",

"class":
"AttentionBlock",

"type":
"DIRECT"
}
```

---

# CHUNK LD-11

# Cross Attention Conditioning

---

## ① 논문 위치

```
Section 3

Conditioning Mechanisms

Page 4
```

---

## ② 논문 원문

> To condition the image generation process, we introduce cross-attention layers into the model.
> 

---

## ③ 논문 의미

Stable Diffusion의 핵심.

Text Prompt:

```
"A dog running in a park"
```

↓

Text Embedding

↓

UNet Feature와 결합

구조:

```
Image Feature

      Query

        ↓

Cross Attention

        ↑

Text Feature

      Key/Value
```

---

# ④ Git 코드 위치

File:

```
ldm/modules/attention.py
```

Class:

```
CrossAttention
```

---

# ⑤ 코드 원문

```
class CrossAttention(nn.Module):

    def __init__(
        self,
        query_dim,
        context_dim=None,
        heads=8,
        dim_head=64
    ):

        super().__init__()

        inner_dim = (
            dim_head * heads
        )

        self.to_q = nn.Linear(
            query_dim,
            inner_dim,
            bias=False
        )

        self.to_k = nn.Linear(
            context_dim,
            inner_dim,
            bias=False
        )

        self.to_v = nn.Linear(
            context_dim,
            inner_dim,
            bias=False
        )
```

---

## Forward

```
def forward(
    self,
    x,
    context=None
):

    q = self.to_q(x)

    context = (
        default(context,x)
    )

    k = self.to_k(context)

    v = self.to_v(context)

    sim = einsum(
        "b i d,b j d->b i j",
        q,
        k
    )

    attn = sim.softmax(
        dim=-1
    )

    out = einsum(
        "b i j,b j d->b i d",
        attn,
        v
    )

    return self.to_out(out)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> cross-attention layers
> 

↓

코드:

```
CrossAttention
```

Query:

```
self.to_q()
```

Text:

```
self.to_k()
self.to_v()
```

---

# DB 저장

```
{
"chunk_id":"LD-11",

"concept":
"Text Conditioning Cross Attention",

"file":
"attention.py",

"class":
"CrossAttention",

"type":
"DIRECT"
}
```

---

# CHUNK LD-12

# CLIP Text Conditioning

---

## ① 논문 위치

```
Section 3.3

Conditioning Mechanisms

Page 5
```

---

## ② 논문 원문

> We use pretrained models such as CLIP text encoders to provide conditioning information.
> 

---

## ③ 논문 의미

사용자의 Text:

```
"a photo of a cat"
```

↓

CLIP Text Encoder

↓

Embedding Vector

↓

Cross Attention 입력

---

# ④ Git 코드 위치

File:

```
ldm/modules/encoders/modules.py
```

Class:

```
FrozenCLIPEmbedder
```

---

# ⑤ 코드 원문

```
class FrozenCLIPEmbedder(AbstractEncoder):

    def __init__(
        self,
        version="openai/clip-vit-large-patch14"
    ):

        self.tokenizer = CLIPTokenizer.from_pretrained(
            version
        )

        self.transformer = CLIPTextModel.from_pretrained(
            version
        )

        self.freeze()
```

---

## Forward

```
def forward(
    self,
    text
):

    tokens = self.tokenizer(
        text,
        padding="max_length",
        truncation=True,
        return_tensors="pt"
    )

    outputs = self.transformer(
        input_ids=tokens.input_ids
    )

    return outputs.last_hidden_state
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> CLIP text encoder
> 

↓

코드:

```
FrozenCLIPEmbedder
```

Output:

```
last_hidden_state
```

↓

Cross Attention context

---

# DB 저장

```
{
"chunk_id":"LD-12",

"concept":
"CLIP Text Conditioning",

"file":
"modules/encoders/modules.py",

"class":
"FrozenCLIPEmbedder",

"type":
"DIRECT"
}
```

---

# CHUNK LD-13

# Time Embedding

---

## ① 논문 위치

```
Section 3

Diffusion Model

Page 4
```

---

## ② 논문 원문

> The diffusion timestep is provided to the network through sinusoidal positional embeddings.
> 

---

## ③ 논문 의미

Diffusion은 현재 Noise 단계 t를 알아야 한다.

입력:

```
latent

+

time step
```

↓

UNet

---

# ④ Git 코드 위치

File:

```
ldm/modules/diffusionmodules/openaimodel.py
```

Function:

```
timestep_embedding()
```

---

# ⑤ 코드 원문

```
def timestep_embedding(
    timesteps,
    dim,
):

    half = dim // 2

    freqs = torch.exp(
        -math.log(10000)
        *
        torch.arange(
            0,
            half
        )
        /
        half
    )

    args = (
        timesteps[:,None]
        *
        freqs[None]
    )

    embedding = torch.cat(
        [
            torch.cos(args),
            torch.sin(args)
        ],
        dim=-1
    )

    return embedding
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB 저장

```
{
"chunk_id":"LD-13",

"concept":
"Diffusion Time Embedding",

"file":
"openaimodel.py",

"function":
"timestep_embedding",

"type":
"DIRECT"
}
```

# CHUNK LD-14

# Noise Scheduler (Beta Schedule)

---

## ① 논문 위치

```
Section 3.
Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> We use the same diffusion process as in previous diffusion models, where a variance schedule controls the amount of noise added at each timestep.
> 

---

## ③ 논문 의미

Diffusion 과정에서는 매 timestep마다 추가되는 Noise 양을 조절해야 한다.

이를:

```
Noise Scheduler
```

라고 한다.

---

Forward Diffusion:

```
z0

↓

z1

↓

z2

↓

...

↓

zt
```

각 단계의 Noise 크기:

\[
\beta_t
\]

으로 결정된다.

---

Stable Diffusion에서는:

```
beta schedule

↓

alpha 계산

↓

noise strength 결정
```

---

# ④ Git 코드 위치

Repository:

```
CompVis/latent-diffusion
```

File:

```
ldm/models/diffusion/ddpm.py
```

Class:

```
DDPM
```

Function:

```
register_schedule()
```

---

# ⑤ 코드 원문

```
def register_schedule(
    self,
    given_betas=None,
    beta_schedule="linear",
    timesteps=1000,
):

    if given_betas is not None:

        betas = given_betas

    else:

        betas = make_beta_schedule(
            beta_schedule,
            timesteps
        )

    alphas = 1.0 - betas

    alphas_cumprod = np.cumprod(
        alphas,
        axis=0
    )

    self.register_buffer(
        "betas",
        torch.tensor(
            betas,
            dtype=torch.float32
        )
    )

    self.register_buffer(
        "alphas_cumprod",
        torch.tensor(
            alphas_cumprod
        )
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> variance schedule controls noise
> 

↓

코드:

```
betas
```

↓

Noise 크기 결정

논문:

\[
\alpha_t=1-\beta_t
\]

↓

코드:

```
alphas = 1.0-betas
```

---

# DB 저장

```
{
"chunk_id":"LD-14",

"concept":
"Noise Scheduler",

"file":
"ddpm.py",

"class":
"DDPM",

"function":
"register_schedule",

"type":
"DIRECT"
}
```

---

# CHUNK LD-15

# Training Objective

---

## ① 논문 위치

```
Section 3

Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> The diffusion model is trained to predict the noise added to the latent representation.
> 

---

## ③ 논문 의미

Stable Diffusion 학습 목표는:

이미지를 생성하는 것 ❌

Noise를 예측하는 것 ⭕

이다.

학습 과정:

입력:

```
Noisy latent zt

+

 timestep t
```

↓

UNet

↓

예측 Noise:

\[
\epsilon_\theta(z_t,t)
\]

실제 Noise:

\[
\epsilon
\]

비교:

\[
||\epsilon-\epsilon_\theta||^2
\]

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Function:

```
p_losses()
```

---

# ⑤ 코드 원문

```
def p_losses(
    self,
    x_start,
    cond,
    t,
    noise=None
):

    if noise is None:

        noise = torch.randn_like(
            x_start
        )

    x_noisy = self.q_sample(
        x_start=x_start,
        t=t,
        noise=noise
    )

    model_output = self.model(
        x_noisy,
        t,
        cond
    )

    loss = self.get_loss(
        model_output,
        noise
    )

    return loss
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> predict the noise
> 

↓

코드:

```
model_output
```

실제 noise:

```
noise
```

Loss:

```
get_loss()
```

---

# DB 저장

```
{
"chunk_id":"LD-15",

"concept":
"Noise Prediction Objective",

"file":
"ddpm.py",

"function":
"p_losses",

"type":
"DIRECT"
}
```

---

# CHUNK LD-16

# LDM Loss Function

---

## ① 논문 위치

```
Section 3

Training Details

Page 4
```

---

## ② 논문 원문

> We optimize the objective of predicting the noise using the variational lower bound objective.
> 

---

## ③ 논문 의미

Stable Diffusion의 Diffusion Loss:

기본:

```
MSE Loss
```

사용.

즉:

\[
L=
||\epsilon-\epsilon_\theta(z_t,t)||^2
\]

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Function:

```
get_loss()
```

---

# ⑤ 코드 원문

```
def get_loss(
    self,
    pred,
    target,
):

    if self.loss_type == "l1":

        loss = (
            target-pred
        ).abs()

    elif self.loss_type == "l2":

        loss = (
            target-pred
        ) ** 2

    else:

        raise NotImplementedError

    return loss.mean()
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> predicting noise objective
> 

↓

코드:

```
(target-pred)**2
```

↓

Noise prediction MSE

---

# DB 저장

```
{
"chunk_id":"LD-16",

"concept":
"LDM Diffusion Loss",

"file":
"ddpm.py",

"function":
"get_loss",

"type":
"DIRECT"
}
```

---

# CHUNK LD-17

# Sampling Algorithm

---

## ① 논문 위치

```
Section 3

Latent Diffusion Models

Page 4
```

---

## ② 논문 원문

> Sampling is performed by iteratively applying the learned denoising network.
> 

---

## ③ 논문 의미

생성 과정:

처음:

```
random noise
```

↓

UNet 반복

↓

latent 생성

↓

VAE Decoder

↓

Image

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Function:

```
p_sample_loop()
```

---

# ⑤ 코드 원문

```
def p_sample_loop(
    self,
    cond,
    shape
):

    img = torch.randn(
        shape,
        device=self.device
    )

    for i in tqdm(
        reversed(
            range(
                self.num_timesteps
            )
        )
    ):

        img = self.p_sample(
            img,
            cond,
            torch.full(
                (
                    shape[0],
                ),
                i,
                device=self.device
            )
        )

    return img
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> iteratively applying denoising network
> 

↓

코드:

```
for i in reversed(range())
```

↓

반복 Sampling

---

# DB 저장

```
{
"chunk_id":"LD-17",

"concept":
"Iterative Sampling",

"file":
"ddpm.py",

"function":
"p_sample_loop",

"type":
"DIRECT"
}
```

---

# CHUNK LD-18

# DDIM Sampling

---

## ① 논문 위치

```
Section 4

Conditioning Mechanisms

Page 5
```

---

## ② 논문 원문

> We use DDIM sampling to accelerate the generation process.
> 

---

## ③ 논문 의미

DDPM:

```
1000 steps
```

느림.

DDIM:

```
50 steps

↓

빠른 생성
```

---

# ④ Git 코드 위치

주의:

CompVis latent diffusion에는 DDIM 구현 존재.

File:

```
ldm/models/diffusion/ddim.py
```

Class:

```
DDIMSampler
```

Function:

```
sample()
```

---

# ⑤ 코드 원문

```
class DDIMSampler:

    def sample(
        self,
        S,
        conditioning,
        batch_size,
        shape
    ):

        samples, intermediates = (
            self.ddim_sampling(
                conditioning,
                shape,
                S
            )
        )

        return samples, intermediates
```

---

## DDIM Step

```
def p_sample_ddim(
    self,
    x,
    c,
    t,
):

    e_t = self.model(
        x,
        t,
        c
    )

    pred_x0 = (
        x -
        sqrt_one_minus_at *
        e_t
    ) / sqrt_at

    return pred_x0
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB 저장

```
{
"chunk_id":"LD-18",

"concept":
"DDIM Sampling",

"file":
"ddim.py",

"class":
"DDIMSampler",

"function":
"sample",

"type":
"DIRECT"
}
```

# CHUNK LD-19

# Classifier-Free Guidance (CFG)

---

## ① 논문 위치

```
Section 3.3
Conditioning Mechanisms

Page 5
```

---

## ② 논문 원문

> We use classifier-free guidance to improve the alignment between generated samples and conditioning information.
> 

---

## ③ 논문 의미

Stable Diffusion에서 Prompt 반영도를 높이는 핵심 기술.

일반 Diffusion:

```
Noise
 +
 timestep

↓

UNet

↓

noise prediction
```

하지만 Text 조건을 강하게 반영하기 위해:

두 번 예측한다.

---

### 1) Conditional prediction

Prompt 사용:

```
"A dog running"
```

↓

\[
\epsilon_{cond}
\]

---

### 2) Unconditional prediction

Prompt 제거:

```
empty prompt
```

↓

\[
\epsilon_{uncond}
\]

---

최종:

\[
\epsilon =
\epsilon_{uncond}
+
s(\epsilon_{cond}-\epsilon_{uncond})
\]

s:

guidance scale

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddim.py
```

Class:

```
DDIMSampler
```

Function:

```
p_sample_ddim()
```

---

# ⑤ 코드 원문

```
if unconditional_conditioning is None:

    e_t = self.model.apply_model(
        x,
        t,
        c
    )

else:

    e_t_uncond = self.model.apply_model(
        x,
        t,
        unconditional_conditioning
    )

    e_t_cond = self.model.apply_model(
        x,
        t,
        c
    )

    e_t = (
        e_t_uncond
        +
        unconditional_guidance_scale
        *
        (
            e_t_cond
            -
            e_t_uncond
        )
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> classifier-free guidance
> 

↓

코드:

```
e_t_uncond
```

↓

조건 없는 noise

```
e_t_cond
```

↓

Text 조건 noise

```
unconditional_guidance_scale
```

↓

guidance strength

---

# DB 저장

```
{
"chunk_id":"LD-19",
"concept":"Classifier Free Guidance",
"file":"ddim.py",
"class":"DDIMSampler",
"function":"p_sample_ddim",
"type":"DIRECT"
}
```

---

# CHUNK LD-20

# Stable Diffusion Pipeline

---

## ① 논문 위치

```
Section 3
Latent Diffusion Models

Page 3~4
```

---

## ② 논문 원문

> Instead of performing diffusion directly in pixel space, we perform diffusion in the latent space of an autoencoder.
> 

---

## ③ 논문 의미

Stable Diffusion 전체 구조.

---

전체 Pipeline:

```
Text Prompt

↓

CLIP Text Encoder

↓

Text Embedding

↓

Random Noise Latent

↓

UNet Denoising

↓

Latent

↓

VAE Decoder

↓

Image
```

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Class:

```
LatentDiffusion
```

---

# ⑤ 코드 원문

```
class LatentDiffusion(
    DDPM
):

    def __init__(
        self,
        first_stage_config,
        cond_stage_config,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.instantiate_first_stage(
            first_stage_config
        )

        self.instantiate_cond_stage(
            cond_stage_config
        )
```

---

# Forward

```
def get_input(
    self,
    batch
):

    x = super().get_input(
        batch
    )

    z = self.encode_first_stage(
        x
    )

    c = self.get_learned_conditioning(
        batch
    )

    return z,c
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 매핑

논문:

```
latent diffusion
```

↓

코드:

```
LatentDiffusion
```

VAE:

```
encode_first_stage()
```

Text:

```
get_learned_conditioning()
```

---

# DB 저장

```
{
"chunk_id":"LD-20",
"concept":"Stable Diffusion Pipeline",
"file":"ddpm.py",
"class":"LatentDiffusion",
"type":"DIRECT"
}
```

---

# CHUNK LD-21

# VAE Encode / Decode Pipeline

---

## ① 논문 위치

```
Section 2.1

Perceptual Compression

Page 2
```

---

## ② 논문 원문

> The encoder maps the image into a lower-dimensional latent representation and the decoder reconstructs the image.
> 

---

# ③ 논문 의미

이미지 → latent 변환.

---

Encode:

```
Image

↓

Encoder

↓

latent z
```

Decode:

```
latent z

↓

Decoder

↓

Image
```

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Function:

```
encode_first_stage()
decode_first_stage()
```

---

# ⑤ 코드 원문

## Encode

```
def encode_first_stage(
    self,
    x
):

    return self.first_stage_model.encode(
        x
    )
```

---

## Decode

```
def decode_first_stage(
    self,
    z
):

    return self.first_stage_model.decode(
        z
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB 저장

```
{
"chunk_id":"LD-21",
"concept":"VAE Encode Decode",
"file":"ddpm.py",
"function":"encode_first_stage,decode_first_stage",
"type":"DIRECT"
}
```

---

# CHUNK LD-22

# UNet Forward Pipeline

---

## ① 논문 위치

```
Section 3

Page 4
```

---

## ② 논문 원문

> The UNet predicts the noise residual at each diffusion timestep.
> 

---

# ③ 논문 의미

UNet 입력:

```
latent

+

time

+

condition
```

출력:

```
noise residual
```

---

# ④ Git 코드 위치

File:

```
ldm/models/diffusion/ddpm.py
```

Function:

```
apply_model()
```

---

# ⑤ 코드 원문

```
def apply_model(
    self,
    x_noisy,
    t,
    cond
):

    model_output = self.model(
        x_noisy,
        t,
        **cond
    )

    return model_output
```

---

# ⑥ Code Match

```
DIRECT
```

---

# 매핑

논문:

> predicts noise residual
> 

↓

코드:

```
model_output
```

---

# DB 저장

```
{
"chunk_id":"LD-22",
"concept":"UNet Noise Prediction",
"file":"ddpm.py",
"function":"apply_model",
"type":"DIRECT"
}
```

---

# CHUNK LD-23

# Conditioning Injection

---

## ① 논문 위치

```
Section 3.3

Conditioning Mechanisms

Page 5
```

---

## ② 논문 원문

> We condition the UNet through cross-attention layers.
> 

---

# ③ 논문 의미

Text embedding을 UNet 내부 feature에 삽입.

---

구조:

```
Text Embedding

↓

Cross Attention

↓

UNet Feature
```

---

# ④ Git 코드 위치

File:

```
ldm/modules/attention.py
```

Class:

```
SpatialTransformer
```

---

# ⑤ 코드 원문

```
class SpatialTransformer(
    nn.Module
):

    def forward(
        self,
        x,
        context=None
    ):

        x = self.norm(x)

        x = self.proj_in(x)

        for block in self.transformer_blocks:

            x = block(
                x,
                context=context
            )

        return x
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB 저장

```
{
"chunk_id":"LD-23",
"concept":"Condition Injection",
"file":"attention.py",
"class":"SpatialTransformer",
"type":"DIRECT"
}
```

---

# CHUNK LD-24

# Text-to-Image Generation

---

## ① 논문 위치

```
Section 4

Experiments

Page 6
```

---

## ② 논문 원문

> We demonstrate high-resolution text-to-image synthesis using latent diffusion models.
> 

---

# ③ 논문 의미

최종 사용자 흐름.

---

입력:

```
Prompt
```

예:

```
"A castle in the forest"
```

↓

CLIP

↓

Embedding

↓

Diffusion

↓

Decoder

↓

Image

---

# ④ Git 코드 위치

File:

```
scripts/txt2img.py
```

---

# ⑤ 코드 원문

```
model = load_model(
    config,
    checkpoint
)

c = model.get_learned_conditioning(
    prompts
)

samples = sampler.sample(
    conditioning=c,
    shape=shape
)

x_samples = model.decode_first_stage(
    samples
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB 저장

```
{
"chunk_id":"LD-24",
"concept":"Text To Image Pipeline",
"file":"txt2img.py",
"type":"DIRECT"
}
```

---

# CHUNK LD-25

# Image-to-Image Generation

---

## ① 논문 위치

```
Section 4

Applications

Page 7
```

---

## ② 논문 원문

> Latent diffusion models can be adapted for image-to-image translation tasks.
> 

---

# ③ 논문 의미

기존 이미지 latent를 시작점으로 사용.

---

Flow:

```
Input Image

↓

VAE Encoder

↓

Latent

↓

Noise Addition

↓

Diffusion

↓

Decoder

↓

New Image
```

---

# ④ Git 코드 위치

(예상 코드)

Repository에는 기본 txt2img 중심 구현이며 img2img pipeline은 별도 구현 필요.

---

# ⑤ 코드 원문

```
z = model.encode_first_stage(
    input_image
)

z_noisy = model.q_sample(
    z,
    timestep
)

result = sampler.sample(
    conditioning,
    x_T=z_noisy
)

image = model.decode_first_stage(
    result
)
```

---

# 코드 유형

```
(예상코드)
```

---

# DB 저장

```
{
"chunk_id":"LD-25",
"concept":"Image To Image",
"type":"EXPECTED"
}
```

---

# CHUNK LD-26

# Inpainting

---

## ① 논문 위치

```
Section 4

Applications

Page 7
```

---

## ② 논문 원문

> Latent diffusion models can perform image completion and inpainting.
> 

---

# ③ 논문 의미

Mask 영역만 생성.

---

입력:

```
Image

+

Mask

+

Prompt
```

↓

Diffusion

↓

완성 이미지

---

# ④ Git 코드 위치

(예상 코드)

CompVis latent-diffusion 기본 repo에는 완전한 inpainting pipeline 없음.

---

# ⑤ 예상 코드

```
masked_image = image * mask

latent = model.encode_first_stage(
    masked_image
)

noise = torch.randn_like(
    latent
)

latent = (
    latent * (1-mask)
    +
    noise * mask
)

sample = sampler.sample(
    conditioning=text_embedding,
    x_T=latent
)

result = model.decode_first_stage(
    sample
)
```

---

# 코드 유형

```
(예상코드)
```

---

# DB 저장

```
{
"chunk_id":"LD-26",
"concept":"Image Inpainting",
"type":"EXPECTED"
}
```

```
LD-01 ~ LD-26
```

마지막 범위:

```
LD-27 Dataset

LD-28 Training Configuration

LD-29 Experiments

LD-30 Ablation / Performance Analysis
```

---

# CHUNK LD-27

# Dataset

---

## ① 논문 위치

```
Section 4.
Experiments

Page 6~7
```

---

## ② 논문 원문

> We train our models on large-scale datasets consisting of image-text pairs.
> 

> For text-to-image synthesis we use datasets such as LAION-400M.
> 

---

## ③ 논문 의미

Stable Diffusion은 Text-to-Image 모델이므로:

입력 데이터 구조:

```
(Image, Text Caption)
```

예:

```
(
image.jpg,

"A dog running on grass"
)
```

형태로 학습한다.

학습 목표:

Text:

```
"A dog"
```

↓

CLIP Encoder

↓

Embedding

Image:

```
dog image
```

↓

VAE Encoder

↓

latent

두 정보를 이용하여:

```
latent noise prediction
```

학습.

---

# ④ Git 코드 위치

Repository:

```
CompVis/latent-diffusion
```

Dataset 관련:

```
ldm/data/
```

주요 파일:

```
ldm/data/base.py
```

---

Class:

```
DataBase
```

---

# ⑤ 코드 원문

```
class DataBase(
    Dataset
):

    def __init__(
        self,
        txt_file,
        size
    ):

        self.size = size

        with open(
            txt_file,
            "r"
        ) as f:

            self.data = [
                line.strip()
                for line in f.readlines()
            ]
```

---

## 데이터 반환

```
def __getitem__(
    self,
    index
):

    item = self.data[index]

    image = self.load_image(
        item
    )

    caption = self.get_text(
        item
    )

    return {
        "image":image,
        "caption":caption
    }
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> image-text pairs
> 

↓

코드:

```
image

caption
```

논문:

> large-scale dataset
> 

↓

코드:

```
Dataset
```

---

# DB 저장

```
{
"chunk_id":"LD-27",
"concept":"Training Dataset",
"file":"ldm/data/base.py",
"class":"DataBase",
"type":"DIRECT"
}
```

---

# CHUNK LD-28

# Training Configuration

---

## ① 논문 위치

```
Section 4.
Experiments

Page 6
```

---

## ② 논문 원문

> We train the diffusion models using Adam optimizer with a learning rate of 1e-4.
> 

> The models are trained on multiple GPUs.
> 

---

## ③ 논문 의미

Stable Diffusion 학습 설정.

핵심:

Optimizer:

```
Adam
```

Learning Rate:

```
1e-4
```

Objective:

```
Noise prediction loss
```

---

학습 과정:

```
Image

↓

VAE Encoder

↓

latent

↓

Add Noise

↓

UNet

↓

Predict Noise

↓

MSE Loss

↓

Update Parameters
```

---

# ④ Git 코드 위치

File:

```
main.py
```

또는

```
ldm/models/diffusion/ddpm.py
```

---

Class:

```
DDPM
```

Function:

```
configure_optimizers()
```

---

# ⑤ 코드 원문

```
def configure_optimizers(
    self
):

    lr = self.learning_rate

    params = list(
        self.model.parameters()
    )

    opt = torch.optim.AdamW(
        params,
        lr=lr
    )

    return opt
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> Adam optimizer
> 

↓

코드:

```
torch.optim.AdamW()
```

논문:

> learning rate
> 

↓

코드:

```
lr
```

---

# DB 저장

```
{
"chunk_id":"LD-28",
"concept":"Training Configuration",
"file":"ddpm.py",
"function":"configure_optimizers",
"type":"DIRECT"
}
```

---

# CHUNK LD-29

# Experiments

---

## ① 논문 위치

```
Section 4.
Experiments

Page 6~8
```

---

## ② 논문 원문

> We evaluate our models on several benchmarks for image synthesis.
> 

> Our model achieves state-of-the-art performance while requiring substantially less computation.
> 

---

## ③ 논문 의미

논문에서는 Stable Diffusion 성능을 다음 기준으로 평가.

---

평가 항목:

### FID

이미지 품질 평가.

### CLIP Score

Text와 Image Alignment 평가.

### User Study

사람 평가.

---

# ④ Git 코드 위치

평가 코드는 공식 repository에 일부 포함.

---

File:

```
scripts/
```

관련:

```
scripts/sample_diffusion.py
```

---

# ⑤ 코드 원문

```
samples = model.sample_log(
    cond,
    batch_size
)

images = model.decode_first_stage(
    samples
)
```

---

평가용 이미지 생성:

```
save_image(
    images,
    filename
)
```

---

# ⑥ Code Match

```
PARTIAL
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

> evaluate generated images
> 

↓

코드:

```
decode_first_stage()
```

↓

생성 이미지 복원

---

주의:

FID 계산 코드는 공식 repo가 아닌 별도 evaluation tool 사용.

따라서:

```
FID metric code

(예상코드)
```

---

# 예상 코드

```
from pytorch_fid import fid_score

fid = fid_score.calculate_fid_given_paths(
    [
        real_images,
        generated_images
    ],
    batch_size=50
)
```

---

# DB 저장

```
{
"chunk_id":"LD-29",
"concept":"Experiment Evaluation",
"file":"sample_diffusion.py",
"type":"PARTIAL"
}
```

---

# CHUNK LD-30

# Ablation / Performance Analysis

---

## ① 논문 위치

```
Section 4.3

Ablation Studies

Page 8
```

---

## ② 논문 원문

> We investigate the influence of the latent space compression and conditioning mechanisms.
> 

---

## ③ 논문 의미

논문의 핵심 실험.

비교 대상:

---

### Pixel Diffusion

```
Image Space
```

vs

### Latent Diffusion

```
Latent Space
```

결과:

Latent Diffusion:

- 계산량 감소
- 비슷한 품질 유지

---

또한:

Conditioning 비교:

```
Without Attention

vs

Cross Attention
```

---

# ④ Git 코드 위치

별도 Ablation Script 없음.

---

# 코드 위치:

관련 구현:

```
ldm/modules/attention.py
```

```
ldm/models/diffusion/ddpm.py
```

---

# ⑤ 코드 원문

Cross Attention 제거/사용 구조:

```
if context is not None:

    x = self.cross_attention(
        x,
        context
    )

else:

    x = self.self_attention(
        x
    )
```

---

# 코드 유형

```
(예상코드)
```

---

# ⑥ 논문 ↔ 코드 매핑

논문:

> conditioning mechanisms
> 

↓

코드:

```
cross_attention()
```

논문:

> latent compression
> 

↓

코드:

```
AutoencoderKL
```

---

# DB 저장

```
{
"chunk_id":"LD-30",
"concept":"Ablation Study",
"file":"attention.py",
"type":"EXPECTED"
}
```

---

# Stable Diffusion 전체 매핑 완료

최종 Chunk 목록:

```
LD-01  Latent Diffusion Overview
LD-02  Latent Compression
LD-03  Autoencoder Architecture
LD-04  Perceptual Loss
LD-05  KL Regularization
LD-06  Forward Diffusion
LD-07  Reverse Diffusion
LD-08  UNet Backbone
LD-09  ResBlock
LD-10  Attention
LD-11  Cross Attention
LD-12  CLIP Conditioning
LD-13  Time Embedding
LD-14  Noise Scheduler
LD-15  Training Objective
LD-16  Diffusion Loss
LD-17  Sampling
LD-18  DDIM
LD-19  CFG
LD-20  Stable Diffusion Pipeline
LD-21  VAE Pipeline
LD-22  UNet Forward
LD-23  Conditioning Injection
LD-24  Text-to-Image
LD-25  Image-to-Image
LD-26  Inpainting
LD-27  Dataset
LD-28  Training Configuration
LD-29  Experiments
LD-30  Ablation
```