# Segment anything

# CHUNK SAM-01

# SAM 전체 Architecture

---

## ① 논문 위치

```
Section 3. Segment Anything Model

Page 5
```

---

## ② 논문 원문

> The Segment Anything Model (SAM) consists of three components: an image encoder, a prompt encoder, and a mask decoder.
> 

---

## ③ 논문 의미

이 문장은 SAM의 전체 구조를 정의한다.

SAM은 세 개의 주요 모듈로 구성된다.

```
Image Encoder

Prompt Encoder

Mask Decoder
```

전체 inference 과정:

```
Image
 |
 |
Image Encoder
 |
 |
Image Embedding

+
Prompt

 |
 |
Prompt Encoder

 |
 |
Mask Decoder

 |
 |
Mask
```

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/modeling/sam.py
```

Class:

```
Sam
```

Function:

```
__init__()
forward()
```

---

# ⑤ 코드 원문

```
class Sam(nn.Module):
    mask_threshold: float = 0.0

    def __init__(
        self,
        image_encoder: ImageEncoderViT,
        prompt_encoder: PromptEncoder,
        mask_decoder: MaskDecoder,
        pixel_mean: List[float] = [123.675, 116.28, 103.53],
        pixel_std: List[float] = [58.395, 57.12, 57.375],
    ) -> None:
        super().__init__()

        self.image_encoder = image_encoder
        self.prompt_encoder = prompt_encoder
        self.mask_decoder = mask_decoder

        self.register_buffer(
            "pixel_mean",
            torch.Tensor(pixel_mean).view(-1, 1, 1),
            False,
        )

        self.register_buffer(
            "pixel_std",
            torch.Tensor(pixel_std).view(-1, 1, 1),
            False,
        )
```

---

## forward 코드

```
def forward(
    self,
    batched_input: List[Dict[str, Any]],
    multimask_output: bool,
) -> List[Dict[str, torch.Tensor]]:

    input_images = torch.stack(
        [
            self.preprocess(x["image"])
            for x in batched_input
        ],
        dim=0,
    )

    image_embeddings = self.image_encoder(
        input_images
    )

    outputs = []

    for image_record, curr_embedding in zip(
        batched_input,
        image_embeddings
    ):

        sparse_embeddings, dense_embeddings = (
            self.prompt_encoder(
                points=image_record.get("point_coords"),
                boxes=image_record.get("boxes"),
                masks=image_record.get("mask_inputs"),
            )
        )

        low_res_masks, iou_predictions = (
            self.mask_decoder(
                image_embeddings=curr_embedding.unsqueeze(0),
                image_pe=self.prompt_encoder.get_dense_pe(),
                sparse_prompt_embeddings=sparse_embeddings,
                dense_prompt_embeddings=dense_embeddings,
                multimask_output=multimask_output,
            )
        )

        masks = self.postprocess_masks(
            low_res_masks,
            image_record["original_size"],
            image_record["input_size"],
        )

        outputs.append(
            {
                "masks": masks,
                "iou_predictions": iou_predictions,
                "low_res_logits": low_res_masks,
            }
        )

    return outputs
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
SAM consists of:
- image encoder
- prompt encoder
- mask decoder
```

↓

코드:

```
self.image_encoder

self.prompt_encoder

self.mask_decoder
```

↓

실행:

```
image_embeddings =
self.image_encoder()

sparse_embeddings,
dense_embeddings =
self.prompt_encoder()

masks =
self.mask_decoder()
```

---

# DB 저장 형태

```
{
  "paper": "Segment Anything",
  "chunk_id": "SAM-01",

  "paper_location": {
    "section": "3 Segment Anything Model",
    "page": 5
  },

  "concept":
  "Overall SAM Architecture",

  "repository":
  "facebookresearch/segment-anything",

  "file":
  "segment_anything/modeling/sam.py",

  "class":
  "Sam",

  "function":
  [
    "__init__",
    "forward"
  ],

  "mapping":
  "DIRECT"
}
```

---

# CHUNK SAM-02

# Image Encoder

---

## ① 논문 위치

```
Section 3
Segment Anything Model

Subsection:
Image Encoder

Page 5
```

---

## ② 논문 원문

> The image encoder is a Vision Transformer (ViT) that computes a one-time embedding for the image.
> 

---

## ③ 논문 의미

Image Encoder는 입력 이미지를 한번 처리해서 dense image embedding을 만든다.

중요한 점:

SAM에서는 Prompt가 여러 개 들어와도:

```
Image Encoder
```

는 다시 실행하지 않는다.

---

구조:

```
Image

↓

Patch Embedding

↓

ViT Transformer

↓

Image Embedding
```

---

# ④ Git 위치

File:

```
segment_anything/modeling/image_encoder.py
```

Class:

```
ImageEncoderViT
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
class ImageEncoderViT(nn.Module):

    def forward(self, x):

        x = self.patch_embed(x)

        if self.pos_embed is not None:
            x = x + self.pos_embed

        for blk in self.blocks:
            x = blk(x)

        x = self.neck(x)

        return x
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
ViT computes image embedding
```

↓

코드:

```
self.patch_embed()

for blk in self.blocks:

self.neck()
```

↓

결과:

```
Image Embedding
```

---

# DB

```
{
"chunk_id":"SAM-02",

"section":
"Image Encoder",

"file":
"segment_anything/modeling/image_encoder.py",

"class":
"ImageEncoderViT",

"function":
"forward",

"type":
"DIRECT"
}
```

계속 진행한다.

---

# CHUNK SAM-03

# Patch Embedding (Image → Token 변환)

---

## ① 논문 위치

```
Section 3. Segment Anything Model
Subsection: Image Encoder

Page 5
```

---

## ② 논문 원문

> We use a pre-trained MAE ViT-H image encoder. The image encoder processes the image and outputs an image embedding.
> 

---

## ③ 논문 의미

SAM의 Image Encoder는 일반 CNN이 아니라 Vision Transformer(ViT)를 사용한다.

ViT는 이미지를 바로 처리하지 않고:

```
Image
 ↓
Patch 분할
 ↓
Patch Token
 ↓
Transformer Encoder
 ↓
Image Embedding
```

과정을 거친다.

즉 Patch Embedding은 Image Encoder의 첫 단계이다.

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/modeling/image_encoder.py
```

