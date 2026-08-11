# ResNet

# ResNet 논문 ↔ 공식 Git 코드 전체 대응

- 논문: **Deep Residual Learning for Image Recognition**
- Git: `https://github.com/kaiminghe/deep-residual-networks`
- 논문 PDF: `1512.03385v1.pdf` 1512.03385v1.pdfPDF

이 저장소는 논문 저자인 Kaiming He의 공식 저장소가 맞습니다. 다만 저장소에는 **ResNet-50·101·152의 Caffe 배포용 네트워크 정의와 pretrained model 링크만 있고, 학습 코드·CIFAR 코드·ResNet-18/34 정의·Faster R-CNN 코드는 없습니다.** 저장소 파일은 `ResNet-50-deploy.prototxt`, `ResNet-101-deploy.prototxt`, `ResNet-152-deploy.prototxt`가 핵심입니다. [GitHub](https://github.com/kaiminghe/deep-residual-networks?utm_source=chatgpt.com)

따라서 아래에서는:

- 저장소에 실제로 있는 코드는 그대로 제시
- 없는 구현은 **(예상코드)**로 표시
- 실험 결과 자체는 필요할 경우 평가용 예상코드 제시
- 논문 페이지 순서대로 정리

합니다.

---

# 1페이지

## 1. 깊은 네트워크의 학습 난이도

### 논문 텍스트

> “Deeper neural networks are more difficult to train.”
> 

> “We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.”
> 

↓

### 대응 코드

공식 저장소에서 깊은 모델은 각각 별도의 Caffe 네트워크 정의로 제공됩니다.

```
name: "ResNet-50"
input: "data"
input_dim: 1
input_dim: 3
input_dim: 224
input_dim: 224
```

```
name: "ResNet-101"
input: "data"
input_dim: 1
input_dim: 3
input_dim: 224
input_dim: 224
```

```
name: "ResNet-152"
input: "data"
input_dim: 1
input_dim: 3
input_dim: 224
input_dim: 224
```

### 판정

`DIRECT-CONCEPTUAL`

50·101·152층 모델은 실제로 제공되지만, “더 쉽게 학습된다”는 것은 구조만으로 완전히 증명되는 것이 아니라 학습 실험 결과에 해당합니다. 공식 저장소에는 학습 로그와 solver가 포함되어 있지 않습니다. [GitHub](https://github.com/kaiminghe/deep-residual-networks?utm_source=chatgpt.com)

---

## 2. 일반 함수가 아닌 residual function 학습

### 논문 텍스트

> “We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions.”
> 

↓

### 대응 코드

다음은 ResNet-50 첫 residual block에서 residual branch와 shortcut branch를 더하는 실제 코드입니다.

```
layer {
    bottom: "pool1"
    top: "res2a_branch1"
    name: "res2a_branch1"
    type: "Convolution"
    convolution_param {
        num_output: 256
        kernel_size: 1
        pad: 0
        stride: 1
        bias_term: false
    }
}

layer {
    bottom: "res2a_branch1"
    top: "res2a_branch1"
    name: "bn2a_branch1"
    type: "BatchNorm"
    batch_norm_param {
        use_global_stats: true
    }
}

layer {
    bottom: "res2a_branch1"
    top: "res2a_branch1"
    name: "scale2a_branch1"
    type: "Scale"
    scale_param {
        bias_term: true
    }
}
```

Residual branch의 마지막 출력과 shortcut을 합칩니다.

```
layer {
    bottom: "res2a_branch1"
    bottom: "res2a_branch2c"
    top: "res2a"
    name: "res2a"
    type: "Eltwise"
}

layer {
    bottom: "res2a"
    top: "res2a"
    name: "res2a_relu"
    type: "ReLU"
}
```

### 판정

`DIRECT`

Caffe의 `Eltwise` 계층이 shortcut 출력과 residual branch 출력을 원소별로 더해 \(F(x)+x\) 또는 \(F(x)+W_sx\)를 만듭니다. [GitExtract](https://gitextract.com/KaimingHe/deep-residual-networks?utm_source=chatgpt.com)

---

## 3. ImageNet에서 최대 152층

### 논문 텍스트

> “On the ImageNet dataset we evaluate residual nets with a depth of up to 152 layers.”
> 

↓

### 대응 코드

공식 저장소에 다음 모델이 존재합니다.

```
ResNet-50-deploy.prototxt
ResNet-101-deploy.prototxt
ResNet-152-deploy.prototxt
```

ResNet-152의 깊이는 bottleneck block 반복 수로 구성됩니다.

```
conv2_x: 3 blocks
conv3_x: 8 blocks
conv4_x: 36 blocks
conv5_x: 3 blocks
```

계산:

```
초기 convolution 1개
+ (3 + 8 + 36 + 3) × 3 convolution
+ 마지막 fully connected 1개
= 1 + 150 + 1
= 152
```

### 판정

`DIRECT`

공식 저장소는 논문의 50·101·152층 원본 Caffe 모델을 제공합니다. [GitHub](https://github.com/kaiminghe/deep-residual-networks?utm_source=chatgpt.com)

---

## 4. ILSVRC·COCO 결과

### 논문 텍스트

> “An ensemble of these residual nets achieves 3.57% error on the ImageNet test set.”
> 

> “We obtain a 28% relative improvement on the COCO object detection dataset.”
> 

↓

### 대응 코드

공식 저장소에는 다음이 없습니다.

```
ensemble 실행 코드
ImageNet test server 제출 코드
COCO detection 학습 코드
COCO segmentation 코드
3.57% 결과 재현 스크립트
```

### (예상코드)

여러 모델의 class probability를 평균하는 ensemble 구현입니다.

```
from __future__ import annotations

import torch
from torch import nn

@torch.no_grad()
def ensemble_classification(
    models: list[nn.Module],
    images: torch.Tensor
) -> torch.Tensor:
    if not models:
        raise ValueError("모델이 하나 이상 필요합니다.")

    probabilities: list[torch.Tensor] = []

    for model in models:
        model.eval()
        logits = model(images)
        probabilities.append(
            torch.softmax(logits, dim=1)
        )

    return torch.stack(
        probabilities,
        dim=0
    ).mean(dim=0)
```

Top-5 error:

```
@torch.no_grad()
def top5_error(
    probabilities: torch.Tensor,
    targets: torch.Tensor
) -> float:
    top5 = probabilities.topk(
        k=5,
        dim=1
    ).indices

    correct = top5.eq(
        targets.unsqueeze(1)
    ).any(dim=1)

    return float(
        1.0 - correct.float().mean().item()
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 5. Figure 1 — 20층·56층 plain network 비교

### 논문 텍스트

> “The deeper network has higher training error, and thus test error.”
> 

↓

### 대응 코드

공식 저장소에는 CIFAR-10의 20층·56층 plain network 학습 코드가 없습니다.

### (예상코드)

Residual connection을 사용하지 않는 CIFAR plain block입니다.

```
from __future__ import annotations

import torch
from torch import nn

class PlainBlock(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: int = 1
    ):
        super().__init__()

        self.layers = nn.Sequential(
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                stride=stride,
                padding=1,
                bias=False
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                kernel_size=3,
                stride=1,
                padding=1,
                bias=False
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        return self.layers(x)
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 2페이지

## 6. Figure 2 — residual building block

### 논문 텍스트

Figure 2는 다음 흐름을 나타냅니다.

```
x
→ weight layer
→ ReLU
→ weight layer
→ F(x)
→ x와 element-wise addition
→ ReLU
```

↓

### 대응 코드

공식 저장소의 모델은 bottleneck block만 포함하므로 Figure 2의 정확한 두 계층 basic block은 없습니다.

공식 bottleneck의 residual branch:

```
layer {
    bottom: "pool1"
    top: "res2a_branch2a"
    name: "res2a_branch2a"
    type: "Convolution"
    convolution_param {
        num_output: 64
        kernel_size: 1
        pad: 0
        stride: 1
        bias_term: false
    }
}

layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "bn2a_branch2a"
    type: "BatchNorm"
    batch_norm_param {
        use_global_stats: true
    }
}

layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "scale2a_branch2a"
    type: "Scale"
    scale_param {
        bias_term: true
    }
}

layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "res2a_branch2a_relu"
    type: "ReLU"
}
```

두 번째 3×3 convolution:

```
layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2b"
    name: "res2a_branch2b"
    type: "Convolution"
    convolution_param {
        num_output: 64
        kernel_size: 3
        pad: 1
        stride: 1
        bias_term: false
    }
}
```

세 번째 1×1 convolution:

```
layer {
    bottom: "res2a_branch2b"
    top: "res2a_branch2c"
    name: "res2a_branch2c"
    type: "Convolution"
    convolution_param {
        num_output: 256
        kernel_size: 1
        pad: 0
        stride: 1
        bias_term: false
    }
}
```

Shortcut과 addition:

```
layer {
    bottom: "res2a_branch1"
    bottom: "res2a_branch2c"
    top: "res2a"
    name: "res2a"
    type: "Eltwise"
}

layer {
    bottom: "res2a"
    top: "res2a"
    name: "res2a_relu"
    type: "ReLU"
}
```

### 판정

`DIRECT`, 단 공식 저장소는 Figure 2의 2-layer basic block이 아니라 3-layer bottleneck block을 제공합니다.

---

## 7. \(F(x)=H(x)-x\), \(H(x)=F(x)+x\)

### 논문 텍스트

> “We explicitly let these layers fit a residual mapping.”
> 

> “The original mapping is recast into \(F(x)+x\).”
> 

↓

### 대응 코드

Identity shortcut을 사용하는 block:

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

여기서:

```
res2a            = x
res2b_branch2c   = F(x)
res2b            = x + F(x)
```

### 판정

`DIRECT`

Projection 계층 없이 이전 block 출력이 `Eltwise`의 입력으로 직접 들어갑니다.

---

## 8. Identity shortcut은 추가 parameter와 연산이 거의 없음

### 논문 텍스트

> “Identity shortcut connections add neither extra parameter nor computational complexity.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

`res2a`에 convolution이나 weight 계층을 적용하지 않고 바로 합산하므로 shortcut 자체에는 학습 parameter가 없습니다.

---

## 9. SGD와 backpropagation으로 end-to-end 학습

### 논문 텍스트

> “The entire network can still be trained end-to-end by SGD with backpropagation.”
> 

↓

### 대응 코드

공식 저장소에는 deploy prototxt만 있으므로 solver와 train prototxt가 없습니다.

### (예상코드)

Caffe solver 설정:

```
net: "ResNet-50-train.prototxt"

test_iter: 50000
test_interval: 10000

base_lr: 0.1
lr_policy: "step"
gamma: 0.1
stepsize: 150000

momentum: 0.9
weight_decay: 0.0001

display: 100
max_iter: 600000

snapshot: 10000
snapshot_prefix: "models/resnet50"

solver_mode: GPU
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 10. Highway network와의 차이

### 논문 텍스트

논문은 highway network의 shortcut에는 gate parameter가 있지만 ResNet의 identity shortcut은 항상 열려 있고 parameter가 없다고 설명합니다.

↓

### 대응 코드

ResNet shortcut:

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

Gate에 해당하는 sigmoid나 multiplication 계층은 존재하지 않습니다.

### 판정

`DIRECT-CONCEPTUAL`

---

# 3페이지

## 11. Equation (1)

### 논문 텍스트

\[
y=F(x,\{W_i\})+x
\]

↓

### 대응 코드

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

Caffe `Eltwise`의 기본 operation은 합산이며 두 bottom blob을 원소별로 더합니다.

---

## 12. 두 계층 residual function

### 논문 텍스트

\[
F=W_2\sigma(W_1x)
\]

↓

### 대응 코드

공식 저장소에는 2-layer basic block이 없습니다.

### (예상코드)

```
class BasicResidualBlock(nn.Module):
    expansion = 1

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: int = 1
    ):
        super().__init__()

        self.conv1 = nn.Conv2d(
            in_channels,
            out_channels,
            kernel_size=3,
            stride=stride,
            padding=1,
            bias=False
        )
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

        self.conv2 = nn.Conv2d(
            out_channels,
            out_channels,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False
        )
        self.bn2 = nn.BatchNorm2d(out_channels)

        if (
            stride != 1
            or in_channels != out_channels
        ):
            self.shortcut = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=stride,
                    bias=False
                ),
                nn.BatchNorm2d(out_channels)
            )
        else:
            self.shortcut = nn.Identity()

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        identity = self.shortcut(x)

        residual = self.conv1(x)
        residual = self.bn1(residual)
        residual = self.relu(residual)

        residual = self.conv2(residual)
        residual = self.bn2(residual)

        output = residual + identity
        output = self.relu(output)

        return output
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 13. Addition 뒤 두 번째 ReLU

### 논문 텍스트

> “We adopt the second nonlinearity after the addition.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2a_branch1"
    bottom: "res2a_branch2c"
    top: "res2a"
    name: "res2a"
    type: "Eltwise"
}

layer {
    bottom: "res2a"
    top: "res2a"
    name: "res2a_relu"
    type: "ReLU"
}
```

### 판정

`DIRECT`

`Eltwise` 다음에 `ReLU`가 배치된 original post-activation ResNet 구조입니다.

---

## 14. Equation (2) — projection shortcut

### 논문 텍스트

\[
y=F(x,\{W_i\})+W_sx
\]

↓

### 대응 코드

차원이 바뀌는 `res3a` block의 shortcut입니다.

```
layer {
    bottom: "res2c"
    top: "res3a_branch1"
    name: "res3a_branch1"
    type: "Convolution"
    convolution_param {
        num_output: 512
        kernel_size: 1
        pad: 0
        stride: 2
        bias_term: false
    }
}

layer {
    bottom: "res3a_branch1"
    top: "res3a_branch1"
    name: "bn3a_branch1"
    type: "BatchNorm"
    batch_norm_param {
        use_global_stats: true
    }
}

layer {
    bottom: "res3a_branch1"
    top: "res3a_branch1"
    name: "scale3a_branch1"
    type: "Scale"
    scale_param {
        bias_term: true
    }
}
```

Projection 결과와 residual branch 합산:

```
layer {
    bottom: "res3a_branch1"
    bottom: "res3a_branch2c"
    top: "res3a"
    name: "res3a"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

`1×1 convolution`, `stride=2`로 공간 크기와 채널 수를 동시에 맞춥니다.

---

## 15. F는 2층 또는 3층일 수 있음

### 논문 텍스트

> “Experiments in this paper involve a function F that has two or three layers.”
> 

↓

### 대응 코드

공식 저장소는 3-layer bottleneck만 제공합니다.

```
1×1 convolution
3×3 convolution
1×1 convolution
```

실제 예:

```
name: "res2a_branch2a"
kernel_size: 1
num_output: 64
```

```
name: "res2a_branch2b"
kernel_size: 3
num_output: 64
```

```
name: "res2a_branch2c"
kernel_size: 1
num_output: 256
```

### 판정

`PARTIAL`

3-layer 구현은 직접 존재하지만 2-layer ResNet-18/34는 저장소에 없습니다.

## 16. 채널별 feature-map addition

### 논문 텍스트

> “The element-wise addition is performed on two feature maps, channel by channel.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

두 bottom tensor의 shape가 동일한 상태에서 채널·공간 위치별 합산이 수행됩니다.

---

## 17. Plain network 설계 규칙

### 논문 텍스트

- 같은 output feature-map 크기에서는 같은 filter 수 사용
- feature-map 크기가 절반이면 filter 수를 두 배로 증가
- downsampling은 stride 2 convolution 사용

↓

### 대응 코드

공식 저장소에는 plain network가 없습니다.

### (예상코드)

```
class PlainImageNetNetwork(nn.Module):
    def __init__(self):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(
                3, 64,
                kernel_size=7,
                stride=2,
                padding=3,
                bias=False
            ),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(
                kernel_size=3,
                stride=2,
                padding=1
            ),

            PlainBlock(64, 64),
            PlainBlock(64, 64),
            PlainBlock(64, 64),

            PlainBlock(64, 128, stride=2),
            PlainBlock(128, 128),
            PlainBlock(128, 128),
            PlainBlock(128, 128),

            PlainBlock(128, 256, stride=2),
            PlainBlock(256, 256),
            PlainBlock(256, 256),
            PlainBlock(256, 256),
            PlainBlock(256, 256),
            PlainBlock(256, 256),

            PlainBlock(256, 512, stride=2),
            PlainBlock(512, 512),
            PlainBlock(512, 512)
        )

        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Linear(512, 1000)

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 18. Global average pooling과 1000-way FC

### 논문 텍스트

> “The network ends with a global average pooling layer and a 1000-way fully-connected layer with softmax.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res5c"
    top: "pool5"
    name: "pool5"
    type: "Pooling"
    pooling_param {
        kernel_size: 7
        stride: 1
        pool: AVE
    }
}
```

```
layer {
    bottom: "pool5"
    top: "fc1000"
    name: "fc1000"
    type: "InnerProduct"
    inner_product_param {
        num_output: 1000
    }
}
```

```
layer {
    bottom: "fc1000"
    top: "prob"
    name: "prob"
    type: "Softmax"
}
```

### 판정

`DIRECT`

---

# 4페이지

## 19. Figure 3 — 첫 7×7 convolution, stride 2

### 논문 텍스트

> “7×7 conv, 64, /2”
> 

↓

### 대응 코드

```
layer {
    bottom: "data"
    top: "conv1"
    name: "conv1"
    type: "Convolution"
    convolution_param {
        num_output: 64
        kernel_size: 7
        pad: 3
        stride: 2
    }
}
```

### 판정

`DIRECT`

---

## 20. Max pooling stride 2

### 논문 텍스트

> “pool, /2”
> 

↓

### 대응 코드

```
layer {
    bottom: "conv1"
    top: "pool1"
    name: "pool1"
    type: "Pooling"
    pooling_param {
        kernel_size: 3
        stride: 2
        pool: MAX
    }
}
```

### 판정

`DIRECT`

논문 Table 1에서 명시한 `3×3 max pool, stride 2`와 일치합니다.

---

## 21. 동일 차원의 identity shortcut

### 논문 텍스트

> “The identity shortcuts can be directly used when the input and output are of the same dimensions.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2a"
    bottom: "res2b_branch2c"
    top: "res2b"
    name: "res2b"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

`res2a`가 별도 변환 없이 바로 addition에 입력됩니다.

---

## 22. Option A — zero-padding shortcut

### 논문 텍스트

> “The shortcut still performs identity mapping, with extra zero entries padded for increasing dimensions.”
> 

↓

### 대응 코드

공식 저장소의 50·101·152 모델은 option B projection을 사용하므로 option A zero-padding shortcut은 없습니다.

### (예상코드)

```
class OptionAShortcut(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: int
    ):
        super().__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.stride = stride

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        if self.stride > 1:
            x = x[
                :,
                :,
                ::self.stride,
                ::self.stride
            ]

        channel_difference = (
            self.out_channels
            - self.in_channels
        )

        if channel_difference < 0:
            raise ValueError(
                "출력 채널이 입력보다 작습니다."
            )

        front = channel_difference // 2
        back = channel_difference - front

        return torch.nn.functional.pad(
            x,
            pad=(0, 0, 0, 0, front, back),
            mode="constant",
            value=0
        )
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 23. Option B — dimension 증가 시에만 projection

### 논문 텍스트

> “The projection shortcut is used to match dimensions, done by 1×1 convolutions.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2c"
    top: "res3a_branch1"
    name: "res3a_branch1"
    type: "Convolution"
    convolution_param {
        num_output: 512
        kernel_size: 1
        pad: 0
        stride: 2
        bias_term: false
    }
}
```

차원이 동일한 다음 block에서는 projection이 없습니다.

```
layer {
    bottom: "res3a"
    bottom: "res3b_branch2c"
    top: "res3b"
    name: "res3b"
    type: "Eltwise"
}
```

### 판정

`DIRECT`

공식 50·101·152 모델은 논문에서 선택한 option B 구조입니다.

---

## 24. Batch normalization은 convolution 직후, activation 이전

### 논문 텍스트

> “We adopt batch normalization right after each convolution and before activation.”
> 

↓

### 대응 코드

```
layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "bn2a_branch2a"
    type: "BatchNorm"
    batch_norm_param {
        use_global_stats: true
    }
}

layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "scale2a_branch2a"
    type: "Scale"
    scale_param {
        bias_term: true
    }
}

layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2a"
    name: "res2a_branch2a_relu"
    type: "ReLU"
}
```

### 판정

`DIRECT`

순서가 `Convolution → BatchNorm → Scale → ReLU`입니다.

---

## 25. ImageNet scale augmentation `[256,480]`

### 논문 텍스트

> “The image is resized with its shorter side randomly sampled in [256, 480].”
> 

↓

### 대응 코드

공식 저장소에는 데이터 전처리와 학습 코드가 없습니다.

### (예상코드)

```
import random

from PIL import Image

def random_short_side_resize(
    image: Image.Image,
    minimum: int = 256,
    maximum: int = 480
) -> Image.Image:
    target_short_side = random.randint(
        minimum,
        maximum
    )

    width, height = image.size
    short_side = min(width, height)

    scale = target_short_side / short_side

    resized_width = round(width * scale)
    resized_height = round(height * scale)

    return image.resize(
        (resized_width, resized_height),
        Image.BILINEAR
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 26. 224×224 random crop·horizontal flip·mean subtraction

### 논문 텍스트

> “A 224×224 crop is randomly sampled from an image or its horizontal flip, with the per-pixel mean subtracted.”
> 

↓

### 대응 코드

### (예상코드)

```
from torchvision import transforms

imagenet_train_transform = transforms.Compose(
    [
        transforms.Lambda(
            random_short_side_resize
        ),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[1.0, 1.0, 1.0]
        )
    ]
)
```

논문은 “per-pixel mean”을 사용했다고 적기 때문에 채널 평균을 사용하는 위 코드는 현대적 근사 구현입니다. 논문 방식에 더 가깝게 하려면 ImageNet 학습셋의 위치별 평균 이미지를 계산해 빼야 합니다.

### 판정

`MISSING-BUT-PROVIDED-PARTIAL`

---

## 27. He initialization

### 논문 텍스트

> “We initialize the weights as in [13].”
> 

↓

### 대응 코드

Deploy prototxt에는 training weight filler가 없습니다.

### (예상코드)

```
def initialize_resnet(
    module: nn.Module
) -> None:
    if isinstance(module, nn.Conv2d):
        nn.init.kaiming_normal_(
            module.weight,
            mode="fan_out",
            nonlinearity="relu"
        )

        if module.bias is not None:
            nn.init.zeros_(module.bias)

    elif isinstance(module, nn.BatchNorm2d):
        nn.init.ones_(module.weight)
        nn.init.zeros_(module.bias)

    elif isinstance(module, nn.Linear):
        nn.init.normal_(
            module.weight,
            mean=0.0,
            std=0.01
        )
        nn.init.zeros_(module.bias)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 28. SGD mini-batch 256

### 논문 텍스트

> “We use SGD with a mini-batch size of 256.”
> 

↓

### 대응 코드

### (예상코드)

```
train_loader = torch.utils.data.DataLoader(
    training_dataset,
    batch_size=256,
    shuffle=True,
    num_workers=16,
    pin_memory=True
)

optimizer = torch.optim.SGD(
    model.parameters(),
    lr=0.1,
    momentum=0.9,
    weight_decay=0.0001
)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 29. Learning rate, weight decay, momentum

### 논문 텍스트

- 시작 learning rate: `0.1`
- plateau 시 `10`으로 나눔
- 최대 `600,000` iterations
- weight decay: `0.0001`
- momentum: `0.9`

↓

### 대응 코드

### (예상코드)

```
optimizer = torch.optim.SGD(
    model.parameters(),
    lr=0.1,
    momentum=0.9,
    weight_decay=0.0001
)

scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="min",
    factor=0.1,
    patience=2
)
```

Iteration 제한:

```
maximum_iterations = 600_000
current_iteration = 0

