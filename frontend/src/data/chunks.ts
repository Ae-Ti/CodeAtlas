export interface PaperChunk {
  chunkId: number;
  paperId: number;
  sectionTitle: string;
  chunkType: 'method' | 'architecture' | 'training' | 'evaluation';
  chunkText: string;
}

export const mockChunks: PaperChunk[] = [
  // Paper 1: Attention Is All You Need
  {
    chunkId: 101,
    paperId: 1,
    sectionTitle: 'Multi-Head Attention',
    chunkType: 'method',
    chunkText: 'Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions. With a single attention head, averaging inhibits this. We found it beneficial to linearly project the queries, keys and values h times with different learned linear projections.',
  },
  {
    chunkId: 102,
    paperId: 1,
    sectionTitle: 'Scaled Dot-Product Attention',
    chunkType: 'architecture',
    chunkText: 'We compute the attention function on a set of queries simultaneously, packed together into a matrix Q. The keys and values are also packed into matrices K and V. We compute the matrix of outputs as Attention(Q, K, V) = softmax(QK^T / √dk)V.',
  },
  {
    chunkId: 103,
    paperId: 1,
    sectionTitle: 'Positional Encoding',
    chunkType: 'architecture',
    chunkText: 'Since our model contains no recurrence and no convolution, we must inject some information about the relative or absolute position of the tokens in the sequence. We use sine and cosine functions of different frequencies for positional encodings.',
  },
  {
    chunkId: 104,
    paperId: 1,
    sectionTitle: 'Training Regime',
    chunkType: 'training',
    chunkText: 'We trained on the standard WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. We used Adam optimizer with β1=0.9, β2=0.98 and ε=10^-9. We varied the learning rate with warmup_steps=4000.',
  },

  // Paper 2: ResNet
  {
    chunkId: 201,
    paperId: 2,
    sectionTitle: 'Residual Learning',
    chunkType: 'method',
    chunkText: 'Instead of hoping each few stacked layers directly fit a desired underlying mapping, we explicitly let these layers fit a residual mapping F(x) = H(x) - x. The original mapping is recast into F(x) + x. We hypothesize that it is easier to optimize the residual mapping than the original.',
  },
  {
    chunkId: 202,
    paperId: 2,
    sectionTitle: 'Shortcut Connections',
    chunkType: 'architecture',
    chunkText: 'The shortcut connections simply perform identity mapping, and their outputs are added to the outputs of the stacked layers. Identity shortcut connections add neither extra parameter nor computational complexity.',
  },
  {
    chunkId: 203,
    paperId: 2,
    sectionTitle: 'Bottleneck Architecture',
    chunkType: 'architecture',
    chunkText: 'For each residual function F, we use a stack of 3 layers: 1×1, 3×3, and 1×1 convolutions. The 1×1 layers are responsible for reducing and then increasing (restoring) dimensions, leaving the 3×3 layer a bottleneck with smaller input/output dimensions.',
  },

  // Paper 3: BERT
  {
    chunkId: 301,
    paperId: 3,
    sectionTitle: 'Masked Language Model',
    chunkType: 'method',
    chunkText: 'We simply mask some percentage of the input tokens at random, and then predict those masked tokens. We refer to this procedure as a masked LM (MLM). In this case, the final hidden vectors corresponding to the mask tokens are fed into an output softmax over the vocabulary.',
  },
  {
    chunkId: 302,
    paperId: 3,
    sectionTitle: 'Next Sentence Prediction',
    chunkType: 'method',
    chunkText: 'Many important downstream tasks such as QA and NLI are based on understanding the relationship between two sentences. We pre-train for a binarized next sentence prediction task that can be trivially generated from any monolingual corpus.',
  },
  {
    chunkId: 303,
    paperId: 3,
    sectionTitle: 'Fine-tuning Procedure',
    chunkType: 'training',
    chunkText: 'For fine-tuning, the BERT model is first initialized with the pre-trained parameters, and all of the parameters are fine-tuned using labeled data from the downstream tasks. Each downstream task has separate fine-tuned models.',
  },

  // Paper 4: GPT-2
  {
    chunkId: 401,
    paperId: 4,
    sectionTitle: 'Language Modeling Approach',
    chunkType: 'method',
    chunkText: 'Language modeling is able to generate conditional probabilities p(output|input). Since the inputs and outputs for any task can be described with a sequence of symbols, a single model can in principle learn to perform many tasks without needing task-specific architectures.',
  },
  {
    chunkId: 402,
    paperId: 4,
    sectionTitle: 'Model Architecture',
    chunkType: 'architecture',
    chunkText: 'We use a Transformer-based architecture following the details of the OpenAI GPT model with a few modifications. Layer normalization was moved to the input of each sub-block and an additional layer normalization was added after the final self-attention block.',
  },

  // Paper 5: ViT
  {
    chunkId: 501,
    paperId: 5,
    sectionTitle: 'Vision Transformer',
    chunkType: 'architecture',
    chunkText: 'We split an image into fixed-size patches, linearly embed each of them, add position embeddings, and feed the resulting sequence of vectors to a standard Transformer encoder. An extra learnable classification token is prepended to the sequence.',
  },
  {
    chunkId: 502,
    paperId: 5,
    sectionTitle: 'Patch Embedding',
    chunkType: 'method',
    chunkText: 'The standard Transformer receives as input a 1D sequence of token embeddings. To handle 2D images, we reshape the image x ∈ R^(H×W×C) into a sequence of flattened 2D patches x_p ∈ R^(N×(P²·C)), where (H, W) is the resolution and P is the patch size.',
  },

  // Paper 6: DDPM
  {
    chunkId: 601,
    paperId: 6,
    sectionTitle: 'Forward Diffusion Process',
    chunkType: 'method',
    chunkText: 'The forward process is a Markov chain that gradually adds Gaussian noise to the data according to a variance schedule β1,...,βT. Given data point x0, the forward process produces a sequence of noisy samples x1,...,xT.',
  },
  {
    chunkId: 602,
    paperId: 6,
    sectionTitle: 'Reverse Denoising Process',
    chunkType: 'method',
    chunkText: 'The reverse process is a learned Markov chain starting at p(xT) = N(0, I). A neural network is trained to predict the noise added at each step, enabling the generation of samples by iteratively denoising from pure noise.',
  },
  {
    chunkId: 603,
    paperId: 6,
    sectionTitle: 'U-Net Architecture',
    chunkType: 'architecture',
    chunkText: 'We use a U-Net backbone with modifications including group normalization, self-attention at certain resolutions, and sinusoidal position embeddings for the diffusion timestep. The model predicts the noise ε added to the original image.',
  },

  // Paper 7: PPO
  {
    chunkId: 701,
    paperId: 7,
    sectionTitle: 'Clipped Surrogate Objective',
    chunkType: 'method',
    chunkText: 'We propose a clipped surrogate objective which forms a lower bound of the policy performance. Let r_t(θ) denote the probability ratio between old and new policy. The objective clips this ratio to [1-ε, 1+ε], removing the incentive for moving the ratio outside of the interval.',
  },
  {
    chunkId: 702,
    paperId: 7,
    sectionTitle: 'Generalized Advantage Estimation',
    chunkType: 'method',
    chunkText: 'We use generalized advantage estimation for computing advantage estimates. The truncated version of GAE uses a discount factor γ and a parameter λ to control the bias-variance tradeoff of the estimator.',
  },

  // Paper 8: CLIP
  {
    chunkId: 801,
    paperId: 8,
    sectionTitle: 'Contrastive Pre-training',
    chunkType: 'method',
    chunkText: 'CLIP jointly trains an image encoder and a text encoder to predict the correct pairings of a batch of (image, text) training examples. Given a batch of N (image, text) pairs, CLIP is trained to predict which of the N × N possible pairings across a batch actually occurred.',
  },
  {
    chunkId: 802,
    paperId: 8,
    sectionTitle: 'Zero-Shot Transfer',
    chunkType: 'method',
    chunkText: 'For each dataset, we use the names of all the classes in the dataset as the set of potential text pairings and predict the most probable (image, text) pair according to CLIP. This enables zero-shot classification without any dataset-specific training.',
  },

  // Paper 9: Stable Diffusion
  {
    chunkId: 901,
    paperId: 9,
    sectionTitle: 'Latent Diffusion',
    chunkType: 'architecture',
    chunkText: 'Instead of operating in pixel space, latent diffusion models first encode images into a lower-dimensional latent space using a pretrained autoencoder. The diffusion process then operates in this latent space, significantly reducing computational requirements.',
  },
  {
    chunkId: 902,
    paperId: 9,
    sectionTitle: 'Cross-Attention Conditioning',
    chunkType: 'method',
    chunkText: 'To condition the generation on text prompts, we use a cross-attention mechanism that maps the U-Net intermediate representations to the CLIP text encoder output. This enables flexible text-to-image generation with arbitrary text prompts.',
  },

  // Paper 10: LLaMA
  {
    chunkId: 1001,
    paperId: 10,
    sectionTitle: 'Architecture Modifications',
    chunkType: 'architecture',
    chunkText: 'Our architecture is based on the transformer architecture. We leverage various improvements: pre-normalization using RMSNorm, SwiGLU activation function replacing ReLU, and rotary positional embeddings (RoPE) instead of absolute positional embeddings.',
  },
  {
    chunkId: 1002,
    paperId: 10,
    sectionTitle: 'Efficient Training',
    chunkType: 'training',
    chunkText: 'We use an efficient implementation of the causal multi-head attention to reduce memory usage and runtime. We use the xformers library for memory-efficient attention and checkpoint activations of computationally expensive layers.',
  },
  {
    chunkId: 1003,
    paperId: 10,
    sectionTitle: 'Scaling Laws',
    chunkType: 'evaluation',
    chunkText: 'We find that a 13B parameter model trained on 1T tokens outperforms GPT-3 (175B) on most benchmarks. This shows the importance of training data volume and quality over model size, challenging the conventional scaling approach.',
  },
];

export function getChunksByPaperId(paperId: number): PaperChunk[] {
  return mockChunks.filter(c => c.paperId === paperId);
}
