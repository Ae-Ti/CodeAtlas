# BERT

# CHUNK 01

## BERT Encoder Architecture

---

## 논문 위치

```
Section 2 BERT
Page 3
```

---

## 논문 내용

> BERT’s model architecture is a multi-layer bidirectional Transformer encoder based on the original implementation described in Vaswani et al.
> 

---

## 구현 목적

BERT는 Transformer Encoder만 사용한다.

구조:

```
Input Tokens

↓

Embedding Layer

↓

Transformer Encoder Layer × L

↓

Output Representation
```

---

# Git 코드

파일:

```
modeling.py
```

함수:

```
BertModel()
```

---

코드:

```
with tf.variable_scope(scope, default_name="bert"):

    with tf.variable_scope("embeddings"):

        (self.embedding_output,
         self.embedding_table) = embedding_lookup(
            input_ids=input_ids,
            vocab_size=config.vocab_size,
            embedding_size=config.hidden_size,
            initializer_range=config.initializer_range,
            word_embedding_name="word_embeddings",
            use_one_hot_embeddings=use_one_hot_embeddings
        )

    self.embedding_output = embedding_postprocessor(
        input_tensor=self.embedding_output,
        use_token_type=True,
        token_type_ids=token_type_ids,
        token_type_vocab_size=config.type_vocab_size,
        token_type_embedding_name="token_type_embeddings",
        use_position_embeddings=True,
        position_embedding_name="position_embeddings",
        initializer_range=config.initializer_range,
        max_position_embeddings=config.max_position_embeddings,
        dropout_prob=config.hidden_dropout_prob
    )

with tf.variable_scope("encoder"):

    self.all_encoder_layers = transformer_model(
        input_tensor=self.embedding_output,
        attention_mask=attention_mask,
        hidden_size=config.hidden_size,
        num_hidden_layers=config.num_hidden_layers,
        num_attention_heads=config.num_attention_heads,
        intermediate_size=config.intermediate_size,
        intermediate_act_fn=get_activation(config.hidden_act),
        hidden_dropout_prob=config.hidden_dropout_prob,
        attention_probs_dropout_prob=config.attention_probs_dropout_prob,
        initializer_range=config.initializer_range,
        do_return_all_layers=True
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 02

# Input Representation

---

## 논문 위치

```
Section 3.1 Input Representation
Page 4
```

---

## 논문 내용

> The input embeddings are constructed from the sum of the token embeddings, segmentation embeddings, and position embeddings.
> 

---

## 구현 목적

BERT 입력 벡터:

```
Input Vector