while current_iteration < maximum_iterations:
    for images, labels in train_loader:
        optimizer.zero_grad()

        logits = model(images)
        loss = criterion(logits, labels)

        loss.backward()
        optimizer.step()

        current_iteration += 1

        if current_iteration >= maximum_iterations:
            break
```

### 판정

`MISSING-BUT-PROVIDED`

## 30. Dropout 미사용

### 논문 텍스트

> “We do not use dropout.”
> 

↓

### 대응 코드

공식 ResNet prototxt에는 다음 계층이 없습니다.

```
type: "Dropout"
```

### 판정

`DIRECT`

50·101·152 deploy prototxt에 dropout layer가 존재하지 않습니다. [GitExtract](https://gitextract.com/KaimingHe/deep-residual-networks?utm_source=chatgpt.com)

---

## 31. 10-crop testing

### 논문 텍스트

> “For comparison studies we adopt the standard 10-crop testing.”
> 

↓

### 대응 코드

공식 저장소에는 평가 전처리 코드가 없습니다.

### (예상코드)

```
from torchvision.transforms import functional as TF

def ten_crop_tensor(
    image: Image.Image,
    crop_size: int = 224
) -> torch.Tensor:
    crops = transforms.TenCrop(
        crop_size
    )(image)

    tensors = [
        TF.to_tensor(crop)
        for crop in crops
    ]

    return torch.stack(
        tensors,
        dim=0
    )

