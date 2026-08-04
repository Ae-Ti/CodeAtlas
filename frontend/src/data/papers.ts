export interface Paper {
  paperId: number;
  title: string;
  authors: string;
  task: 'NLP' | 'CV' | 'RL' | 'Multimodal';
  pdfUrl: string;
  abstract: string;
  year: number;
}

export const mockPapers: Paper[] = [
  {
    paperId: 1,
    title: 'Attention Is All You Need',
    authors: 'Vaswani, Shazeer, Parmar et al.',
    task: 'NLP',
    pdfUrl: 'https://arxiv.org/pdf/1706.03762',
    abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    year: 2017,
  },
  {
    paperId: 2,
    title: 'Deep Residual Learning for Image Recognition',
    authors: 'He, Zhang, Ren, Sun',
    task: 'CV',
    pdfUrl: 'https://arxiv.org/pdf/1512.03385',
    abstract: 'We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously. We explicitly reformulate the layers as learning residual functions with reference to the layer inputs.',
    year: 2015,
  },
  {
    paperId: 3,
    title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    authors: 'Devlin, Chang, Lee, Toutanova',
    task: 'NLP',
    pdfUrl: 'https://arxiv.org/pdf/1810.04805',
    abstract: 'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. BERT is designed to pre-train deep bidirectional representations from unlabeled text.',
    year: 2018,
  },
  {
    paperId: 4,
    title: 'Language Models are Unsupervised Multitask Learners',
    authors: 'Radford, Wu, Child, Luan, Amodei, Sutskever',
    task: 'NLP',
    pdfUrl: 'https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf',
    abstract: 'Natural language processing tasks such as question answering, machine translation, and reading comprehension are typically approached with supervised learning on task-specific datasets. We demonstrate that language models begin to learn these tasks without any explicit supervision.',
    year: 2019,
  },
  {
    paperId: 5,
    title: 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale',
    authors: 'Dosovitskiy, Beyer, Kolesnikov et al.',
    task: 'CV',
    pdfUrl: 'https://arxiv.org/pdf/2010.11929',
    abstract: 'While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. We show that a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks.',
    year: 2020,
  },
  {
    paperId: 6,
    title: 'Denoising Diffusion Probabilistic Models',
    authors: 'Ho, Jain, Abbeel',
    task: 'CV',
    pdfUrl: 'https://arxiv.org/pdf/2006.11239',
    abstract: 'We present high quality image synthesis results using diffusion probabilistic models, a class of latent variable models inspired by considerations from nonequilibrium thermodynamics.',
    year: 2020,
  },
  {
    paperId: 7,
    title: 'Proximal Policy Optimization Algorithms',
    authors: 'Schulman, Wolski, Dhariwal, Radford, Klimov',
    task: 'RL',
    pdfUrl: 'https://arxiv.org/pdf/1707.06347',
    abstract: 'We propose a new family of policy gradient methods for reinforcement learning, which alternate between sampling data through interaction with the environment, and optimizing a surrogate objective function using stochastic gradient ascent.',
    year: 2017,
  },
  {
    paperId: 8,
    title: 'Learning Transferable Visual Models From Natural Language Supervision',
    authors: 'Radford, Kim, Hallacy et al.',
    task: 'Multimodal',
    pdfUrl: 'https://arxiv.org/pdf/2103.00020',
    abstract: 'State-of-the-art computer vision systems are trained to predict a fixed set of predetermined object categories. We demonstrate that the simple pre-training task of predicting which caption goes with which image is an efficient and scalable way to learn SOTA image representations.',
    year: 2021,
  },
  {
    paperId: 9,
    title: 'High-Resolution Image Synthesis with Latent Diffusion Models',
    authors: 'Rombach, Blattmann, Lorenz, Esser, Ommer',
    task: 'CV',
    pdfUrl: 'https://arxiv.org/pdf/2112.10752',
    abstract: 'By decomposing the image formation process into a sequential application of denoising autoencoders, diffusion models achieve state-of-the-art synthesis results on image data. We apply them in the latent space of powerful pretrained autoencoders.',
    year: 2022,
  },
  {
    paperId: 10,
    title: 'LLaMA: Open and Efficient Foundation Language Models',
    authors: 'Touvron, Lavril, Izacard et al.',
    task: 'NLP',
    pdfUrl: 'https://arxiv.org/pdf/2302.13971',
    abstract: 'We introduce LLaMA, a collection of foundation language models ranging from 7B to 65B parameters. We train our models on trillions of tokens, and show that it is possible to train state-of-the-art models using publicly available datasets exclusively.',
    year: 2023,
  },
];
