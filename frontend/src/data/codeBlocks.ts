export interface CodeBlock {
  codeBlockId: number;
  repoName: string;
  filePath: string;
  className?: string;
  functionName: string;
  startLine: number;
  endLine: number;
  codeText: string;
  similarityScore: number;
  githubUrl: string;
  explanation: string;
}

export interface MappingResult {
  queryChunk: { sectionTitle: string; chunkText: string };
  results: CodeBlock[];
}

// Mapping: chunkId -> CodeBlock[]
export const mockCodeBlocks: Record<number, CodeBlock[]> = {
  // Chunk 101: Multi-Head Attention
  101: [
    {
      codeBlockId: 1001,
      repoName: 'annotated-transformer',
      filePath: 'model/attention.py',
      className: 'MultiHeadedAttention',
      functionName: 'forward',
      startLine: 42,
      endLine: 89,
      codeText: `class MultiHeadedAttention(nn.Module):
    def __init__(self, h, d_model, dropout=0.1):
        super().__init__()
        assert d_model % h == 0
        self.d_k = d_model // h
        self.h = h
        self.linears = clones(nn.Linear(d_model, d_model), 4)
        self.attn = None
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, query, key, value, mask=None):
        nbatches = query.size(0)
        # 1) Do all the linear projections in batch
        query, key, value = [
            lin(x).view(nbatches, -1, self.h, self.d_k).transpose(1, 2)
            for lin, x in zip(self.linears, (query, key, value))
        ]
        # 2) Apply attention on all the projected vectors
        x, self.attn = attention(query, key, value,
                                  mask=mask, dropout=self.dropout)
        # 3) Concat and apply a final linear
        x = x.transpose(1, 2).contiguous().view(
            nbatches, -1, self.h * self.d_k
        )
        return self.linears[-1](x)`,
      similarityScore: 0.92,
      githubUrl: 'https://github.com/harvardnlp/annotated-transformer/blob/master/model/attention.py#L42',
      explanation: 'This code directly implements the multi-head attention mechanism described in the paper. The forward method performs parallel attention computation across h heads by projecting Q, K, V through linear layers, computing scaled dot-product attention, and concatenating the results.',
    },
    {
      codeBlockId: 1002,
      repoName: 'huggingface/transformers',
      filePath: 'src/transformers/models/bert/modeling_bert.py',
      className: 'BertSelfAttention',
      functionName: 'forward',
      startLine: 210,
      endLine: 280,
      codeText: `class BertSelfAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.num_attention_heads = config.num_attention_heads
        self.attention_head_size = int(config.hidden_size / config.num_attention_heads)
        self.all_head_size = self.num_attention_heads * self.attention_head_size
        self.query = nn.Linear(config.hidden_size, self.all_head_size)
        self.key = nn.Linear(config.hidden_size, self.all_head_size)
        self.value = nn.Linear(config.hidden_size, self.all_head_size)
        self.dropout = nn.Dropout(config.attention_probs_dropout_prob)

    def forward(self, hidden_states, attention_mask=None):
        query_layer = self.query(hidden_states)
        key_layer = self.key(hidden_states)
        value_layer = self.value(hidden_states)
        # ... reshape and compute attention
        return context_layer`,
      similarityScore: 0.85,
      githubUrl: 'https://github.com/huggingface/transformers/blob/main/src/transformers/models/bert/modeling_bert.py#L210',
      explanation: 'HuggingFace BERT implementation of multi-head attention. Uses separate Q, K, V linear projections following the same architecture pattern described in the Transformer paper.',
    },
    {
      codeBlockId: 1003,
      repoName: 'pytorch/pytorch',
      filePath: 'torch/nn/modules/activation.py',
      className: 'MultiheadAttention',
      functionName: 'forward',
      startLine: 1050,
      endLine: 1120,
      codeText: `class MultiheadAttention(Module):
    def __init__(self, embed_dim, num_heads, dropout=0.0, ...):
        super().__init__()
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.in_proj_weight = Parameter(torch.empty(3 * embed_dim, embed_dim))
        self.out_proj = NonDynamicallyQuantizableLinear(embed_dim, embed_dim)

    def forward(self, query, key, value, key_padding_mask=None,
                need_weights=True, attn_mask=None):
        return F.multi_head_attention_forward(
            query, key, value, self.embed_dim, self.num_heads,
            self.in_proj_weight, self.in_proj_bias,
            self.out_proj.weight, self.out_proj.bias,
            dropout_p=self.dropout, training=self.training)`,
      similarityScore: 0.81,
      githubUrl: 'https://github.com/pytorch/pytorch/blob/main/torch/nn/modules/activation.py#L1050',
      explanation: 'PyTorch official MultiheadAttention implementation. Uses a combined in_proj_weight for Q, K, V and delegates to F.multi_head_attention_forward for optimized computation.',
    },
  ],

  // Chunk 102: Scaled Dot-Product Attention
  102: [
    {
      codeBlockId: 1010,
      repoName: 'annotated-transformer',
      filePath: 'model/attention.py',
      functionName: 'attention',
      startLine: 10,
      endLine: 30,
      codeText: `def attention(query, key, value, mask=None, dropout=None):
    """Compute 'Scaled Dot Product Attention'"""
    d_k = query.size(-1)
    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(mask == 0, -1e9)
    p_attn = scores.softmax(dim=-1)
    if dropout is not None:
        p_attn = dropout(p_attn)
    return torch.matmul(p_attn, value), p_attn`,
      similarityScore: 0.95,
      githubUrl: 'https://github.com/harvardnlp/annotated-transformer/blob/master/model/attention.py#L10',
      explanation: 'Direct implementation of the scaled dot-product attention formula: Attention(Q,K,V) = softmax(QK^T/√dk)V. Includes optional masking for decoder self-attention.',
    },
    {
      codeBlockId: 1011,
      repoName: 'tensorflow/tensorflow',
      filePath: 'tensorflow/python/ops/nn_impl.py',
      functionName: 'scaled_dot_product_attention',
      startLine: 200,
      endLine: 240,
      codeText: `def scaled_dot_product_attention(query, key, value, attn_mask=None):
    L, S = query.size(-2), key.size(-2)
    scale_factor = 1 / math.sqrt(query.size(-1))
    attn_weight = query @ key.transpose(-2, -1) * scale_factor
    if attn_mask is not None:
        attn_weight += attn_mask
    attn_weight = torch.softmax(attn_weight, dim=-1)
    return attn_weight @ value`,
      similarityScore: 0.88,
      githubUrl: 'https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/ops/nn_impl.py#L200',
      explanation: 'TensorFlow implementation of scaled dot-product attention. Follows the exact same mathematical formulation using matrix multiplication and softmax normalization.',
    },
  ],

  // Chunk 103: Positional Encoding
  103: [
    {
      codeBlockId: 1020,
      repoName: 'annotated-transformer',
      filePath: 'model/positional.py',
      className: 'PositionalEncoding',
      functionName: 'forward',
      startLine: 5,
      endLine: 35,
      codeText: `class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout, max_len=5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2) * -(math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x):
        x = x + self.pe[:, : x.size(1)].requires_grad_(False)
        return self.dropout(x)`,
      similarityScore: 0.93,
      githubUrl: 'https://github.com/harvardnlp/annotated-transformer/blob/master/model/positional.py#L5',
      explanation: 'Implements sinusoidal positional encoding using sin/cos functions of different frequencies, exactly as described in Section 3.5 of the paper.',
    },
  ],

  // Chunk 201: Residual Learning
  201: [
    {
      codeBlockId: 2001,
      repoName: 'torchvision',
      filePath: 'torchvision/models/resnet.py',
      className: 'BasicBlock',
      functionName: 'forward',
      startLine: 55,
      endLine: 85,
      codeText: `class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample

    def forward(self, x):
        identity = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity  # Residual connection!
        out = self.relu(out)
        return out`,
      similarityScore: 0.94,
      githubUrl: 'https://github.com/pytorch/vision/blob/main/torchvision/models/resnet.py#L55',
      explanation: 'The BasicBlock class implements F(x) + x residual learning. The identity shortcut connection (out += identity) is the key insight from the paper, enabling training of very deep networks.',
    },
    {
      codeBlockId: 2002,
      repoName: 'torchvision',
      filePath: 'torchvision/models/resnet.py',
      className: 'Bottleneck',
      functionName: 'forward',
      startLine: 90,
      endLine: 135,
      codeText: `class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super().__init__()
        self.conv1 = conv1x1(inplanes, planes)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = conv3x3(planes, planes, stride)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = conv1x1(planes, planes * self.expansion)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion)

    def forward(self, x):
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        out = self.relu(out)
        return out`,
      similarityScore: 0.89,
      githubUrl: 'https://github.com/pytorch/vision/blob/main/torchvision/models/resnet.py#L90',
      explanation: 'Bottleneck residual block using 1×1, 3×3, 1×1 convolution pattern. The 1×1 convolutions reduce and restore dimensions, making the 3×3 convolution operate on a lower-dimensional bottleneck.',
    },
  ],

  // Chunk 301: Masked Language Model
  301: [
    {
      codeBlockId: 3001,
      repoName: 'huggingface/transformers',
      filePath: 'src/transformers/models/bert/modeling_bert.py',
      className: 'BertForMaskedLM',
      functionName: 'forward',
      startLine: 1150,
      endLine: 1200,
      codeText: `class BertForMaskedLM(BertPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.bert = BertModel(config)
        self.cls = BertOnlyMLMHead(config)

    def forward(self, input_ids=None, attention_mask=None, labels=None):
        outputs = self.bert(input_ids, attention_mask=attention_mask)
        sequence_output = outputs[0]
        prediction_scores = self.cls(sequence_output)
        masked_lm_loss = None
        if labels is not None:
            loss_fct = CrossEntropyLoss()
            masked_lm_loss = loss_fct(
                prediction_scores.view(-1, self.config.vocab_size),
                labels.view(-1)
            )
        return MaskedLMOutput(loss=masked_lm_loss, logits=prediction_scores)`,
      similarityScore: 0.91,
      githubUrl: 'https://github.com/huggingface/transformers/blob/main/src/transformers/models/bert/modeling_bert.py#L1150',
      explanation: 'HuggingFace implementation of BERT masked language model. The forward pass takes masked input_ids, generates predictions for masked positions through the MLM head, and computes cross-entropy loss against the original tokens.',
    },
  ],

  // Chunk 501: Vision Transformer
  501: [
    {
      codeBlockId: 5001,
      repoName: 'google/vision_transformer',
      filePath: 'vit_jax/models_vit.py',
      className: 'VisionTransformer',
      functionName: 'forward',
      startLine: 80,
      endLine: 130,
      codeText: `class VisionTransformer(nn.Module):
    def __init__(self, img_size=224, patch_size=16, in_chans=3,
                 embed_dim=768, depth=12, num_heads=12):
        super().__init__()
        self.patch_embed = PatchEmbed(img_size, patch_size, in_chans, embed_dim)
        num_patches = self.patch_embed.num_patches
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
        self.blocks = nn.Sequential(*[
            Block(embed_dim, num_heads) for _ in range(depth)
        ])
        self.norm = nn.LayerNorm(embed_dim)
        self.head = nn.Linear(embed_dim, num_classes)

    def forward(self, x):
        x = self.patch_embed(x)
        cls_token = self.cls_token.expand(x.shape[0], -1, -1)
        x = torch.cat((cls_token, x), dim=1)
        x = x + self.pos_embed
        x = self.blocks(x)
        x = self.norm(x[:, 0])  # CLS token
        return self.head(x)`,
      similarityScore: 0.90,
      githubUrl: 'https://github.com/google-research/vision_transformer/blob/main/vit_jax/models_vit.py#L80',
      explanation: 'Implements the ViT architecture: patches → linear embedding → prepend CLS token → add position embeddings → Transformer encoder → classify from CLS token output.',
    },
  ],

  // Chunk 601: Forward Diffusion
  601: [
    {
      codeBlockId: 6001,
      repoName: 'hojonathanho/diffusion',
      filePath: 'diffusion/gaussian_diffusion.py',
      className: 'GaussianDiffusion',
      functionName: 'q_sample',
      startLine: 120,
      endLine: 155,
      codeText: `class GaussianDiffusion:
    def __init__(self, betas):
        self.betas = betas
        self.alphas = 1.0 - betas
        self.alphas_cumprod = np.cumprod(self.alphas)
        self.sqrt_alphas_cumprod = np.sqrt(self.alphas_cumprod)
        self.sqrt_one_minus_alphas_cumprod = np.sqrt(1.0 - self.alphas_cumprod)

    def q_sample(self, x_start, t, noise=None):
        """Forward diffusion: sample x_t from q(x_t | x_0)"""
        if noise is None:
            noise = torch.randn_like(x_start)
        return (
            extract(self.sqrt_alphas_cumprod, t, x_start.shape) * x_start
            + extract(self.sqrt_one_minus_alphas_cumprod, t, x_start.shape) * noise
        )`,
      similarityScore: 0.93,
      githubUrl: 'https://github.com/hojonathanho/diffusion/blob/master/diffusion/gaussian_diffusion.py#L120',
      explanation: 'Implements the forward diffusion process q(x_t|x_0) using the reparameterization trick. The noisy sample is computed as √ᾱt·x₀ + √(1-ᾱt)·ε, directly following the paper\'s formulation.',
    },
  ],

  // Chunk 701: Clipped Surrogate Objective
  701: [
    {
      codeBlockId: 7001,
      repoName: 'openai/baselines',
      filePath: 'baselines/ppo2/model.py',
      className: 'PPO',
      functionName: 'compute_loss',
      startLine: 45,
      endLine: 80,
      codeText: `def compute_loss(self, obs, actions, advantages, old_log_probs, clip_range=0.2):
    # Get current policy log probabilities
    log_probs = self.policy.log_prob(obs, actions)

    # Compute probability ratio
    ratio = torch.exp(log_probs - old_log_probs)

    # Clipped surrogate objective
    surr1 = ratio * advantages
    surr2 = torch.clamp(ratio, 1.0 - clip_range, 1.0 + clip_range) * advantages
    policy_loss = -torch.min(surr1, surr2).mean()

    # Value function loss
    value_pred = self.value_fn(obs)
    value_loss = F.mse_loss(value_pred, returns)

    # Entropy bonus
    entropy = self.policy.entropy(obs).mean()

    return policy_loss + 0.5 * value_loss - 0.01 * entropy`,
      similarityScore: 0.91,
      githubUrl: 'https://github.com/openai/baselines/blob/master/baselines/ppo2/model.py#L45',
      explanation: 'Implements the PPO clipped surrogate objective. The ratio r(θ) = π(a|s)/π_old(a|s) is clipped to [1-ε, 1+ε], and the minimum of clipped and unclipped objectives is taken as a conservative policy update.',
    },
  ],

  // Chunk 801: Contrastive Pre-training
  801: [
    {
      codeBlockId: 8001,
      repoName: 'openai/CLIP',
      filePath: 'clip/model.py',
      className: 'CLIP',
      functionName: 'forward',
      startLine: 300,
      endLine: 340,
      codeText: `class CLIP(nn.Module):
    def __init__(self, embed_dim, image_encoder, text_encoder):
        super().__init__()
        self.visual = image_encoder
        self.transformer = text_encoder
        self.logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / 0.07))

    def forward(self, image, text):
        image_features = self.visual(image)
        text_features = self.transformer(text)

        # Normalize features
        image_features = image_features / image_features.norm(dim=1, keepdim=True)
        text_features = text_features / text_features.norm(dim=1, keepdim=True)

        # Cosine similarity as logits
        logit_scale = self.logit_scale.exp()
        logits_per_image = logit_scale * image_features @ text_features.t()
        logits_per_text = logits_per_image.t()

        return logits_per_image, logits_per_text`,
      similarityScore: 0.93,
      githubUrl: 'https://github.com/openai/CLIP/blob/main/clip/model.py#L300',
      explanation: 'CLIP forward pass computes normalized image and text embeddings, then calculates cosine similarity scaled by a learned temperature parameter. The contrastive loss maximizes diagonal entries (correct pairs) in the similarity matrix.',
    },
  ],
};

export function getCodeBlocksForChunk(chunkId: number): CodeBlock[] {
  return mockCodeBlocks[chunkId] || [];
}