@torch.no_grad()
def predict_ten_crop(
    model: nn.Module,
    crops: torch.Tensor
) -> torch.Tensor:
    batch_size, number_of_crops = (
        crops.shape[:2]
    )

    flattened = crops.view(
        -1,
        *crops.shape[2:]
    )

    logits = model(flattened)

    logits = logits.view(
        batch_size,
        number_of_crops,
        -1
    )

    return logits.mean(dim=1)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 32. Multi-scale testing

### 논문 텍스트

> “Images are resized such that the shorter side is in {224, 256, 384, 480, 640}.”
> 

↓

### 대응 코드

### (예상코드)

```
@torch.no_grad()
def multiscale_predict(
    model: nn.Module,
    image: Image.Image,
    scales: tuple[int, ...] = (
        224,
        256,
        384,
        480,
        640
    )
) -> torch.Tensor:
    probabilities: list[torch.Tensor] = []

    for short_side in scales:
        resized = transforms.Resize(
            short_side
        )(image)

        tensor = transforms.ToTensor()(
            resized
        ).unsqueeze(0)

        logits = model(tensor)
        probabilities.append(
            torch.softmax(logits, dim=1)
        )

    return torch.stack(
        probabilities,
        dim=0
    ).mean(dim=0)
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 5페이지 — Table 1 구조

## 33. ResNet-50 bottleneck 반복 수

### 논문 텍스트

```
conv2_x: [1×1,64 → 3×3,64 → 1×1,256] ×3
conv3_x: [1×1,128 → 3×3,128 → 1×1,512] ×4
conv4_x: [1×1,256 → 3×3,256 → 1×1,1024] ×6
conv5_x: [1×1,512 → 3×3,512 → 1×1,2048] ×3
```

↓

### 대응 코드

첫 conv2 block:

```
name: "res2a_branch2a"
num_output: 64
kernel_size: 1
```

```
name: "res2a_branch2b"
num_output: 64
kernel_size: 3
```

```
name: "res2a_branch2c"
num_output: 256
kernel_size: 1
```

동일 stage의 이름:

```
res2a
res2b
res2c
```

conv3 stage:

```
res3a
res3b
res3c
res3d
```

conv4 stage:

```
res4a
res4b
res4c
res4d
res4e
res4f
```

conv5 stage:

```
res5a
res5b
res5c
```

### 판정

`DIRECT`

---

## 34. ResNet-101 반복 수

### 논문 텍스트

```
conv2_x ×3
conv3_x ×4
conv4_x ×23
conv5_x ×3
```

↓

### 대응 코드

공식 ResNet-101 prototxt의 conv4 block 이름은 다음 범위를 포함합니다.

```
res4a
res4b1
res4b2
...
res4b22
```

총 23개입니다.

### 판정

`DIRECT`

---

## 35. ResNet-152 반복 수

### 논문 텍스트

```
conv2_x ×3
conv3_x ×8
conv4_x ×36
conv5_x ×3
```

↓

### 대응 코드

공식 ResNet-152 prototxt에는 다음 stage들이 구현됩니다.

```
conv2: res2a, res2b, res2c
conv3: res3a + 7개 후속 block
conv4: res4a + 35개 후속 block
conv5: res5a, res5b, res5c
```

### 판정

`DIRECT`

---

## 36. ResNet-18·34 basic block

### 논문 텍스트

ResNet-18과 ResNet-34는 두 개의 `3×3` convolution으로 구성된 basic block을 사용합니다.

↓

### 대응 코드

공식 저장소에는 ResNet-18·34 prototxt가 없습니다.

### (예상코드)

```
def resnet18() -> nn.Module:
    return ResNet(
        block=BasicResidualBlock,
        layers=[2, 2, 2, 2],
        number_of_classes=1000
    )