Class:

```
PatchEmbed
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
class PatchEmbed(nn.Module):
    """
    Image to Patch Embedding.
    """

    def __init__(
        self,
        kernel_size: Tuple[int, int],
        stride: Tuple[int, int],
        padding: Tuple[int, int],
        in_chans: int,
        embed_dim: int,
    ):
        super().__init__()

        self.proj = nn.Conv2d(
            in_chans,
            embed_dim,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:

        x = self.proj(x)

        x = x.permute(
            0,
            2,
            3,
            1
        )

        return x
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
Image encoder receives image input
and produces image embedding.
```

↓

코드:

```
self.proj = nn.Conv2d(...)
```

↓

이미지를 patch 단위 feature map으로 변환

논문 개념:

```
Image Patch Tokenization
```

코드:

```
Conv2d with kernel=stride=patch size
```

---

# DB 저장

```
{
"chunk_id":"SAM-03",

"paper_section":
"3 Image Encoder",

"concept":
"Patch Embedding",

"file":
"segment_anything/modeling/image_encoder.py",

"class":
"PatchEmbed",

"function":
"forward",

"type":
"DIRECT"
}
```

---

---

# CHUNK SAM-04

# Vision Transformer Block

---

## ① 논문 위치

```
Section 3
Image Encoder

Page 5
```

---

## ② 논문 원문

> The image encoder is based on ViT-H and produces a high dimensional image embedding.
> 

---

## ③ 논문 의미

Patch Embedding 이후 Transformer Encoder를 통과한다.

SAM에서는:

```
Patch Token

↓

Transformer Block × N

↓

Image Feature
```

구조.

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/image_encoder.py
```

Class:

```
Block
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
class Block(nn.Module):

    def forward(self, x):

        shortcut = x

        x = self.norm1(x)

        x = self.attn(x)

        x = shortcut + x

        x = x + self.mlp(
            self.norm2(x)
        )

        return x
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
ViT encoder computes image representation
```

↓

코드:

```
for blk in self.blocks:
    x = blk(x)