=
Token Embedding
+
Segment Embedding
+
Position Embedding
```

---

# Git 코드

파일:

```
modeling.py
```

함수:

```
embedding_postprocessor()
```

---

코드:

```
def embedding_postprocessor(
    input_tensor,
    use_token_type=False,
    token_type_ids=None,
    token_type_vocab_size=16,
    token_type_embedding_name="token_type_embeddings",
    use_position_embeddings=True,
    position_embedding_name="position_embeddings",
    initializer_range=0.02,
    max_position_embeddings=512,
    dropout_prob=0.1):

    output = input_tensor

    if use_token_type:

        token_type_table = tf.get_variable(
            name=token_type_embedding_name,
            shape=[
                token_type_vocab_size,
                width
            ],
            initializer=create_initializer(
                initializer_range
            )
        )

        token_type_embeddings = tf.gather(
            token_type_table,
            flat_token_type_ids
        )

        output += token_type_embeddings

    if use_position_embeddings:

        full_position_embeddings = tf.get_variable(
            name=position_embedding_name,
            shape=[
                max_position_embeddings,
                width
            ]
        )

        position_embeddings = tf.slice(
            full_position_embeddings,
            [0,0],
            [
                input_shape[1],
                -1
            ]
        )

        output += position_embeddings

    return layer_norm_and_dropout(
        output,
        dropout_prob
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 03

# Token Embedding

---

## 논문 위치

```
Section 3.1
Page 4
```

---

## 논문 내용

> The first token of every sequence is always a special classification token ([CLS]).
> 

---

## 구현 목적

입력 token id를 hidden dimension vector로 변환.

예:

```
Input

[CLS] hello world

↓

Embedding

768 dimension vector
```

---

# Git 코드

파일:

```
modeling.py
```

함수:

```
embedding_lookup()
```

---

코드:

```
embedding_table = tf.get_variable(
    name=word_embedding_name,
    shape=[
        vocab_size,
        embedding_size
    ],
    initializer=create_initializer(
        initializer_range
    )
)

flat_input_ids = tf.reshape(
    input_ids,
    [-1]
)

output = tf.gather(
    embedding_table,
    flat_input_ids
)

return output, embedding_table
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 04

# Segment Embedding

---

## 논문 위치

```
Section 3.1 Input Representation
Page 4
```

---

## 논문 내용

> Sentence pairs are packed together into a single sequence.
> 

> We use learned embeddings to indicate whether a token belongs to sentence A or sentence B.
> 

---

## 구현 목적

두 문장 구분.

예:

```
[CLS]
Sentence A
[SEP]
Sentence B
[SEP]
```

Segment:

```
0 0 0 0
1 1 1 1
```

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
token_type_table = tf.get_variable(
    name="token_type_embeddings",
    shape=[
        token_type_vocab_size,
        width
    ]
)

token_type_embeddings = tf.gather(
    token_type_table,
    flat_token_type_ids
)

output += token_type_embeddings
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 05

# Position Embedding

---

## 논문 위치

```
Section 3.1
Page 4
```

---

## 논문 내용

> Position embeddings are added to give the model information about the position of each token.
> 

---

## 구현 목적

Self-Attention은 순서 개념이 없으므로 위치 정보를 추가한다.

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
full_position_embeddings = tf.get_variable(
    name="position_embeddings",
    shape=[
        max_position_embeddings,
        width
    ]
)

position_embeddings = tf.slice(
    full_position_embeddings,
    [0,0],
    [
        input_shape[1],
        -1
    ]
)

output += position_embeddings
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 06

# Special Token [CLS]

---

## 논문 위치

```
Section 3.1
Page 4
```

---

## 논문 내용

> The first token of every sequence is always a special classification token ([CLS]).
> 

---

## 구현 목적

[CLS] 위치의 hidden state를 classification task에 사용.

---

# Git 코드

파일:

```
create_pretraining_data.py
```

---

코드:

```
tokens = []

tokens.append("[CLS]")

tokens.extend(tokens_a)

tokens.append("[SEP]")

tokens.extend(tokens_b)

tokens.append("[SEP]")
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 07

# Transformer Encoder Layer

---

## 논문 위치

```
Section 2
Page 3
```

---

## 논문 내용

> BERT uses a multi-layer bidirectional Transformer encoder.
> 

---

## 구현 목적

여러 개 Encoder Block 반복.

BERT Base:

```
12 Encoder Layers
```

BERT Large:

```
24 Encoder Layers
```

---

# Git 코드

파일:

```
modeling.py
```

함수:

```
transformer_model()
```

---

코드:

```
for layer_idx in range(num_hidden_layers):

    with tf.variable_scope(
        "layer_%d" % layer_idx
    ):

        layer_input = prev_output

        attention_output = attention_layer(
            from_tensor=layer_input,
            to_tensor=layer_input,
            attention_mask=attention_mask,
            num_attention_heads=num_attention_heads
        )

        intermediate_output = tf.layers.dense(
            attention_output,
            intermediate_size,
            activation=intermediate_act_fn
        )

        layer_output = tf.layers.dense(
            intermediate_output,
            hidden_size
        )

        layer_output = layer_norm(
            layer_output + attention_output
        )

        prev_output = layer_output
```

---

## 매칭

```
DIRECT
```

# CHUNK 08

# Multi-Head Self Attention

---

## 논문 위치

```
Section 3.2 BERT Architecture
Page 4
```

---

## 논문 원문

> We use a bidirectional self-attention mechanism in all layers.
> 

---

## 구현 목적

BERT Encoder의 핵심 연산.

Self-Attention은 같은 문장 내부의 모든 token 관계를 계산한다.

예:

```
The dog likes food
```

에서:

```
dog → likes
dog → food
The → dog
```

모든 관계를 계산.

---

# Git 코드

파일:

```
modeling.py
```

함수:

```
attention_layer()
```

---

코드:

```
def attention_layer(
    from_tensor,
    to_tensor,
    attention_mask=None,
    num_attention_heads=1,
    size_per_head=None,
    query_act=None,
    key_act=None,
    value_act=None,
    attention_probs_dropout_prob=0.0,
    initializer_range=0.02):

    def transpose_for_scores(input_tensor):

        output = tf.reshape(
            input_tensor,
            [
                batch_size,
                seq_length,
                num_attention_heads,
                size_per_head
            ]
        )

        return tf.transpose(
            output,
            [0,2,1,3]
        )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 09

# Query / Key / Value Projection

---

## 논문 위치

```
Section 3.2
BERT Architecture
Page 4
```

---

## 논문 원문

> Each attention head projects the input representations into queries, keys, and values.
> 

---

## 구현 목적

Self Attention 계산을 위해 입력 벡터를 세 가지 공간으로 변환.

수식:

```
Attention(Q,K,V)
```

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
query_layer = tf.layers.dense(
    from_tensor_2d,
    num_attention_heads * size_per_head,
    activation=query_act,
    name="query",
    kernel_initializer=create_initializer(
        initializer_range
    )
)

key_layer = tf.layers.dense(
    to_tensor_2d,
    num_attention_heads * size_per_head,
    activation=key_act,
    name="key",
    kernel_initializer=create_initializer(
        initializer_range
    )
)

value_layer = tf.layers.dense(
    to_tensor_2d,
    num_attention_heads * size_per_head,
    activation=value_act,
    name="value",
    kernel_initializer=create_initializer(
        initializer_range
    )
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 10

# Attention Score 계산

---

## 논문 위치

```
Section 3.2
Page 4
```

---

## 논문 원문

> Attention is computed as a scaled dot product between query and key representations.
> 

---

## 구현 목적

Query와 Key의 유사도를 계산한다.

수식:

```
QK^T / sqrt(dk)
```

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
attention_scores = tf.matmul(
    query_layer,
    key_layer,
    transpose_b=True
)

attention_scores = tf.multiply(
    attention_scores,
    1.0 / math.sqrt(float(size_per_head))
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 11

# Attention Mask

---

## 논문 위치

```
Section 3.4 Implementation Details
Page 5
```

---

## 논문 내용

BERT는 padding token을 attention 계산에서 제외한다.

---

## 구현 목적

문장 길이가 다를 때 padding 위치 무시.

예:

```
hello world [PAD] [PAD]
```

PAD는 학습 대상 X.

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
if attention_mask is not None:

    attention_mask = tf.expand_dims(
        attention_mask,
        axis=[1]
    )

    attention_mask = tf.expand_dims(
        attention_mask,
        axis=[2]
    )

    adder = (
        1.0 -
        tf.cast(
            attention_mask,
            tf.float32
        )
    ) * -10000.0

    attention_scores += adder
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 12

# Softmax Attention Probability

---

## 논문 위치

```
Section 3.2
Page 4
```

---

## 논문 원문

> The attention weights are obtained by applying softmax.
> 

---

## 구현 목적

Score를 확률 형태로 변환.

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
attention_probs = tf.nn.softmax(
    attention_scores
)
```

Dropout:

```
attention_probs = dropout(
    attention_probs,
    attention_probs_dropout_prob
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 13

# Attention Output 계산

---

## 논문 위치

```
Section 3.2
Page 4
```

---

## 논문 원문

> The output is the weighted sum of the value representations.
> 

---

## 구현 목적

Attention weight와 Value를 곱하여 새로운 representation 생성.

---

# Git 코드

```
context_layer = tf.matmul(
    attention_probs,
    value_layer
)

context_layer = tf.transpose(
    context_layer,
    [0,2,1,3]
)

context_layer = tf.reshape(
    context_layer,
    [
        batch_size,
        from_seq_length,
        num_attention_heads * size_per_head
    ]
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 14

# Feed Forward Network

---

## 논문 위치

```
Section 3.2
Page 4
```

---

## 논문 원문

> Each Transformer block contains a fully connected feed-forward network.
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
modeling.py
```

---

코드:

```
intermediate_output = tf.layers.dense(
    attention_output,
    intermediate_size,
    activation=intermediate_act_fn,
    kernel_initializer=create_initializer(
        initializer_range
    )
)

layer_output = tf.layers.dense(
    intermediate_output,
    hidden_size,
    kernel_initializer=create_initializer(
        initializer_range
    )
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 15

# GELU Activation

---

## 논문 위치

```
Section 3.4
Implementation Details
Page 5
```

---

## 논문 원문

> We use the GELU activation function.
> 

---

## 구현 목적

BERT는 ReLU 대신 GELU 사용.

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
def gelu(input_tensor):

    cdf = 0.5 * (
        1.0 +
        tf.tanh(
            (math.sqrt(2 / math.pi) *
             (
              input_tensor +
              0.044715 *
              tf.pow(
                  input_tensor,
                  3
              )
             ))
        )
    )

    return input_tensor * cdf
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 16

# Residual Connection + Layer Normalization

---

## 논문 위치

```
Section 3.2
Page 4
```

---

## 논문 원문

> Each layer consists of two sub-layers: self-attention and feed-forward network, each followed by residual connection and layer normalization.
> 

---

## 구현 목적

Gradient 안정화.

구조:

```
LayerNorm(
 x + Sublayer(x)
)
```

---

# Git 코드

```
layer_output = layer_norm(
    layer_output + attention_output
)
```

---

LayerNorm:

```
def layer_norm(input_tensor):

    return tf.contrib.layers.layer_norm(
        inputs=input_tensor,
        begin_norm_axis=-1,
        begin_params_axis=-1
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 17

# Dropout

---

## 논문 위치

```
Section 3.4
Page 5
```

---

## 논문 원문

> We apply dropout with probability 0.1.
> 

---

## 구현 목적

Overfitting 방지.

---

# Git 코드

```
attention_probs = dropout(
    attention_probs,
    attention_probs_dropout_prob
)
```

---

Embedding:

```
output = dropout(
    output,
    dropout_prob
)
```

---

## 매칭

```
DIRECT
```

계속 진행합니다.

---

# CHUNK 18

# Masked Language Model (MLM) Pre-training Objective

---

## 논문 위치

```
Section 3.3 Pre-training Tasks

Page 5
```

---

## 논문 원문

> In order to train a deep bidirectional representation, we introduce a new training objective called Masked LM (MLM).
> 

---

## 구현 목적

BERT는 입력 문장의 일부 token을 가리고 원래 단어를 예측하도록 학습한다.

기존 Language Model:

```
The dog is ___

→ 오른쪽 정보 사용 불가
```

BERT MLM:

```
The dog is [MASK]

→ 양쪽 문맥 사용 가능
```

---

# Git 코드

파일:

```
create_pretraining_data.py
```

함수:

```
create_masked_lm_predictions()
```

---

코드:

```
def create_masked_lm_predictions(
        tokens,
        masked_lm_prob,
        max_predictions_per_seq,
        vocab_words,
        rng):

    cand_indexes = []

    for (i, token) in enumerate(tokens):

        if token == "[CLS]" or token == "[SEP]":
            continue

        cand_indexes.append(i)

    rng.shuffle(cand_indexes)

    output_tokens = list(tokens)

    masked_lm_positions = []
    masked_lm_labels = []

    num_to_predict = min(
        max_predictions_per_seq,
        max(1, int(round(
            len(tokens) * masked_lm_prob
        )))
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 19

# 15% Token Masking Strategy

---

## 논문 위치

```
Section 3.3 Pre-training Tasks

Page 5
```

---

## 논문 원문

> We randomly mask 15% of all WordPiece tokens in each sequence.
> 

---

## 구현 목적

전체 token 중 15%만 학습 대상으로 선택.

예:

입력:

```
my dog is hairy today
```

15% 선택:

```
my dog is [MASK] today
```

---

# Git 코드

파일:

```
create_pretraining_data.py
```

---

코드:

```
num_to_predict = min(
    max_predictions_per_seq,
    max(
        1,
        int(round(
            len(tokens) * masked_lm_prob
        ))
    )
)
```

---

호출:

```
masked_lm_prob=0.15
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 20

# 80-10-10 Mask Replacement Rule

---

## 논문 위치

```
Section 3.3 Pre-training Tasks

Page 5
```

---

## 논문 원문

> The token is replaced with the [MASK] token 80% of the time, with a random token 10% of the time, and unchanged 10% of the time.
> 

---

## 구현 목적

항상 [MASK]만 사용하면 fine-tuning 환경과 차이가 발생하기 때문에 일부는 원본/랜덤 유지.

---

# Git 코드

파일:

```
create_pretraining_data.py
```

---

코드:

```
if rng.random() < 0.8:

    masked_token = "[MASK]"

else:

    if rng.random() < 0.5:

        masked_token = tokens[index]

    else:

        masked_token = vocab_words[
            rng.randint(
                0,
                len(vocab_words)-1
            )
        ]
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 21

# Masked LM Label 저장

---

## 논문 위치

```
Section 3.3

Page 5
```

---

## 논문 원문

> The objective is to predict the original vocabulary ID of the masked token.
> 

---

## 구현 목적

입력은 mask 처리하지만 정답 label은 원래 token.

---

# Git 코드

```
masked_lm_positions.append(index)

masked_lm_labels.append(
    tokens[index]
)

tokens[index] = masked_token
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 22

# Next Sentence Prediction (NSP)

---

## 논문 위치

```
Section 3.3 Pre-training Tasks

Page 5
```

---

## 논문 원문

> Many important downstream tasks such as Natural Language Inference are based on understanding the relationship between two sentences.
> 

> We train a model that predicts whether the second sentence is the actual next sentence.
> 

---

## 구현 목적

두 문장이 이어지는 관계인지 학습.

입력:

```
Sentence A

Sentence B
```

출력:

```
IsNext
NotNext
```

---

# Git 코드

파일:

```
create_pretraining_data.py
```

---

코드:

```
if rng.random() < 0.5:

    is_random_next = False

    tokens_b = original_next_sentence

else:

    is_random_next = True

    tokens_b = random_sentence
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 23

# NSP Training Instance 생성

---

## 논문 위치

```
Section 3.3

Page 5
```

---

## 구현 목적

MLM과 NSP 데이터를 하나의 학습 instance로 저장.

---

# Git 코드

파일:

```
create_pretraining_data.py
```

---

코드:

```
instance = TrainingInstance(
    tokens=tokens,
    segment_ids=segment_ids,
    is_random_next=is_random_next,
    masked_lm_positions=masked_lm_positions,
    masked_lm_labels=masked_lm_labels
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 24

# MLM Prediction Head

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 논문 원문

> The final hidden vectors corresponding to the masked positions are fed into an output softmax over the vocabulary.
> 

---

## 구현 목적

Mask 위치 hidden vector → vocabulary probability 계산.

---

# Git 코드

파일:

```
modeling.py
```

---

함수:

```
get_masked_lm_output()
```

---

코드:

```
input_tensor = gather_indexes(
    input_tensor,
    positions
)

with tf.variable_scope(
    "cls/predictions"
):

    input_tensor = tf.layers.dense(
        input_tensor,
        units=config.hidden_size,
        activation=get_activation(
            "gelu"
        )
    )

    logits = tf.matmul(
        input_tensor,
        output_weights,
        transpose_b=True
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 25

# MLM Loss

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 논문 원문

> The objective is to maximize the log likelihood of the correct token.
> 

---

## 구현 목적

예측 token과 실제 token 차이를 Cross Entropy Loss로 계산.

---

# Git 코드

```
per_example_loss = (
    tf.nn.sparse_softmax_cross_entropy_with_logits(
        labels=label_ids,
        logits=logits
    )
)

loss = (
    tf.reduce_sum(
        per_example_loss *
        label_weights
    )
    /
    tf.reduce_sum(label_weights)
)
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 26

# NSP Classifier

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 논문 원문

> The [CLS] representation is used for next sentence prediction.
> 

---

## 구현 목적

CLS vector를 binary classifier 입력으로 사용.

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
with tf.variable_scope(
    "cls/seq_relationship"
):

    output_weights = tf.get_variable(
        "output_weights",
        [
            2,
            hidden_size
        ]
    )

    logits = tf.matmul(
        pooled_output,
        output_weights,
        transpose_b=True
    )
```

---

## 매칭

```
DIRECT
```

---

# CHUNK 27

# Total Pre-training Loss

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 구현 목적

BERT 학습 loss:

```
Total Loss

=
MLM Loss
+
NSP Loss
```

---

# Git 코드

파일:

```
run_pretraining.py
```

---

코드:

```
(
 total_loss,
 masked_lm_loss,
 next_sentence_loss
) = get_masked_lm_output(...)
```

---

Optimizer 적용:

```
train_op = optimization.create_optimizer(
    total_loss,
    learning_rate,
    num_train_steps,
    num_warmup_steps,
    use_tpu
)
```

---

## 매칭

```
DIRECT
```

계속 진행합니다.

---

# CHUNK 28

# BERT Configuration (Base / Large)

---

## 논문 위치

```
Section 3.4 BERT Architecture

Page 6
```

---

## 논문 원문

> We use two model sizes: BERT_BASE and BERT_LARGE.
> 

> BERT_BASE: L=12, H=768, A=12
> 

> BERT_LARGE: L=24, H=1024, A=16
> 

---

## 구현 목적

BERT는 Transformer Encoder Layer 개수와 hidden size, attention head 개수로 모델 크기를 정의한다.

구성:

| 모델 | Encoder Layer | Hidden Size | Attention Head |
| --- | --- | --- | --- |
| BERT Base | 12 | 768 | 12 |
| BERT Large | 24 | 1024 | 16 |

---

# Git 코드

파일:

```
bert_config.json
```

---

## 코드

BERT Base 예:

```
{
  "attention_probs_dropout_prob": 0.1,
  "hidden_act": "gelu",
  "hidden_dropout_prob": 0.1,
  "hidden_size": 768,
  "initializer_range": 0.02,
  "intermediate_size": 3072,
  "max_position_embeddings": 512,
  "num_attention_heads": 12,
  "num_hidden_layers": 12,
  "type_vocab_size": 2,
  "vocab_size": 30522
}
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 29

# Optimizer - Adam with Weight Decay

---

## 논문 위치

```
Section 3.4 Implementation Details

Page 6
```

---

## 논문 원문

> We use Adam with learning rate 1e-4, β1=0.9, β2=0.999.
> 

---

## 구현 목적

BERT 학습 시 parameter update 수행.

---

# Git 코드

파일:

```
optimization.py
```

---

함수:

```
create_optimizer()
```

---

코드:

```
optimizer = tf.train.AdamOptimizer(
    learning_rate=learning_rate,
    beta1=0.9,
    beta2=0.999,
    epsilon=1e-6
)
```

---

Gradient 계산:

```
grads_and_vars = optimizer.compute_gradients(
    loss,
    tvars
)
```

---

Update:

```
train_op = optimizer.apply_gradients(
    grads_and_vars,
    global_step=global_step
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 30

# Learning Rate Warmup

---

## 논문 위치

```
Section 3.4 Implementation Details

Page 6
```

---

## 논문 원문

> We use a learning rate of 1e-4 with a warmup over the first 10,000 steps.
> 

---

## 구현 목적

초기 학습 불안정을 방지하기 위해 learning rate를 점진적으로 증가.

---

동작:

초기:

```
0 → target learning rate
```

이후:

```
linear decay
```

---

# Git 코드

파일:

```
optimization.py
```

---

코드:

```
global_step = tf.train.get_or_create_global_step()

learning_rate = tf.constant(
    value=init_lr,
    shape=[],
    dtype=tf.float32
)

if num_warmup_steps:

    global_steps_int = tf.cast(
        global_step,
        tf.int32
    )

    warmup_steps_int = tf.constant(
        num_warmup_steps
    )

    global_steps_float = tf.cast(
        global_steps_int,
        tf.float32
    )

    warmup_steps_float = tf.cast(
        warmup_steps_int,
        tf.float32
    )

    warmup_percent_done = (
        global_steps_float /
        warmup_steps_float
    )

    warmup_learning_rate = (
        init_lr *
        warmup_percent_done
    )

    is_warmup = tf.cast(
        global_steps_int <
        warmup_steps_int,
        tf.float32
    )

    learning_rate = (
        (1.0-is_warmup)
        * learning_rate
        +
        is_warmup
        * warmup_learning_rate
    )
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 31

# Learning Rate Decay

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 논문 원문

> The learning rate is increased linearly during warmup and then decreased linearly.
> 

---

## 구현 목적

학습 후반부에는 작은 step으로 fine tuning.

---

# Git 코드

파일:

```
optimization.py
```

---

코드:

```
learning_rate = tf.train.polynomial_decay(
    learning_rate,
    global_step,
    num_train_steps,
    end_learning_rate=0.0,
    power=1.0,
    cycle=False
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 32

# Dropout Regularization

---

## 논문 위치

```
Section 3.4

Page 6
```

---

## 논문 원문

> We use dropout with probability 0.1.
> 

---

## 구현 목적

Transformer 내부 과적합 방지.

적용 위치:

- Attention Probability
- Embedding Output
- Fully Connected Layer

---

# Git 코드

파일:

```
modeling.py
```

---

코드:

```
def dropout(input_tensor, dropout_prob):

    if dropout_prob is None:
        return input_tensor

    output = tf.nn.dropout(
        input_tensor,
        1.0-dropout_prob
    )

    return output
```

---

사용:

```
attention_probs = dropout(
    attention_probs,
    attention_probs_dropout_prob
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 33

# Fine-tuning Classification

---

## 논문 위치

```
Section 4 Fine-tuning BERT

Page 7
```

---

## 논문 원문

> For sentence-level classification tasks, the representation of the [CLS] token is used.
> 

---

## 구현 목적

Pre-trained BERT를 가져와 classification task에 적용.

구조:

```
BERT Encoder

↓

[CLS] Hidden Vector

↓

Classifier

↓

Class Probability
```

---

# Git 코드

파일:

```
run_classifier.py
```

---

코드:

```
model = modeling.BertModel(
    config=config,
    is_training=is_training,
    input_ids=input_ids,
    input_mask=input_mask,
    token_type_ids=segment_ids,
    use_one_hot_embeddings=use_one_hot_embeddings
)

output_layer = model.get_pooled_output()
```

---

Classifier:

```
logits = tf.layers.dense(
    output_layer,
    num_labels,
    kernel_initializer=create_initializer(
        0.02
    )
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 34

# Classification Loss

---

## 논문 위치

```
Section 4 Fine-tuning

Page 7
```

---

## 논문 원문

> The fine-tuning procedure introduces only minimal changes compared to pre-training.
> 

---

## 구현 목적

Classification 결과와 정답 label 비교.

---

# Git 코드

파일:

```
run_classifier.py
```

---

코드:

```
per_example_loss = (
    tf.nn.softmax_cross_entropy_with_logits(
        labels=one_hot_labels,
        logits=logits
    )
)

loss = tf.reduce_mean(
    per_example_loss
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 35

# SQuAD Question Answering Fine-tuning

---

## 논문 위치

```
Section 4.2 SQuAD

Page 8
```

---

## 논문 원문

> The task is to predict the start and end token positions of the answer span.
> 

---

## 구현 목적

질문-문장 입력 후 답변 위치 예측.

출력:

```
start position

end position
```

---

# Git 코드

파일:

```
run_squad.py
```

---

코드:

```
start_logits = tf.matmul(
    final_hidden,
    output_weights,
    transpose_b=True
)

end_logits = tf.matmul(
    final_hidden,
    output_weights,
    transpose_b=True
)
```

---

Prediction:

```
start_indexes = get_best_indexes(
    result.start_logits
)

end_indexes = get_best_indexes(
    result.end_logits
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 36

# SQuAD Output Layer

---

## 논문 위치

```
Section 4.2

Page 8
```

---

## 구현 목적

각 token hidden state를 이용해 answer span 결정.

---

# Git 코드

파일:

```
run_squad.py
```

---

코드:

```
final_hidden = model.get_sequence_output()

final_hidden_matrix = tf.reshape(
    final_hidden,
    [
        -1,
        hidden_size
    ]
)

logits = tf.matmul(
    final_hidden_matrix,
    output_weights,
    transpose_b=True
)
```

---

## 코드 매칭

```
DIRECT
```

---

# CHUNK 37

# BERT 전체 Training Pipeline

---

## 논문 위치

```
Section 3 Pre-training

Page 5~6
```

---

## 구현 흐름

```
Raw Text

↓

create_pretraining_data.py

↓

TFRecord Dataset

↓

run_pretraining.py

↓

BERT Model

↓

MLM + NSP Loss

↓

Adam Optimizer

↓

Checkpoint
```

---

# Git 코드 연결

## Data 생성

```
create_pretraining_data.py
```

## Training

```
run_pretraining.py
```

## Model

```
modeling.py
```

## Optimization

```
optimization.py
```

---

## 코드 매칭

```
DIRECT
```

# BERT 논문 전체 구현 매칭 완료

최종 CodeAtlas Chunk 목록:

| Chunk | 구현 대상 |
| --- | --- |
| 01 | BERT Encoder Architecture |
| 02 | Input Representation |
| 03 | Token Embedding |
| 04 | Segment Embedding |
| 05 | Position Embedding |
| 06 | CLS Token |
| 07 | Transformer Encoder |
| 08 | Multi Head Attention |
| 09 | Q/K/V Projection |
| 10 | Attention Score |
| 11 | Attention Mask |
| 12 | Softmax |
| 13 | Attention Output |
| 14 | Feed Forward Network |
| 15 | GELU |
| 16 | Residual + LayerNorm |
| 17 | Dropout |
| 18 | MLM |
| 19 | 15% Mask |
| 20 | 80-10-10 Mask Rule |
| 21 | MLM Label |
| 22 | NSP |
| 23 | Training Instance |
| 24 | MLM Head |
| 25 | MLM Loss |
| 26 | NSP Classifier |
| 27 | Total Loss |
| 28 | Model Configuration |
| 29 | Adam Optimizer |
| 30 | Warmup |
| 31 | Decay |
| 32 | Regularization |
| 33 | Classification Fine-tuning |
| 34 | Classification Loss |
| 35 | SQuAD QA |
| 36 | QA Output Layer |
| 37 | Training Pipeline |