def resnet34() -> nn.Module:
    return ResNet(
        block=BasicResidualBlock,
        layers=[3, 4, 6, 3],
        number_of_classes=1000
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 6페이지

## 37. Option A·B·C

### 논문 텍스트

- A: dimension 증가 시 zero padding, 모든 shortcut parameter 없음
- B: dimension 증가 시에만 projection
- C: 모든 shortcut에 projection

↓

### 대응 코드

공식 저장소는 option B만 구현합니다.

### (예상코드)

```
def make_shortcut(
    in_channels: int,
    out_channels: int,
    stride: int,
    option: str
) -> nn.Module:
    dimensions_change = (
        stride != 1
        or in_channels != out_channels
    )

    if option == "A":
        if dimensions_change:
            return OptionAShortcut(
                in_channels,
                out_channels,
                stride
            )
        return nn.Identity()

    if option == "B":
        if dimensions_change:
            return nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=stride,
                    bias=False
                ),
                nn.BatchNorm2d(out_channels)
            )
        return nn.Identity()

    if option == "C":
        return nn.Sequential(
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=1,
                stride=stride,
                bias=False
            ),
            nn.BatchNorm2d(out_channels)
        )

    raise ValueError(
        f"지원하지 않는 option: {option}"
    )
```

### 판정

`PARTIAL + 예상코드`

---

## 38. Figure 5 — bottleneck block

### 논문 텍스트

> “The three layers are 1×1, 3×3, and 1×1 convolutions.”
> 

↓

### 대응 코드

```
layer {
    bottom: "pool1"
    top: "res2a_branch2a"
    name: "res2a_branch2a"
    type: "Convolution"
    convolution_param {
        num_output: 64
        kernel_size: 1
        stride: 1
        bias_term: false
    }
}
```

```
layer {
    bottom: "res2a_branch2a"
    top: "res2a_branch2b"
    name: "res2a_branch2b"
    type: "Convolution"
    convolution_param {
        num_output: 64
        kernel_size: 3
        pad: 1
        stride: 1
        bias_term: false
    }
}
```

```
layer {
    bottom: "res2a_branch2b"
    top: "res2a_branch2c"
    name: "res2a_branch2c"
    type: "Convolution"
    convolution_param {
        num_output: 256
        kernel_size: 1
        stride: 1
        bias_term: false
    }
}
```

### 판정

`DIRECT`

---

## 39. 1×1 계층의 차원 축소와 복원

### 논문 텍스트

> “The 1×1 layers are responsible for reducing and then increasing dimensions.”
> 

↓

### 대응 코드

```
입력 shortcut 출력: 256 channels
첫 1×1: 64 channels로 축소
3×3: 64 channels 유지
마지막 1×1: 256 channels로 복원
```

실제 설정:

```
num_output: 64
kernel_size: 1
```

```
num_output: 64
kernel_size: 3
```

```
num_output: 256
kernel_size: 1
```

### 판정

`DIRECT`

---

# 7페이지

## 40. CIFAR-10 구조

### 논문 텍스트

- 입력: `32×32`
- 첫 계층: `3×3 convolution`
- feature map: `{32,16,8}`
- filter: `{16,32,64}`
- 총 깊이: `6n+2`
- global average pooling
- 10-way FC와 softmax

↓

### 대응 코드

공식 저장소에는 CIFAR-10 코드가 없습니다. README는 별도의 `resnet-1k-layers` 저장소를 안내하지만, 현재 사용자가 지정한 저장소 자체에는 포함되지 않습니다. [GitExtract](https://gitextract.com/KaimingHe/deep-residual-networks?utm_source=chatgpt.com)

### (예상코드)

```
class CIFARResNet(nn.Module):
    def __init__(
        self,
        depth: int,
        number_of_classes: int = 10
    ):
        super().__init__()

        if (
            depth - 2
        ) % 6 != 0:
            raise ValueError(
                "CIFAR ResNet 깊이는 6n+2여야 합니다."
            )

        blocks_per_stage = (
            depth - 2
        ) // 6

        self.in_channels = 16

        self.conv1 = nn.Conv2d(
            3,
            16,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False
        )
        self.bn1 = nn.BatchNorm2d(16)
        self.relu = nn.ReLU(inplace=True)

        self.stage1 = self._make_stage(
            out_channels=16,
            blocks=blocks_per_stage,
            stride=1
        )
        self.stage2 = self._make_stage(
            out_channels=32,
            blocks=blocks_per_stage,
            stride=2
        )
        self.stage3 = self._make_stage(
            out_channels=64,
            blocks=blocks_per_stage,
            stride=2
        )

        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(
            64,
            number_of_classes
        )

        self.apply(initialize_resnet)

    def _make_stage(
        self,
        out_channels: int,
        blocks: int,
        stride: int
    ) -> nn.Sequential:
        layers = [
            BasicResidualBlock(
                self.in_channels,
                out_channels,
                stride=stride
            )
        ]

        self.in_channels = out_channels

        for _ in range(1, blocks):
            layers.append(
                BasicResidualBlock(
                    self.in_channels,
                    out_channels,
                    stride=1
                )
            )

        return nn.Sequential(*layers)

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.fc(x)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 41. CIFAR mini-batch·optimizer 설정

### 논문 텍스트

- weight decay `0.0001`
- momentum `0.9`
- dropout 없음
- mini-batch `128`
- learning rate `0.1`
- `32k`, `48k`에서 10분의 1
- `64k`에서 종료

↓

### 대응 코드

### (예상코드)

```
optimizer = torch.optim.SGD(
    model.parameters(),
    lr=0.1,
    momentum=0.9,
    weight_decay=0.0001
)

scheduler = torch.optim.lr_scheduler.MultiStepLR(
    optimizer,
    milestones=[32_000, 48_000],
    gamma=0.1
)

maximum_iterations = 64_000
```

Iteration 단위 scheduler:

```
iteration = 0

while iteration < maximum_iterations:
    for images, labels in train_loader:
        optimizer.zero_grad()

        logits = model(images)
        loss = criterion(logits, labels)

        loss.backward()
        optimizer.step()
        scheduler.step()

        iteration += 1

        if iteration >= maximum_iterations:
            break
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 42. CIFAR data augmentation

### 논문 텍스트

> “4 pixels are padded on each side, and a 32×32 crop is randomly sampled from the padded image or its horizontal flip.”
> 

↓

### 대응 코드

### (예상코드)

```
cifar_train_transform = transforms.Compose(
    [
        transforms.RandomCrop(
            size=32,
            padding=4
        ),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=(0.4914, 0.4822, 0.4465),
            std=(1.0, 1.0, 1.0)
        )
    ]
)
```

### 판정

`MISSING-BUT-PROVIDED-PARTIAL`

논문은 per-pixel mean subtraction을 사용하므로 위 채널 평균 정규화는 근사 구현입니다.

---

## 43. 110-layer warm-up

### 논문 텍스트

> “We use 0.01 to warm up the training until the training error is below 80%, about 400 iterations, and then go back to 0.1.”
> 

↓

### 대응 코드

### (예상코드)

```
def cifar110_learning_rate(
    iteration: int
) -> float:
    if iteration < 400:
        return 0.01

    if iteration < 32_000:
        return 0.1

    if iteration < 48_000:
        return 0.01

    return 0.001
```

학습 중 적용:

```
for parameter_group in optimizer.param_groups:
    parameter_group["lr"] = (
        cifar110_learning_rate(
            iteration
        )
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 8페이지

## 44. Layer response 표준편차 분석

### 논문 텍스트

> “The responses are the outputs of each 3×3 layer, after BN and before nonlinearity.”
> 

↓

### 대응 코드

공식 저장소에는 activation 분석 코드가 없습니다.

### (예상코드)

```
from collections import OrderedDict

@torch.no_grad()
def collect_layer_response_std(
    model: nn.Module,
    images: torch.Tensor
) -> OrderedDict[str, float]:
    response_stds: OrderedDict[
        str,
        float
    ] = OrderedDict()

    hooks = []

    def create_hook(name: str):
        def hook(
            module: nn.Module,
            inputs: tuple[torch.Tensor, ...],
            output: torch.Tensor
        ) -> None:
            response_stds[name] = float(
                output.std().item()
            )

        return hook

    for name, module in model.named_modules():
        if isinstance(
            module,
            nn.BatchNorm2d
        ):
            hooks.append(
                module.register_forward_hook(
                    create_hook(name)
                )
            )

    model.eval()
    model(images)

    for hook in hooks:
        hook.remove()

    return response_stds
```

### 판정

`MISSING-BUT-PROVIDED`

정확히 3×3 convolution 뒤 BN만 수집하려면 module 이름과 앞선 convolution kernel을 함께 검사해야 합니다.

---

## 45. 1202-layer ResNet

### 논문 텍스트

> “We set n=200 that leads to a 1202-layer network.”
> 

↓

### 대응 코드

```
resnet1202 = CIFARResNet(
    depth=1202,
    number_of_classes=10
)
```

검증:

```
6 × 200 + 2 = 1202
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 46. PASCAL·COCO detection에서 ResNet-101 사용

### 논문 텍스트

> “We adopt Faster R-CNN as the detection method.”
> 

> “We are interested in the improvements of replacing VGG-16 with ResNet-101.”
> 

↓

### 대응 코드

공식 저장소에는 Faster R-CNN 코드가 없습니다.

### (예상코드)

```
from torchvision.models import resnet101
from torchvision.models.detection import (
    FasterRCNN
)
from torchvision.models.detection.rpn import (
    AnchorGenerator
)

resnet = resnet101(
    weights="DEFAULT"
)

backbone = nn.Sequential(
    resnet.conv1,
    resnet.bn1,
    resnet.relu,
    resnet.maxpool,
    resnet.layer1,
    resnet.layer2,
    resnet.layer3
)

backbone.out_channels = 1024

anchor_generator = AnchorGenerator(
    sizes=((32, 64, 128, 256, 512),),
    aspect_ratios=((0.5, 1.0, 2.0),)
)

model = FasterRCNN(
    backbone=backbone,
    num_classes=81,
    rpn_anchor_generator=anchor_generator
)
```

### 판정

`MISSING-BUT-PROVIDED-PARTIAL`

이 코드는 현대 torchvision 근사 구현이며 논문 부록의 원래 Caffe Faster R-CNN 구조를 그대로 재현한 것은 아닙니다.

# 9페이지 — References

참고문헌은 대부분 코드 구현 대상이 아닙니다.

직접적인 구현 연결은 다음과 같습니다.

## 47. Reference 13 — He initialization

### 논문 연결

```
nn.init.kaiming_normal_(
    convolution.weight,
    mode="fan_out",
    nonlinearity="relu"
)
```

### 판정

`예상코드`

---

## 48. Reference 16 — Batch Normalization

### 실제 코드

```
type: "BatchNorm"
```

```
type: "Scale"
scale_param {
    bias_term: true
}
```

### 판정

`DIRECT`

---

## 49. Reference 19 — Caffe

### 실제 저장소 설정

```
.gitmodules:
path = caffe
url = https://github.com/BVLC/caffe.git
branch = master
```

### 판정

`DIRECT`

공식 저장소는 BVLC Caffe를 submodule 대상으로 지정합니다. [GitExtract](https://gitextract.com/KaimingHe/deep-residual-networks?utm_source=chatgpt.com)

---

# 10페이지 — Object Detection Baselines

## 50. conv1~conv4_x를 shared feature로 사용

### 논문 텍스트

> “We compute the full-image shared conv feature maps using conv1, conv2_x, conv3_x, and conv4_x.”
> 

↓

### 대응 코드

공식 classification prototxt에는 해당 계층들이 존재하지만 RPN과 연결하는 detection prototxt는 없습니다.

### (예상코드)

```
class ResNet101DetectionBackbone(nn.Module):
    def __init__(
        self,
        resnet: nn.Module
    ):
        super().__init__()

        self.stem = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu,
            resnet.maxpool
        )

        self.conv2_x = resnet.layer1
        self.conv3_x = resnet.layer2
        self.conv4_x = resnet.layer3

    def forward(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        x = self.stem(x)
        x = self.conv2_x(x)
        x = self.conv3_x(x)
        x = self.conv4_x(x)

        return x
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 51. RPN 300 proposals

### 논문 텍스트

> “These layers are shared by a region proposal network, generating 300 proposals.”
> 

↓

### 대응 코드

### (예상코드)

```
model.rpn.post_nms_top_n = {
    "training": 300,
    "testing": 300
}
```

또는 일반화:

```
def select_top_proposals(
    proposals: torch.Tensor,
    objectness: torch.Tensor,
    maximum_proposals: int = 300
) -> torch.Tensor:
    indices = objectness.topk(
        k=min(
            maximum_proposals,
            objectness.numel()
        )
    ).indices

    return proposals[indices]
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 52. RoI pooling 후 conv5_x 실행

### 논문 텍스트

> “RoI pooling is performed before conv5_1. All layers of conv5_x and up are adopted for each region.”
> 

↓

### 대응 코드

### (예상코드)

```
from torchvision.ops import roi_pool

class ResNetRoIHead(nn.Module):
    def __init__(
        self,
        conv5_x: nn.Module,
        classifier: nn.Linear,
        box_regressor: nn.Linear
    ):
        super().__init__()

        self.conv5_x = conv5_x
        self.classifier = classifier
        self.box_regressor = box_regressor

    def forward(
        self,
        feature_map: torch.Tensor,
        proposals: list[torch.Tensor]
    ) -> tuple[
        torch.Tensor,
        torch.Tensor
    ]:
        pooled = roi_pool(
            feature_map,
            proposals,
            output_size=(14, 14),
            spatial_scale=1.0 / 16.0
        )

        features = self.conv5_x(pooled)
        features = torch.mean(
            features,
            dim=(2, 3)
        )

        class_logits = self.classifier(
            features
        )
        box_deltas = self.box_regressor(
            features
        )

        return class_logits, box_deltas
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 53. Detection fine-tuning 중 BN 고정

### 논문 텍스트

> “The BN layers are fixed during fine-tuning for object detection.”
> 

↓

### 대응 코드

Deploy prototxt의 BN은 global statistics 사용으로 설정됩니다.

```
batch_norm_param {
    use_global_stats: true
}
```

### 판정

`DIRECT-PARTIAL`

이 설정은 추론 또는 고정 BN에 대응하지만, fine-tuning 중 parameter freeze를 수행하는 solver 설정은 저장소에 없습니다.

### (예상코드)

```
def freeze_batch_normalization(
    model: nn.Module
) -> None:
    for module in model.modules():
        if isinstance(
            module,
            nn.BatchNorm2d
        ):
            module.eval()

            for parameter in module.parameters():
                parameter.requires_grad = False
```

---

## 54. COCO detection 학습 설정

### 논문 텍스트

- 8 GPU
- RPN mini-batch: 8 images
- Fast R-CNN mini-batch: 16 images
- `240k` iterations at `0.001`
- `80k` iterations at `0.0001`

↓

### 대응 코드

### (예상코드)

```
def detection_learning_rate(
    iteration: int
) -> float:
    if iteration < 240_000:
        return 0.001

    if iteration < 320_000:
        return 0.0001

    return 0.0
```

```
rpn_batch_size = 8
fast_rcnn_batch_size = 16
maximum_iterations = 320_000
number_of_gpus = 8
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 55. Box refinement

### 논문 텍스트

> “We pool a new feature from the regressed box and obtain a new classification score and a new regressed box.”
> 

↓

### 대응 코드

### (예상코드)

```
@torch.no_grad()
def refine_boxes_twice(
    detector: nn.Module,
    images: torch.Tensor
):
    first_detections = detector(images)

    refined_inputs = [
        detection["boxes"]
        for detection in first_detections
    ]

    second_detections = detector(
        images,
        proposals=refined_inputs
    )

    return first_detections, second_detections
```

### 판정

`MISSING-BUT-PROVIDED-CONCEPTUAL`

실제 Faster R-CNN API에 맞추려면 detector가 외부 proposal을 받을 수 있도록 수정해야 합니다.

---

## 56. NMS IoU 0.3와 box voting

### 논문 텍스트

> “NMS is applied … using an IoU threshold of 0.3, followed by box voting.”
> 

↓

### 대응 코드

### (예상코드)

```
from torchvision.ops import nms

def apply_detection_nms(
    boxes: torch.Tensor,
    scores: torch.Tensor
) -> torch.Tensor:
    return nms(
        boxes,
        scores,
        iou_threshold=0.3
    )
```

Box voting:

```
def box_voting(
    selected_box: torch.Tensor,
    candidate_boxes: torch.Tensor,
    candidate_scores: torch.Tensor
) -> torch.Tensor:
    normalized_weights = (
        candidate_scores
        / candidate_scores.sum().clamp_min(
            1e-8
        )
    )

    return (
        candidate_boxes
        * normalized_weights.unsqueeze(1)
    ).sum(dim=0)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 57. Global context feature

### 논문 텍스트

> “The global feature is concatenated with the original per-region feature.”
> 

↓

### 대응 코드

### (예상코드)

```
def combine_region_and_global_context(
    region_features: torch.Tensor,
    full_feature_map: torch.Tensor
) -> torch.Tensor:
    global_features = torch.nn.functional.adaptive_avg_pool2d(
        full_feature_map,
        output_size=(1, 1)
    )

    global_features = torch.flatten(
        global_features,
        start_dim=1
    )

    repeated_global = global_features.repeat_interleave(
        repeats=region_features.shape[0]
        // global_features.shape[0],
        dim=0
    )

    return torch.cat(
        [
            region_features,
            repeated_global
        ],
        dim=1
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 58. Detection multi-scale testing

### 논문 텍스트

> “The image’s shorter sides are in {200, 400, 600, 800, 1000}.”
> 

↓

### 대응 코드

### (예상코드)

```
DETECTION_SCALES = (
    200,
    400,
    600,
    800,
    1000
)

@torch.no_grad()
def detection_multiscale_test(
    detector: nn.Module,
    image: Image.Image
):
    detections = []

    for scale in DETECTION_SCALES:
        resized = transforms.Resize(
            scale
        )(image)

        tensor = transforms.ToTensor()(
            resized
        ).unsqueeze(0)

        detections.append(
            detector(tensor)
        )

    return detections
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 11페이지

## 59. Ensemble of region proposals and classifiers

### 논문 텍스트

> “We use an ensemble for proposing regions, and the union set of proposals are processed by an ensemble of per-region classifiers.”
> 

↓

### 대응 코드

### (예상코드)

```
@torch.no_grad()
def ensemble_detection_proposals(
    proposal_models: list[nn.Module],
    images: torch.Tensor
) -> list[torch.Tensor]:
    proposal_sets = [
        model.generate_proposals(images)
        for model in proposal_models
    ]

    merged: list[torch.Tensor] = []

    for image_index in range(
        images.shape[0]
    ):
        merged.append(
            torch.cat(
                [
                    proposals[image_index]
                    for proposals in proposal_sets
                ],
                dim=0
            )
        )

    return merged
```

### 판정

`MISSING-BUT-PROVIDED`

## 60. ImageNet detection 200 classes

### 논문 텍스트

> “The ImageNet Detection task involves 200 object categories.”
> 

↓

### 대응 코드

### (예상코드)

```
classification_head = nn.Linear(
    input_features,
    201
)
```

`201`은 background 1개와 object 200개를 포함하는 일반적인 Faster R-CNN 출력 예입니다.

### 판정

`MISSING-BUT-PROVIDED`

---

# 12페이지 — ImageNet Localization

## 61. Per-class classification·box regression

### 논문 텍스트

- classification layer: `1000-d`
- regression layer: `1000×4-d`

↓

### 대응 코드

### (예상코드)

```
class PerClassLocalizationHead(nn.Module):
    def __init__(
        self,
        input_features: int,
        number_of_classes: int = 1000
    ):
        super().__init__()

        self.classification = nn.Linear(
            input_features,
            number_of_classes
        )

        self.box_regression = nn.Linear(
            input_features,
            number_of_classes * 4
        )

    def forward(
        self,
        features: torch.Tensor
    ) -> tuple[
        torch.Tensor,
        torch.Tensor
    ]:
        class_logits = self.classification(
            features
        )

        box_deltas = self.box_regression(
            features
        ).view(
            features.shape[0],
            1000,
            4
        )

        return class_logits, box_deltas
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 62. Anchor sampling — 이미지당 8개, positive:negative=1:1

### 논문 텍스트

> “8 anchors are randomly sampled for each image, where positive and negative anchors have a ratio of 1:1.”
> 

↓

### 대응 코드

### (예상코드)

```
def sample_localization_anchors(
    positive_indices: torch.Tensor,
    negative_indices: torch.Tensor
) -> tuple[
    torch.Tensor,
    torch.Tensor
]:
    positive_count = min(
        4,
        positive_indices.numel()
    )

    negative_count = min(
        4,
        negative_indices.numel()
    )

    positive_selection = positive_indices[
        torch.randperm(
            positive_indices.numel()
        )[:positive_count]
    ]

    negative_selection = negative_indices[
        torch.randperm(
            negative_indices.numel()
        )[:negative_count]
    ]

    return (
        positive_selection,
        negative_selection
    )
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 63. Fully convolutional localization test

### 논문 텍스트

> “For testing, the network is applied on the image fully-convolutionally.”
> 

↓

### 대응 코드

공식 classification prototxt의 마지막 `InnerProduct`는 고정 입력을 기대하므로 완전한 dense localization 코드는 없습니다.

### (예상코드)

```
class FullyConvolutionalClassifier(nn.Module):
    def __init__(
        self,
        original_fc: nn.Linear
    ):
        super().__init__()

        self.classifier = nn.Conv2d(
            in_channels=original_fc.in_features,
            out_channels=original_fc.out_features,
            kernel_size=1
        )

        self.classifier.weight.data.copy_(
            original_fc.weight.data.view(
                original_fc.out_features,
                original_fc.in_features,
                1,
                1
            )
        )

        self.classifier.bias.data.copy_(
            original_fc.bias.data
        )

    def forward(
        self,
        feature_map: torch.Tensor
    ) -> torch.Tensor:
        return self.classifier(feature_map)
```

### 판정

`MISSING-BUT-PROVIDED`

---

## 64. R-CNN용 상위 200개 proposal

### 논문 텍스트

> “For each training image, the highest scored 200 proposals are extracted as training samples.”
> 

↓

### 대응 코드

### (예상코드)

```
def top200_proposals(
    proposals: torch.Tensor,
    scores: torch.Tensor
) -> torch.Tensor:
    number_to_keep = min(
        200,
        scores.numel()
    )

    indices = scores.topk(
        number_to_keep
    ).indices

    return proposals[indices]
```

### 판정

`MISSING-BUT-PROVIDED`

---

# 최종 대응 요약

| 논문 요소 | 공식 저장소 상태 |
| --- | --- |
| 공식 ResNet 저장소 | 맞음 |
| ResNet-50 | 실제 Caffe prototxt 있음 |
| ResNet-101 | 실제 Caffe prototxt 있음 |
| ResNet-152 | 실제 Caffe prototxt 있음 |
| ResNet-18 | 없음, 예상코드 제공 |
| ResNet-34 | 없음, 예상코드 제공 |
| 2-layer basic block | 없음, 예상코드 제공 |
| 3-layer bottleneck | 실제 코드 있음 |
| \(F(x)+x\) | 실제 `Eltwise` 코드 있음 |
| Addition 후 ReLU | 실제 코드 있음 |
| Identity shortcut | 실제 코드 있음 |
| Projection shortcut | 실제 1×1 convolution 있음 |
| Option A zero padding | 없음, 예상코드 제공 |
| Option B | 실제 코드 있음 |
| Option C | 없음, 예상코드 제공 |
| 7×7 conv·max pool | 실제 코드 있음 |
| BatchNorm before activation | 실제 코드 있음 |
| Global average pooling | 실제 코드 있음 |
| FC 1000·softmax | 실제 코드 있음 |
| He initialization | deploy 파일에는 없음, 예상코드 제공 |
| ImageNet augmentation | 없음, 예상코드 제공 |
| SGD 학습 설정 | 없음, 예상코드 제공 |
| 10-crop test | 없음, 예상코드 제공 |
| Multi-scale classification | 없음, 예상코드 제공 |
| CIFAR-10 모델 | 없음, 예상코드 제공 |
| 110-layer warm-up | 없음, 예상코드 제공 |
| 1202-layer 모델 | 없음, 예상코드 제공 |
| Layer response 분석 | 없음, 예상코드 제공 |
| Faster R-CNN | 없음, 예상코드 제공 |
| BN freeze for detection | prototxt는 global stats 사용, freeze 코드는 없음 |
| Box refinement | 없음, 예상코드 제공 |
| Global context | 없음, 예상코드 제공 |
| Detection multi-scale test | 없음, 예상코드 제공 |
| Detection ensemble | 없음, 예상코드 제공 |
| ImageNet localization | 없음, 예상코드 제공 |

가장 중요한 점은 이 공식 Git이 **전체 학습 프로젝트가 아니라 원본 pretrained ResNet-50·101·152의 배포용 Caffe 모델 정의 저장소**라는 것입니다. 따라서 논문의 핵심 residual 구조, bottleneck, identity/projection shortcut, BN, global average pooling은 정확하게 연결되지만, 학습 설정·CIFAR 실험·detection 부록은 저장소에 없어 예상코드로 보완했습니다.