```

↓

각 Transformer Block 수행

---

# DB

```
{
"chunk_id":"SAM-04",

"concept":
"Vision Transformer Encoder Block",

"file":
"image_encoder.py",

"class":
"Block",

"function":
"forward",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-05

# Multi Head Attention

---

## ① 논문 위치

```
Section 3
Image Encoder

Page 5
```

---

## ② 논문 원문

> The image encoder uses a ViT architecture.
> 

---

## ③ 논문 의미

ViT 내부 핵심 연산은 Self Attention이다.

Token 간 관계를 계산한다.

예:

```
Patch A
 ↔
Patch B
 ↔
Patch C
```

서로 정보를 교환.

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/image_encoder.py
```

Class:

```
Attention
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
class Attention(nn.Module):

    def forward(self, x):

        B, H, W, _ = x.shape

        qkv = self.qkv(
            x
        ).reshape(
            B,
            H * W,
            3,
            self.num_heads,
            -1
        )

        qkv = qkv.permute(
            2,
            0,
            3,
            1,
            4
        )

        q, k, v = qkv.unbind(0)

        attn = (
            q @ k.transpose(-2,-1)
        )

        attn = attn * self.scale

        attn = attn.softmax(
            dim=-1
        )

        x = (
            attn @ v
        )

        return x
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
ViT image encoder
```

↓

코드:

```
Attention.forward()
```

↓

구현:

```
Q,K,V 생성
↓
Attention score 계산
↓
Feature aggregation
```

---

# DB

```
{
"chunk_id":"SAM-05",

"concept":
"Self Attention in ViT",

"file":
"image_encoder.py",

"class":
"Attention",

"function":
"forward",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-06

# Prompt Encoder Overview

---

## ① 논문 위치

```
Section 3
Prompt Encoder

Page 5
```

---

## ② 논문 원문

> The prompt encoder takes sparse prompts (points, boxes, text) and dense prompts (masks).
> 

---

## ③ 논문 의미

SAM은 사용자가 제공하는 Prompt를 embedding으로 변환한다.

Prompt 종류:

```
Sparse Prompt

- Point
- Box
- Text

Dense Prompt

- Mask
```

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/prompt_encoder.py
```

Class:

```
PromptEncoder
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
def forward(
    self,
    points=None,
    boxes=None,
    masks=None
):

    sparse_embeddings = self._embed_points(
        points
    )

    if boxes is not None:
        sparse_embeddings = torch.cat(
            [
                sparse_embeddings,
                self._embed_boxes(boxes)
            ],
            dim=1,
        )

    dense_embeddings = self._embed_masks(
        masks
    )

    return (
        sparse_embeddings,
        dense_embeddings
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
Sparse prompts and dense prompts
```

↓

코드:

```
_embed_points()

_embed_boxes()

_embed_masks()
```

---

# DB

```
{
"chunk_id":"SAM-06",

"concept":
"Prompt Encoder",

"file":
"prompt_encoder.py",

"class":
"PromptEncoder",

"function":
"forward",

"type":
"DIRECT"
}
```

# CHUNK SAM-07

# Point Prompt Encoding

---

## ① 논문 위치

```
Section 3. Segment Anything Model

Subsection:
Prompt Encoder

Page 5
```

---

## ② 논문 원문

> Sparse prompts, which include points, boxes, and text, are represented as positional encodings summed with learned embeddings.
> 

---

## ③ 논문 의미

Point Prompt는 단순 좌표값을 사용하는 것이 아니라:

```
(x, y)
 ↓
Position Encoding
 ↓
Learned Embedding 추가
 ↓
Sparse Prompt Embedding
```

으로 변환된다.

사용자가 클릭한 점:

```
Point = (x,y)
```

을 Transformer가 처리할 수 있는 vector로 변환하는 과정.

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/modeling/prompt_encoder.py
```

Class:

```
PromptEncoder
```

Function:

```
_embed_points()
```

---

# ⑤ 코드 원문

```
def _embed_points(
    self,
    points: torch.Tensor,
    labels: torch.Tensor,
    pad: bool,
) -> torch.Tensor:

    points = points + 0.5

    if pad:
        padding_point = torch.zeros(
            (points.shape[0], 1, 2),
            device=points.device
        )

        padding_label = -torch.ones(
            (labels.shape[0], 1),
            device=labels.device
        )

        points = torch.cat(
            [points, padding_point],
            dim=1
        )

        labels = torch.cat(
            [labels, padding_label],
            dim=1
        )

    point_embedding = self.pe_layer.forward_with_coords(
        points,
        self.input_image_size
    )

    point_embedding[
        labels == -1
    ] = 0.0

    point_embedding[
        labels == -1
    ] += self.not_a_point_embed.weight

    point_embedding[
        labels == 0
    ] += self.point_embeddings[0].weight

    point_embedding[
        labels == 1
    ] += self.point_embeddings[1].weight

    return point_embedding
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
point prompts are represented
as positional encodings
with learned embeddings
```

↓

코드:

```
self.pe_layer.forward_with_coords()
```

↓

좌표 embedding 생성

그리고:

```
self.point_embeddings
```

↓

positive / negative point label embedding 추가

---

# DB 저장

```
{
"chunk_id":"SAM-07",

"paper_section":
"Prompt Encoder",

"concept":
"Point Prompt Encoding",

"file":
"segment_anything/modeling/prompt_encoder.py",

"class":
"PromptEncoder",

"function":
"_embed_points",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-08

# Box Prompt Encoding

---

## ① 논문 위치

```
Section 3
Prompt Encoder

Page 5
```

---

## ② 논문 원문

> Sparse prompts include points, boxes, and text.
> 

---

## ③ 논문 의미

Bounding Box Prompt는:

```
(x1,y1)

(x2,y2)
```

두 개의 corner point로 표현한다.

즉 Box도 Point Encoding 방식으로 변환된다.

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/prompt_encoder.py
```

Class:

```
PromptEncoder
```

Function:

```
_embed_boxes()
```

---

# ⑤ 코드 원문

```
def _embed_boxes(
    self,
    boxes: torch.Tensor
) -> torch.Tensor:

    boxes = boxes + 0.5

    coords = boxes.reshape(
        -1,
        2,
        2
    )

    corner_embedding = self.pe_layer.forward_with_coords(
        coords,
        self.input_image_size
    )

    corner_embedding[:,0,:] += (
        self.point_embeddings[2].weight
    )

    corner_embedding[:,1,:] += (
        self.point_embeddings[3].weight
    )

    return corner_embedding
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
box prompt
```

↓

코드:

```
boxes.reshape(
    -1,
    2,
    2
)
```

↓

두 개 corner point 생성

↓

```
point_embeddings[2]
point_embeddings[3]
```

↓

box corner embedding

---

# DB 저장

```
{
"chunk_id":"SAM-08",

"concept":
"Box Prompt Encoding",

"file":
"prompt_encoder.py",

"class":
"PromptEncoder",

"function":
"_embed_boxes",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-09

# Mask Prompt Encoding

---

## ① 논문 위치

```
Section 3
Prompt Encoder

Page 5
```

---

## ② 논문 원문

> Dense prompts, such as masks, are embedded with a convolutional neural network.
> 

---

## ③ 논문 의미

Mask Prompt는 Point와 다르게 이미지 크기의 dense feature이다.

흐름:

```
Input Mask

↓

CNN Downsampling

↓

Dense Embedding

↓

Mask Decoder
```

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/prompt_encoder.py
```

Class:

```
PromptEncoder
```

Function:

```
_embed_masks()
```

---

# ⑤ 코드 원문

```
def _embed_masks(
    self,
    masks: torch.Tensor
) -> torch.Tensor:

    mask_embedding = self.mask_downscaling(
        masks
    )

    return mask_embedding
```

---

## mask_downscaling 구조

```
self.mask_downscaling = nn.Sequential(
    nn.Conv2d(
        1,
        mask_in_chans // 4,
        kernel_size=2,
        stride=2
    ),

    LayerNorm2d(
        mask_in_chans // 4
    ),

    activation(),

    nn.Conv2d(
        mask_in_chans // 4,
        mask_in_chans,
        kernel_size=2,
        stride=2
    )
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
Dense prompts are embedded
with CNN
```

↓

코드:

```
self.mask_downscaling()
```

↓

Mask feature embedding 생성

---

# DB 저장

```
{
"chunk_id":"SAM-09",

"concept":
"Mask Prompt Encoding",

"file":
"prompt_encoder.py",

"class":
"PromptEncoder",

"function":
"_embed_masks",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-10

# Positional Encoding

---

## ① 논문 위치

```
Section 3
Prompt Encoder

Page 5
```

---

## ② 논문 원문

> Sparse prompts are represented as positional encodings summed with learned embeddings.
> 

---

## ③ 논문 의미

SAM은 좌표 정보를 그대로 사용하지 않는다.

좌표:

```
(x,y)
```

↓

Fourier Feature Encoding

↓

Embedding Vector

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/prompt_encoder.py
```

Class:

```
PositionEmbeddingRandom
```

Function:

```
forward_with_coords()
```

---

# ⑤ 코드 원문

```
def forward_with_coords(
    self,
    coords,
    image_size
):

    coords = coords.clone()

    coords[:, :, 0] /= image_size[1]

    coords[:, :, 1] /= image_size[0]

    return self._pe_encoding(
        coords
    )
```

---

내부:

```
def _pe_encoding(
    self,
    coords
):

    coords = 2 * coords - 1

    coords = coords @ self.positional_encoding_gaussian_matrix

    coords = 2 * np.pi * coords

    return torch.cat(
        [
            torch.sin(coords),
            torch.cos(coords)
        ],
        dim=-1
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
positional encoding
```

↓

코드:

```
_pe_encoding()
```

↓

Fourier Feature 생성

---

# DB 저장

```
{
"chunk_id":"SAM-10",

"concept":
"Random Fourier Positional Encoding",

"file":
"prompt_encoder.py",

"class":
"PositionEmbeddingRandom",

"function":
"forward_with_coords",

"type":
"DIRECT"
}
```

# CHUNK SAM-11

# Mask Decoder Overview

---

## ① 논문 위치

```
Section 3. Segment Anything Model

Subsection:
Mask Decoder

Page 5
```

---

## ② 논문 원문

> The mask decoder efficiently maps the image embedding, prompt embeddings, and an output token to a mask.
> 

---

## ③ 논문 의미

Mask Decoder는 SAM에서 실제 segmentation mask를 생성하는 핵심 모듈이다.

입력:

```
Image Embedding
+
Prompt Embedding
+
Mask Token
```

↓

Transformer Decoder

↓

Mask Prediction

전체 구조:

```
Image Encoder
      |
      |
Image Embedding
      |
      |
      +----------------+
                       |
Prompt Encoder ----> Mask Decoder
                       |
                       |
                    Mask
```

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/modeling/mask_decoder.py
```

Class:

```
MaskDecoder
```

Function:

```
forward()
predict_masks()
```

---

# ⑤ 코드 원문

## Class

```
class MaskDecoder(nn.Module):

    def __init__(
        self,
        transformer_dim,
        transformer,
        num_multimask_outputs=3,
        activation=nn.GELU,
    ):
        super().__init__()

        self.transformer_dim = transformer_dim

        self.transformer = transformer

        self.num_multimask_outputs = (
            num_multimask_outputs
        )

        self.iou_token = nn.Embedding(
            1,
            transformer_dim
        )

        self.num_mask_tokens = (
            num_multimask_outputs + 1
        )

        self.mask_tokens = nn.Embedding(
            self.num_mask_tokens,
            transformer_dim
        )
```

---

## forward()

```
def forward(
    self,
    image_embeddings,
    image_pe,
    sparse_prompt_embeddings,
    dense_prompt_embeddings,
    multimask_output,
):

    masks, iou_pred = self.predict_masks(
        image_embeddings,
        image_pe,
        sparse_prompt_embeddings,
        dense_prompt_embeddings,
    )

    if multimask_output:

        mask_slice = slice(
            1,
            None
        )

    else:

        mask_slice = slice(
            0,
            1
        )

    masks = masks[:, mask_slice, :, :]

    iou_pred = iou_pred[:, mask_slice]

    return masks, iou_pred
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
Mask decoder maps:
image embedding
prompt embedding
output token

to mask
```

↓

코드:

```
self.predict_masks()
```

↓

실제 구현:

```
image_embeddings

+

sparse_prompt_embeddings

+

dense_prompt_embeddings

+

mask_tokens
```

---

# DB 저장

```
{
"chunk_id":"SAM-11",

"paper_section":
"Mask Decoder",

"concept":
"Mask Decoder Overview",

"file":
"mask_decoder.py",

"class":
"MaskDecoder",

"function":
"forward",

"type":
"DIRECT"
}
```

---

---

# CHUNK SAM-12

# Mask Decoder Prediction Pipeline

---

## ① 논문 위치

```
Section 3
Mask Decoder

Page 5
```

---

## ② 논문 원문

> The decoder predicts multiple masks for a single prompt, allowing the model to handle ambiguity.
> 

---

## ③ 논문 의미

SAM은 하나의 Prompt에 대해 여러 Mask를 출력한다.

이유:

Prompt가 모호할 수 있기 때문.

예:

점 하나:

```
       ●
```

가능한 객체:

```
사람 전체

사람 얼굴

배경 영역
```

따라서:

```
Prompt

↓

Multiple Masks

↓

IoU Score 선택
```

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/mask_decoder.py
```

Function:

```
predict_masks()
```

---

# ⑤ 코드 원문

```
def predict_masks(
    self,
    image_embeddings,
    image_pe,
    sparse_prompt_embeddings,
    dense_prompt_embeddings,
):

    output_tokens = torch.cat(
        [
            self.iou_token.weight,
            self.mask_tokens.weight,
        ],
        dim=0,
    )

    output_tokens = (
        output_tokens.unsqueeze(0)
        .expand(
            sparse_prompt_embeddings.size(0),
            -1,
            -1,
        )
    )

    tokens = torch.cat(
        (
            output_tokens,
            sparse_prompt_embeddings,
        ),
        dim=1,
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
output token
```

↓

코드:

```
self.mask_tokens
self.iou_token
```

---

논문:

```
multiple masks
```

↓

코드:

```
num_mask_tokens
```

---

# DB

```
{
"chunk_id":"SAM-12",

"concept":
"Multiple Mask Prediction",

"file":
"mask_decoder.py",

"function":
"predict_masks",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-13

# Two-Way Transformer

---

## ① 논문 위치

```
Section 3
Mask Decoder

Page 5~6
```

---

## ② 논문 원문

> The decoder uses a two-way transformer that updates both the image embedding and the prompt tokens.
> 

---

## ③ 논문 의미

일반 Transformer:

```
Query
 ↓
Key / Value
```

SAM:

두 방향으로 정보를 교환한다.

```
Prompt Tokens
       ↕
Image Embedding
```

그래서 이름:

```
Two-Way Transformer
```

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/transformer.py
```

Class:

```
TwoWayTransformer
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
class TwoWayTransformer(nn.Module):

    def forward(
        self,
        image_embedding,
        image_pe,
        point_embedding,
    ):

        bs, c, h, w = image_embedding.shape

        image_embedding = (
            image_embedding.flatten(2)
            .permute(0,2,1)
        )

        image_pe = (
            image_pe.flatten(2)
            .permute(0,2,1)
        )

        queries = point_embedding

        keys = image_embedding

        for layer in self.layers:

            queries, keys = layer(
                queries,
                keys,
                query_pe,
                key_pe,
            )

        return queries, keys
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
updates image embedding
and prompt tokens
```

↓

코드:

```
queries, keys = layer(...)
```

---

# DB

```
{
"chunk_id":"SAM-13",

"concept":
"Two-Way Transformer",

"file":
"transformer.py",

"class":
"TwoWayTransformer",

"function":
"forward",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-14

# Two-Way Attention Block

---

## ① 논문 위치

```
Section 3
Mask Decoder

Page 6
```

---

## ② 논문 원문

> The transformer block consists of self-attention and cross-attention layers.
> 

---

## ③ 논문 의미

Two-Way Transformer 내부는:

1. Token Self Attention
2. Token → Image Cross Attention
3. Image → Token Cross Attention

으로 구성된다.

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/transformer.py
```

Class:

```
TwoWayAttentionBlock
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
def forward(
    self,
    queries,
    keys,
    query_pe,
    key_pe,
):

    q = queries + query_pe

    attn_out = self.self_attn(
        q=q,
        k=q,
        v=queries,
    )

    queries = queries + attn_out

    queries = self.norm1(
        queries
    )

    queries = queries + self.cross_attn_token_to_image(
        q=queries + query_pe,
        k=keys + key_pe,
        v=keys,
    )

    queries = self.norm2(
        queries
    )

    keys = keys + self.cross_attn_image_to_token(
        q=keys + key_pe,
        k=queries + query_pe,
        v=queries,
    )

    keys = self.norm3(keys)

    return queries, keys
```

---

# ⑥ Code Match

```
DIRECT
```

---

# DB

```
{
"chunk_id":"SAM-14",

"concept":
"Two Way Attention Block",

"file":
"transformer.py",

"class":
"TwoWayAttentionBlock",

"function":
"forward",

"type":
"DIRECT"
}
```

# CHUNK SAM-15

# Mask Token Hypernetwork (Mask Generation)

---

## ① 논문 위치

```
Section 3. Segment Anything Model

Subsection:
Mask Decoder

Page 6
```

---

## ② 논문 원문

> After the transformer, the mask tokens are passed through a small MLP and then used to generate the final masks.
> 

---

## ③ 논문 의미

SAM은 Transformer 출력 token을 바로 mask로 사용하지 않는다.

과정:

```
Mask Token

↓

MLP Hypernetwork

↓

Mask Embedding Vector

↓

Image Embedding과 내적

↓

Segmentation Mask
```

구조:

```
Transformer Output

        |
        |
 Mask Tokens

        |
        |
 Hypernetwork MLP

        |
        |
Mask Prediction
```

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/modeling/mask_decoder.py
```

Class:

```
MaskDecoder
```

Function:

```
predict_masks()
```

---

# ⑤ 코드 원문

```
hyper_in_list = []

for i in range(self.num_mask_tokens):

    hyper_in_list.append(
        self.output_hypernetworks_mlps[i](
            mask_tokens_out[:, i, :]
        )
    )

hyper_in = torch.stack(
    hyper_in_list,
    dim=1
)
```

---

## Mask 생성 부분

```
b, c, h, w = upscaled_embedding.shape

masks = (
    hyper_in @ upscaled_embedding.view(
        b,
        c,
        h * w
    )
)

masks = masks.view(
    b,
    -1,
    h,
    w
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
mask tokens are passed through MLP
and generate masks
```

↓

코드:

```
self.output_hypernetworks_mlps
```

↓

Mask Token을 MLP 변환

논문:

```
generate final masks
```

↓

코드:

```
hyper_in @ upscaled_embedding
```

↓

Mask Logit 생성

---

# DB 저장

```
{
"chunk_id":"SAM-15",

"paper_section":
"Mask Decoder",

"concept":
"Mask Token Hypernetwork",

"file":
"mask_decoder.py",

"class":
"MaskDecoder",

"function":
"predict_masks",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-16

# IoU Prediction Head

---

## ① 논문 위치

```
Section 3
Mask Decoder

Page 6
```

---

## ② 논문 원문

> The decoder also predicts a confidence score for each mask.
> 

---

## ③ 논문 의미

SAM은 Mask만 출력하지 않는다.

각 Mask가 얼마나 좋은지 판단하는:

```
IoU Prediction Score
```

를 함께 출력한다.

흐름:

```
Mask 1
 |
IoU Score 0.92

Mask 2
 |
IoU Score 0.71

Mask 3
 |
IoU Score 0.55
```

가장 높은 Mask 선택 가능.

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/mask_decoder.py
```

Class:

```
MaskDecoder
```

Function:

```
predict_masks()
```

---

# ⑤ 코드 원문

```
iou_pred = self.iou_prediction_head(
    iou_token_out
)
```

---

IoU Head:

```
self.iou_prediction_head = MLP(
    transformer_dim,
    iou_head_hidden_dim,
    self.num_mask_tokens,
    iou_head_depth,
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
predicts confidence score
for each mask
```

↓

코드:

```
iou_prediction_head()
```

↓

출력:

```
iou_pred
```

---

# DB 저장

```
{
"chunk_id":"SAM-16",

"concept":
"IoU Prediction Head",

"file":
"mask_decoder.py",

"class":
"MaskDecoder",

"function":
"predict_masks",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-17

# Full SAM Forward Pipeline

---

## ① 논문 위치

```
Section 3
Segment Anything Model

Page 5~6
```

---

## ② 논문 원문

> The image encoder, prompt encoder, and mask decoder are combined to form the Segment Anything Model.
> 

---

## ③ 논문 의미

앞에서 분리했던 세 모듈을 실제 하나의 모델로 연결하는 부분.

전체 흐름:

```
                Image

                  |
                  v

          Image Encoder(ViT)

                  |
                  v

          Image Embedding

Prompt
  |
  v

Prompt Encoder

  |
  v

Prompt Embedding

Image Embedding
+
Prompt Embedding

        |
        v

    Mask Decoder

        |
        v

 Masks + IoU Score
```

---

# ④ Git 코드 위치

File:

```
segment_anything/modeling/sam.py
```

Class:

```
Sam
```

Function:

```
forward()
```

---

# ⑤ 코드 원문

```
image_embeddings = self.image_encoder(
    input_images
)
```

---

Prompt Encoding:

```
sparse_embeddings, dense_embeddings = (
    self.prompt_encoder(
        points=image_record.get("point_coords"),
        boxes=image_record.get("boxes"),
        masks=image_record.get("mask_inputs"),
    )
)
```

---

Mask Decoder:

```
low_res_masks, iou_predictions = (
    self.mask_decoder(
        image_embeddings=curr_embedding,
        image_pe=self.prompt_encoder.get_dense_pe(),
        sparse_prompt_embeddings=sparse_embeddings,
        dense_prompt_embeddings=dense_embeddings,
        multimask_output=multimask_output,
    )
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
three components combined
```

↓

코드:

```
self.image_encoder

self.prompt_encoder

self.mask_decoder
```

---

# DB 저장

```
{
"chunk_id":"SAM-17",

"concept":
"Full SAM Forward Pipeline",

"file":
"sam.py",

"class":
"Sam",

"function":
"forward",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-18

# SAM Predictor API

---

## ① 논문 위치

```
Section 3
Model Usage

Page 6
```

---

## ② 논문 원문

> The image encoder can be run once and the resulting embedding can be reused for multiple prompts.
> 

---

## ③ 논문 의미

실제 서비스 사용을 위한 최적화 부분.

일반 방식:

```
Image
 ↓
Encoder
 ↓
Prompt
 ↓
Mask
```

반복

하지만 SAM:

```
Image
 ↓
Encoder
 ↓
Cache Embedding

Prompt 1 → Mask

Prompt 2 → Mask

Prompt 3 → Mask
```

---

# ④ Git 코드 위치

File:

```
segment_anything/predictor.py
```

Class:

```
SamPredictor
```

Function:

```
set_image()
predict()
```

---

# ⑤ 코드 원문

## set_image()

```
def set_image(self, image):

    input_image = self.transform.apply_image(
        image
    )

    input_image = torch.as_tensor(
        input_image
    )

    self.set_torch_image(
        input_image,
        image.shape[:2]
    )
```

---

## predict()

```
def predict(
    self,
    point_coords=None,
    point_labels=None,
    box=None,
    mask_input=None,
):

    masks, scores, logits = self.predict_torch(
        coords,
        labels,
        box,
        mask_input
    )

    return masks, scores, logits
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
image embedding reused
```

↓

코드:

```
self.features
```

저장 후 재사용.

논문:

```
multiple prompts
```

↓

코드:

```
predict()
```

---

# DB 저장

```
{
"chunk_id":"SAM-18",

"concept":
"Predictor API and Embedding Cache",

"file":
"predictor.py",

"class":
"SamPredictor",

"function":
[
"set_image",
"predict"
],

"type":
"DIRECT"
}
```

# CHUNK SAM-19

# Automatic Mask Generator

---

## ① 논문 위치

```
Section 4. Segment Anything Data Engine

Page 7
```

---

## ② 논문 원문

> We develop an automatic annotation pipeline that uses SAM to generate masks automatically.
> 

---

## ③ 논문 의미

SAM은 사용자가 Point/Box Prompt를 직접 주지 않아도 전체 객체를 자동으로 찾을 수 있다.

이를 위해:

```
Automatic Mask Generator
```

를 제공한다.

전체 흐름:

```
Image

↓

Generate Grid Points

↓

SAM Prediction

↓

Mask Filtering

↓

Final Object Masks
```

---

# ④ Git 코드 위치

Repository:

```
facebookresearch/segment-anything
```

File:

```
segment_anything/automatic_mask_generator.py
```

Class:

```
SamAutomaticMaskGenerator
```

Function:

```
generate()
```

---

# ⑤ 코드 원문

```
class SamAutomaticMaskGenerator:

    def generate(
        self,
        image: np.ndarray,
    ) -> List[Dict[str, Any]]:

        mask_data = self._generate_masks(
            image
        )

        mask_data = self._postprocess_small_regions(
            mask_data
        )

        masks = []

        for idx in range(len(mask_data["segmentations"])):

            masks.append(
                {
                    "segmentation":
                    mask_data["segmentations"][idx],

                    "area":
                    mask_data["areas"][idx],

                    "bbox":
                    mask_data["boxes"][idx],

                    "predicted_iou":
                    mask_data["iou_preds"][idx],

                    "stability_score":
                    mask_data["stability_score"][idx],
                }
            )

        return masks
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드 매칭

논문:

```
automatic annotation pipeline
```

↓

코드:

```
SamAutomaticMaskGenerator.generate()
```

↓

자동 Mask 생성 전체 Pipeline

---

# DB 저장

```
{
"chunk_id":"SAM-19",

"concept":
"Automatic Mask Generation",

"file":
"automatic_mask_generator.py",

"class":
"SamAutomaticMaskGenerator",

"function":
"generate",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-20

# Point Grid Sampling

---

## ① 논문 위치

```
Section 4
Automatic Annotation

Page 7
```

---

## ② 논문 원문

> We automatically generate masks by sampling points over the image.
> 

---

## ③ 논문 의미

Automatic Mode에서는 사람이 Prompt를 주지 않는다.

대신:

```
Image 전체 영역

↓

Grid Point 생성

↓

각 Point를 Prompt로 사용
```

한다.

예:

```
+---+---+---+
| ● | ● | ● |
+---+---+---+
| ● | ● | ● |
+---+---+---+
| ● | ● | ● |
+---+---+---+
```

---

# ④ Git 코드 위치

File:

```
segment_anything/utils/amg.py
```

Function:

```
build_all_layer_point_grids()
```

---

# ⑤ 코드 원문

```
def build_all_layer_point_grids(
    n_per_side,
    n_layers,
    scale_per_layer,
):

    points_by_layer = []

    for i in range(n_layers + 1):

        n_points = int(
            n_per_side /
            (scale_per_layer ** i)
        )

        points_by_layer.append(
            build_point_grid(
                n_points
            )
        )

    return points_by_layer
```

---

Point 생성:

```
def build_point_grid(
    n_per_side
):

    offset = 1 / (
        2 * n_per_side
    )

    points = np.linspace(
        offset,
        1-offset,
        n_per_side
    )

    return np.stack(
        np.meshgrid(
            points,
            points
        ),
        axis=-1
    ).reshape(
        -1,
        2
    )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
sampling points over image
```

↓

코드:

```
build_point_grid()
```

↓

Prompt 후보 생성

---

# DB 저장

```
{
"chunk_id":"SAM-20",

"concept":
"Automatic Point Sampling",

"file":
"utils/amg.py",

"function":
"build_all_layer_point_grids",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-21

# Crop Strategy

---

## ① 논문 위치

```
Section 4
Automatic Mask Generation

Page 7
```

---

## ② 논문 원문

> We use a crop-based strategy to improve the segmentation of small objects.
> 

---

## ③ 논문 의미

큰 이미지에서는 작은 객체가 잘 안 잡힐 수 있다.

그래서:

```
Original Image

↓

Multiple Crops

↓

각 Crop에서 SAM 실행

↓

Merge
```

한다.

---

# ④ Git 코드 위치

File:

```
automatic_mask_generator.py
```

Function:

```
_generate_masks()
```

---

# ⑤ 코드 원문

```
def _generate_masks(
    self,
    image
):

    orig_size = image.shape[:2]

    crop_boxes, layer_idxs = (
        generate_crop_boxes(
            orig_size,
            self.crop_n_layers,
            self.crop_overlap_ratio,
        )
    )

    for crop_box, layer_idx in zip(
        crop_boxes,
        layer_idxs
    ):

        crop_data = self._process_crop(
            image,
            crop_box,
            layer_idx,
        )
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
crop-based strategy
```

↓

코드:

```
generate_crop_boxes()
```

↓

Crop 영역 생성

---

# DB 저장

```
{
"chunk_id":"SAM-21",

"concept":
"Multi Crop Processing",

"file":
"automatic_mask_generator.py",

"function":
"_generate_masks",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-22

# Mask Filtering

---

## ① 논문 위치

```
Section 4
Automatic Mask Generation

Page 7
```

---

## ② 논문 원문

> We filter masks using predicted IoU and stability scores.
> 

---

## ③ 논문 의미

SAM은 많은 후보 Mask를 생성한다.

하지만 모든 Mask가 좋은 것은 아니다.

따라서:

```
Candidate Masks

↓

Quality Filtering

↓

Final Masks
```

과정 수행.

---

# ④ Git 코드 위치

File:

```
automatic_mask_generator.py
```

---

관련 함수:

```
calculate_stability_score()
```

---

# ⑤ 코드 원문

```
def calculate_stability_score(
    masks,
    mask_threshold,
    threshold_offset,
):

    intersections = (
        calculate_stability_score(
            masks > (
                mask_threshold +
                threshold_offset
            ),

            masks > (
                mask_threshold -
                threshold_offset
            )
        )
    )

    return intersections
```

---

IoU Filtering:

```
if predicted_iou[
    i
] < self.pred_iou_thresh:

    continue
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
predicted IoU
stability score
```

↓

코드:

```
pred_iou_thresh

calculate_stability_score()
```

---

# DB 저장

```
{
"chunk_id":"SAM-22",

"concept":
"Mask Quality Filtering",

"file":
"automatic_mask_generator.py",

"function":
"calculate_stability_score",

"type":
"DIRECT"
}
```

---

# CHUNK SAM-23

# Non-Maximum Suppression(NMS)

---

## ① 논문 위치

```
Section 4
Automatic Mask Generation
```

---

## ② 논문 원문

> We remove duplicate masks using non-maximum suppression.
> 

---

## ③ 논문 의미

같은 객체에 대해 여러 Mask가 생성된다.

예:

```
Mask A
████

Mask B
 ████
```

겹치는 Mask 제거.

---

# ④ Git 코드 위치

File:

```
automatic_mask_generator.py
```

Import:

```
torchvision.ops.batched_nms
```

---

# ⑤ 코드 원문

```
keep = batched_nms(
    boxes,
    scores,
    categories,
    iou_threshold
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
remove duplicate masks
```

↓

코드:

```
batched_nms()
```

---

# DB 저장

```
{
"chunk_id":"SAM-23",

"concept":
"Mask NMS",

"file":
"automatic_mask_generator.py",

"function":
"batched_nms",

"type":
"DIRECT"
}
```

# CHUNK SAM-24

# Training Strategy (학습 전략)

---

## ① 논문 위치

```
Section 3
Segment Anything Model

Page 6
```

---

## ② 논문 원문

> We train SAM on a large-scale dataset of images and masks. The model is trained with a combination of image encoder, prompt encoder, and mask decoder.
> 

---

## ③ 논문 의미

SAM 학습은 세 모듈을 동시에 최적화한다.

학습 대상:

```
Image Encoder
        |
        |
Prompt Encoder
        |
        |
Mask Decoder
```

전체 End-to-End 학습.

입력:

```
Image

+

Prompt

+

Ground Truth Mask
```

출력:

```
Predicted Mask
```

비교:

```
Prediction

vs

Ground Truth
```

Loss 계산.

---

# ④ Git 코드 위치

공식 Git:

```
facebookresearch/segment-anything
```

주의:

SAM 공식 Git에는 학습 코드는 포함되어 있지 않다.

논문 학습 코드는 공개되지 않았고,

Inference 코드만 제공된다.

따라서 해당 부분은:

```
예상코드
```

이다.

---

# ⑤ 코드 원문

## (예상코드)

```
def train_step(
    image,
    prompt,
    gt_mask
):

    # Image Encoder
    image_embedding = image_encoder(
        image
    )

    # Prompt Encoder
    sparse_embedding, dense_embedding = (
        prompt_encoder(prompt)
    )

    # Mask Decoder
    pred_mask = mask_decoder(
        image_embedding,
        sparse_embedding,
        dense_embedding
    )

    # Loss
    loss = criterion(
        pred_mask,
        gt_mask
    )

    optimizer.zero_grad()

    loss.backward()

    optimizer.step()

    return loss
```

---

# ⑥ Code Match

```
예상코드
```

---

# ⑦ 논문 ↔ 코드 매핑

논문:

```
image encoder,
prompt encoder,
mask decoder
trained together
```

↓

예상 코드:

```
image_encoder()

prompt_encoder()

mask_decoder()
```

↓

End-to-End Training Pipeline

---

# DB 저장

```
{
"chunk_id":"SAM-24",

"concept":
"End-to-End Training Strategy",

"file":
"training_loop.py",

"type":
"예상코드"
}
```

---

---

# CHUNK SAM-25

# Loss Function

---

## ① 논문 위치

```
Section 3
Segment Anything Model

Page 6
```

---

## ② 논문 원문

> We use a combination of focal loss and dice loss for mask prediction.
> 

---

## ③ 논문 의미

SAM은 Mask Segmentation 문제이기 때문에:

단순 Binary Cross Entropy만 사용하지 않는다.

사용 Loss:

```
Total Loss

=

Focal Loss

+

Dice Loss
```

---

## Focal Loss

역할:

잘 맞추는 pixel보다

틀리는 pixel에 더 집중.

---

## Dice Loss

역할:

Mask overlap 정도 평가.

IoU와 유사한 개념.

---

# ④ Git 코드 위치

공식 Git:

```
segment-anything
```

학습 loss 코드 없음.

따라서:

```
예상코드
```

---

# ⑤ 코드 원문

## (예상코드)

```
import torch.nn.functional as F

def sigmoid_focal_loss(
    inputs,
    targets,
    alpha=0.25,
    gamma=2
):

    prob = inputs.sigmoid()

    ce_loss = F.binary_cross_entropy_with_logits(
        inputs,
        targets,
        reduction="none"
    )

    p_t = (
        prob * targets
        +
        (1-prob)*(1-targets)
    )

    loss = ce_loss * (
        (1-p_t)**gamma
    )

    return loss.mean()
```

---

Dice Loss:

```
def dice_loss(
    inputs,
    targets
):

    inputs = inputs.sigmoid()

    numerator = (
        2 *
        (inputs * targets).sum()
    )

    denominator = (
        inputs.sum()
        +
        targets.sum()
    )

    loss = 1 - (
        numerator /
        denominator
    )

    return loss
```

---

Total:

```
loss = (
    focal_loss
    +
    dice_loss
)
```

---

# ⑥ Code Match

```
예상코드
```

---

# ⑦ 논문 ↔ 코드

논문:

```
focal loss + dice loss
```

↓

코드:

```
sigmoid_focal_loss()

dice_loss()
```

---

# DB

```
{
"chunk_id":"SAM-25",

"concept":
"Mask Training Loss",

"type":
"예상코드"
}
```

---

# CHUNK SAM-26

# SA-1B Dataset

---

## ① 논문 위치

```
Section 2
Dataset

Page 4
```

---

## ② 논문 원문

> We introduce SA-1B, a dataset containing 1 billion masks collected through our data engine.
> 

---

## ③ 논문 의미

SAM 학습의 핵심 데이터셋.

기존:

```
COCO

1M masks
```

↓

SAM:

```
SA-1B

1 billion masks
```

---

구성:

```
Images

11 million

Masks

1 billion
```

---

# ④ Git 코드 위치

공식 Git:

```
segment-anything
```

데이터셋 생성 코드는 없음.

따라서:

```
예상코드
```

---

# ⑤ 코드 원문

## (예상코드)

```
class SA1BDataset:

    def __init__(
        self,
        image_dir,
        mask_dir
    ):

        self.images = load_images(
            image_dir
        )

        self.masks = load_masks(
            mask_dir
        )

    def __getitem__(
        self,
        idx
    ):

        image = read_image(
            self.images[idx]
        )

        mask = read_mask(
            self.masks[idx]
        )

        return {
            "image":image,
            "mask":mask
        }
```

---

# ⑥ Code Match

```
예상코드
```

---

# DB

```
{
"chunk_id":"SAM-26",

"concept":
"SA-1B Dataset Loader",

"type":
"예상코드"
}
```

---

# CHUNK SAM-27

# Data Engine

---

## ① 논문 위치

```
Section 4
Data Engine

Page 7
```

---

## ② 논문 원문

> We develop a data engine with three stages: assisted-manual, semi-automatic, and fully automatic annotation.
> 

---

## ③ 논문 의미

SAM 데이터 생성 과정.

3단계:

---

### Stage 1

```
Assisted Manual
```

사람이 Prompt 입력

↓

SAM Mask 생성

---

### Stage 2

```
Semi Automatic
```

SAM이 Mask 후보 생성

사람 검수

---

### Stage 3

```
Fully Automatic
```

SAM 자체 생성

---

# ④ Git 코드 위치

Automatic Annotation 관련:

```
automatic_mask_generator.py
```

하지만 전체 Data Engine 없음.

---

# ⑤ 코드 원문

## (예상코드)

```
def data_engine_pipeline(image):

    # Stage 1
    manual_prompt = human_annotation()

    mask = sam.predict(
        manual_prompt
    )

    # Stage 2
    candidates = sam.generate(
        image
    )

    verified_masks = human_review(
        candidates
    )

    # Stage 3
    final_masks = sam.generate(
        image
    )

    return final_masks
```

---

# ⑥ Code Match

```
부분 DIRECT
+
예상코드
```

---

# DB

```
{
"chunk_id":"SAM-27",

"concept":
"Data Engine Pipeline",

"type":
"부분 DIRECT + 예상코드"
}
```

---

# CHUNK SAM-28

# Experiments

---

## ① 논문 위치

```
Section 5
Experiments

Page 9
```

---

## ② 논문 원문

> We evaluate SAM on several segmentation benchmarks and compare zero-shot performance.
> 

---

## ③ 논문 의미

SAM 성능 평가.

평가:

```
COCO

LVIS

ADE20K

etc.
```

---

# ④ Git 코드 위치

공식 Git:

평가 코드 없음.

---

# ⑤ 코드 원문

## (예상코드)

```
with torch.no_grad():

    masks, scores, logits = predictor.predict(
        point_coords,
        point_labels
    )

iou = calculate_iou(
    masks,
    ground_truth
)
```

---

# ⑥ Code Match

```
예상코드
```

---

# DB

```
{
"chunk_id":"SAM-28",

"concept":
"Evaluation Pipeline",

"type":
"예상코드"
}
```

---

# CHUNK SAM-29

# Zero-shot Transfer

---

## ① 논문 위치

```
Section 5
Experiments

Page 10
```

---

## ② 논문 원문

> SAM demonstrates strong zero-shot transfer performance on a variety of segmentation tasks.
> 

---

## ③ 논문 의미

SAM은 특정 데이터셋에만 학습되지 않고:

새로운 데이터

↓

Prompt

↓

Segmentation

가능.

---

# ④ Git 코드 위치

Inference API:

```
predictor.py
```

---

# ⑤ 코드 원문

```
predictor.set_image(
    image
)

masks, scores, logits = (
    predictor.predict(
        point_coords,
        point_labels
    )
)
```

---

# ⑥ Code Match

```
DIRECT
```

---

# ⑦ 논문 ↔ 코드

논문:

```
zero-shot transfer
```

↓

코드:

```
predict()
```

↓

새로운 이미지에 Prompt 기반 추론

---

# DB

```
{
"chunk_id":"SAM-29",

"concept":
"Zero Shot Prediction",

"file":
"predictor.py",

"type":
"DIRECT"
}
```