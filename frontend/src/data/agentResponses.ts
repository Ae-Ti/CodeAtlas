export interface McpTool {
  toolName: string;
  status: 'pending' | 'running' | 'done' | 'error';
  latencyMs: number;
  description: string;
}

export interface TaccResult {
  initialContexts: number;
  removedContexts: number;
  selectedContexts: number;
}

export interface Nl2SqlResult {
  naturalQuery: string;
  generatedSql: string;
  results: Record<string, string | number>[];
}

export interface AgentResponse {
  query: string;
  mcpTools: McpTool[];
  tacc: TaccResult;
  nl2sql?: Nl2SqlResult;
  aiResponse: string;
}

export const mockAgentResponses: Record<string, AgentResponse> = {
  'How is multi-head attention implemented in open-source code?': {
    query: 'How is multi-head attention implemented in open-source code?',
    mcpTools: [
      { toolName: 'SearchPaperChunk', status: 'done', latencyMs: 410, description: 'Searching paper chunks for "multi-head attention"' },
      { toolName: 'FindCodeImplementation', status: 'done', latencyMs: 620, description: 'Finding code implementations matching attention chunks' },
      { toolName: 'QueryMetadataSQL', status: 'done', latencyMs: 180, description: 'Querying repository metadata' },
      { toolName: 'CurateContext', status: 'done', latencyMs: 95, description: 'Selecting optimal context for response generation' },
    ],
    tacc: { initialContexts: 24, removedContexts: 19, selectedContexts: 5 },
    nl2sql: {
      naturalQuery: 'Find repositories that implement attention mechanisms',
      generatedSql: "SELECT r.repo_name, r.stars, COUNT(cb.code_block_id) as impl_count\nFROM repositories r\nJOIN code_blocks cb ON r.repo_id = cb.repo_id\nWHERE cb.function_name ILIKE '%attention%'\nGROUP BY r.repo_name, r.stars\nORDER BY r.stars DESC\nLIMIT 10;",
      results: [
        { repo_name: 'huggingface/transformers', stars: 125000, impl_count: 47 },
        { repo_name: 'pytorch/pytorch', stars: 78000, impl_count: 23 },
        { repo_name: 'annotated-transformer', stars: 5200, impl_count: 8 },
        { repo_name: 'google/vision_transformer', stars: 8900, impl_count: 12 },
      ],
    },
    aiResponse: `## Multi-Head Attention Implementations

Based on the analysis of **3 paper chunks** and **5 code repositories**, here are the key findings:

### Core Pattern
The multi-head attention mechanism from "Attention Is All You Need" (Vaswani et al., 2017) follows a consistent implementation pattern across repositories:

1. **Linear Projections**: Q, K, V are projected through separate linear layers (or a combined weight matrix)
2. **Head Splitting**: The projected tensors are reshaped to separate attention heads
3. **Scaled Dot-Product**: \`softmax(QK^T / √dk) × V\` is computed per head
4. **Concatenation**: Head outputs are concatenated and projected through a final linear layer

### Top Implementation
The **annotated-transformer** repository provides the clearest reference implementation with a **0.92 similarity score** to the paper's description. The \`MultiHeadedAttention.forward()\` method follows the paper's notation almost exactly.

### Key Variations
- **PyTorch native**: Uses combined \`in_proj_weight\` for efficiency
- **HuggingFace**: Separate Q, K, V projections for modularity
- **Flash Attention**: Memory-efficient variant with IO-awareness`,
  },

  'What papers describe residual connections and how are they coded?': {
    query: 'What papers describe residual connections and how are they coded?',
    mcpTools: [
      { toolName: 'SearchPaperChunk', status: 'done', latencyMs: 380, description: 'Searching paper chunks for "residual connections"' },
      { toolName: 'FindCodeImplementation', status: 'done', latencyMs: 550, description: 'Finding code implementations of residual blocks' },
      { toolName: 'QueryMetadataSQL', status: 'done', latencyMs: 150, description: 'Querying paper metadata' },
      { toolName: 'CurateContext', status: 'done', latencyMs: 88, description: 'Curating final context' },
    ],
    tacc: { initialContexts: 18, removedContexts: 13, selectedContexts: 5 },
    aiResponse: `## Residual Connections: Paper to Code

### Paper: Deep Residual Learning (He et al., 2015)
The key insight is reformulating layers to learn **residual functions** F(x) = H(x) - x, making the actual computation F(x) + x via shortcut connections.

### Implementation in torchvision
The \`BasicBlock\` class in torchvision/models/resnet.py implements the core idea with a single line:
\`\`\`python
out += identity  # This is the residual connection!
\`\`\`

### Two Variants
1. **BasicBlock**: Two 3×3 conv layers + identity shortcut (ResNet-18/34)
2. **Bottleneck**: 1×1 → 3×3 → 1×1 conv layers + identity shortcut (ResNet-50/101/152)

The bottleneck design reduces computational cost while maintaining representational power. Both variants share the same residual connection pattern.`,
  },

  'Show me diffusion model implementations': {
    query: 'Show me diffusion model implementations',
    mcpTools: [
      { toolName: 'SearchPaperChunk', status: 'done', latencyMs: 450, description: 'Searching chunks for diffusion models' },
      { toolName: 'FindCodeImplementation', status: 'done', latencyMs: 700, description: 'Finding diffusion implementations' },
      { toolName: 'CurateContext', status: 'done', latencyMs: 110, description: 'Selecting best diffusion contexts' },
    ],
    tacc: { initialContexts: 20, removedContexts: 15, selectedContexts: 5 },
    aiResponse: `## Diffusion Model Implementations

### DDPM (Ho et al., 2020)
The forward diffusion process \`q_sample\` adds noise following:
\`\`\`
x_t = √ᾱt · x₀ + √(1-ᾱt) · ε
\`\`\`

The implementation in **hojonathanho/diffusion** directly corresponds to this formula, using precomputed \`sqrt_alphas_cumprod\` and \`sqrt_one_minus_alphas_cumprod\` coefficients.

### Stable Diffusion (Rombach et al., 2022)
Latent Diffusion Models operate in compressed latent space instead of pixel space, dramatically reducing computational cost. The key innovation is applying the diffusion process after VAE encoding.

### Key Components
- **Noise Schedule**: Linear or cosine beta schedule
- **U-Net**: Predicts noise ε at each timestep
- **Cross-Attention**: Enables text conditioning (Stable Diffusion)`,
  },
};

export const exampleQueries = Object.keys(mockAgentResponses);
