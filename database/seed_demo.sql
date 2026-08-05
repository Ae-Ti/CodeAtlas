/* =========================================================
   Script-4. 데모용 seed 데이터 (임시)
   Script-2.sql → Script-3_pgvector.sql 다음에 적용

   ⚠️ 이 파일은 A의 실제 큐레이션 데이터(논문 10건)가 준비되기 전까지
      백엔드를 혼자 띄워 검증하기 위한 **임시 데이터**입니다.
      기획서 §2의 `seed_dump.sql`(클론 시 동일 DB 재현용, 운영규정 제10조①)이
      나오면 이 파일은 삭제하고 그쪽으로 대체하세요.

   embedding 컬럼은 비워둡니다. 백엔드를 아래처럼 띄우면 채워집니다.
      CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
   (A의 Python 파이프라인이 Ollama /api/embed로 채우는 것과 동일한
    nomic-embed-text 768차원 벡터를 만듭니다)
   ========================================================= */

INSERT INTO papers (id, title, abstract, arxiv_id, pdf_url, published_date, authors, processing_status) VALUES
  (1, 'Attention Is All You Need',
      'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.',
      '1706.03762', 'https://arxiv.org/pdf/1706.03762', DATE '2017-06-12',
      '[{"name": "Ashish Vaswani"}, {"name": "Noam Shazeer"}, {"name": "Niki Parmar"}]'::jsonb, 'COMPLETED'),
  (2, 'Deep Residual Learning for Image Recognition',
      'Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.',
      '1512.03385', 'https://arxiv.org/pdf/1512.03385', DATE '2015-12-10',
      '[{"name": "Kaiming He"}, {"name": "Xiangyu Zhang"}, {"name": "Shaoqing Ren"}]'::jsonb, 'COMPLETED'),
  (3, 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
      'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.',
      '1810.04805', 'https://arxiv.org/pdf/1810.04805', DATE '2018-10-11',
      '[{"name": "Jacob Devlin"}, {"name": "Ming-Wei Chang"}]'::jsonb, 'COMPLETED');

INSERT INTO paper_chunks (id, paper_id, section_title, subsection_title, chunk_index, content, page_start, page_end, token_count) VALUES
  (101, 1, 'Multi-Head Attention', NULL, 0,
   'Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions. Instead of performing a single attention function with d_model-dimensional keys, values and queries, we linearly project the queries, keys and values h times with different, learned linear projections. On each of these projected versions we then perform the attention function in parallel, yielding d_v-dimensional output values. These are concatenated and once again projected, resulting in the final values.',
   4, 5, 96),
  (102, 1, 'Scaled Dot-Product Attention', NULL, 1,
   'We call our particular attention Scaled Dot-Product Attention. The input consists of queries and keys of dimension d_k, and values of dimension d_v. We compute the dot products of the query with all keys, divide each by sqrt(d_k), and apply a softmax function to obtain the weights on the values. We suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients, so we scale by 1/sqrt(d_k).',
   3, 4, 104),
  (103, 1, 'Position-wise Feed-Forward Networks', NULL, 2,
   'In addition to attention sub-layers, each of the layers in our encoder and decoder contains a fully connected feed-forward network, which is applied to each position separately and identically. This consists of two linear transformations with a ReLU activation in between. While the linear transformations are the same across different positions, they use different parameters from layer to layer.',
   5, 5, 71),
  (104, 1, 'Positional Encoding', NULL, 3,
   'Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute position of the tokens in the sequence. To this end, we add positional encodings to the input embeddings, using sine and cosine functions of different frequencies.',
   5, 6, 68),
  (201, 2, 'Residual Learning', NULL, 0,
   'We explicitly reformulate the layers as learning residual functions with reference to the layer inputs, instead of learning unreferenced functions. We hypothesize that it is easier to optimize the residual mapping than to optimize the original, unreferenced mapping. The formulation of F(x) + x can be realized by feedforward neural networks with shortcut connections that perform identity mapping.',
   2, 3, 79),
  (301, 3, 'Masked Language Model', NULL, 0,
   'In order to train a deep bidirectional representation, we simply mask some percentage of the input tokens at random, and then predict those masked tokens. We refer to this procedure as a masked LM. In all of our experiments we mask 15% of all WordPiece tokens in each sequence at random.',
   4, 4, 62);

INSERT INTO repositories (id, github_url, owner_name, repository_name, default_branch, license_name, primary_language, star_count, processing_status) VALUES
  (11, 'https://github.com/harvardnlp/annotated-transformer', 'harvardnlp',      'annotated-transformer', 'master', 'MIT',        'Python',   6200, 'COMPLETED'),
  (12, 'https://github.com/huggingface/transformers',        'huggingface',     'transformers',          'main',   'Apache-2.0', 'Python', 142000, 'COMPLETED'),
  (13, 'https://github.com/pytorch/vision',                  'pytorch',         'vision',                'main',   'BSD-3-Clause', 'Python', 17000, 'COMPLETED'),
  (14, 'https://github.com/google-research/bert',            'google-research', 'bert',                  'master', 'Apache-2.0', 'Python',  39000, 'COMPLETED');

INSERT INTO paper_repositories (paper_id, repository_id, relation_type, is_primary) VALUES
  (1, 11, 'COMMUNITY', TRUE),
  (1, 12, 'COMMUNITY', FALSE),
  (2, 13, 'COMMUNITY', TRUE),
  (3, 14, 'OFFICIAL',  TRUE);

INSERT INTO code_blocks (id, repository_id, file_path, symbol_name, symbol_type, programming_language, start_line, end_line, code_content, parent_symbol_name) VALUES
  (501, 11, 'model/attention.py', 'forward', 'METHOD', 'Python', 42, 89,
   'def forward(self, query, key, value, mask=None):\n    "Implements Figure 2"\n    if mask is not None:\n        mask = mask.unsqueeze(1)\n    nbatches = query.size(0)\n\n    query, key, value = [\n        lin(x).view(nbatches, -1, self.h, self.d_k).transpose(1, 2)\n        for lin, x in zip(self.linears, (query, key, value))\n    ]\n\n    x, self.attn = attention(query, key, value, mask=mask, dropout=self.dropout)\n\n    x = x.transpose(1, 2).contiguous().view(nbatches, -1, self.h * self.d_k)\n    return self.linears[-1](x)',
   'MultiHeadedAttention'),
  (502, 11, 'model/attention.py', 'attention', 'FUNCTION', 'Python', 12, 24,
   'def attention(query, key, value, mask=None, dropout=None):\n    "Compute Scaled Dot Product Attention"\n    d_k = query.size(-1)\n    scores = torch.matmul(query, key.transpose(-2, -1)) / math.sqrt(d_k)\n    if mask is not None:\n        scores = scores.masked_fill(mask == 0, -1e9)\n    p_attn = scores.softmax(dim=-1)\n    if dropout is not None:\n        p_attn = dropout(p_attn)\n    return torch.matmul(p_attn, value), p_attn',
   NULL),
  (503, 11, 'model/feed_forward.py', 'forward', 'METHOD', 'Python', 8, 16,
   'def forward(self, x):\n    return self.w_2(self.dropout(self.w_1(x).relu()))',
   'PositionwiseFeedForward'),
  (504, 11, 'model/embeddings.py', 'forward', 'METHOD', 'Python', 20, 34,
   'def forward(self, x):\n    x = x + self.pe[:, : x.size(1)].requires_grad_(False)\n    return self.dropout(x)',
   'PositionalEncoding'),
  (505, 12, 'src/transformers/models/bert/modeling_bert.py', 'forward', 'METHOD', 'Python', 240, 310,
   'def forward(self, hidden_states, attention_mask=None, head_mask=None):\n    query_layer = self.transpose_for_scores(self.query(hidden_states))\n    key_layer = self.transpose_for_scores(self.key(hidden_states))\n    value_layer = self.transpose_for_scores(self.value(hidden_states))\n\n    attention_scores = torch.matmul(query_layer, key_layer.transpose(-1, -2))\n    attention_scores = attention_scores / math.sqrt(self.attention_head_size)\n    if attention_mask is not None:\n        attention_scores = attention_scores + attention_mask\n\n    attention_probs = nn.functional.softmax(attention_scores, dim=-1)\n    attention_probs = self.dropout(attention_probs)\n    context_layer = torch.matmul(attention_probs, value_layer)\n    return context_layer',
   'BertSelfAttention'),
  (506, 13, 'torchvision/models/resnet.py', 'forward', 'METHOD', 'Python', 60, 84,
   'def forward(self, x):\n    identity = x\n\n    out = self.conv1(x)\n    out = self.bn1(out)\n    out = self.relu(out)\n\n    out = self.conv2(out)\n    out = self.bn2(out)\n\n    if self.downsample is not None:\n        identity = self.downsample(x)\n\n    out += identity\n    out = self.relu(out)\n    return out',
   'BasicBlock'),
  (507, 14, 'run_pretraining.py', 'get_masked_lm_output', 'FUNCTION', 'Python', 240, 279,
   'def get_masked_lm_output(bert_config, input_tensor, output_weights, positions, label_ids, label_weights):\n  """Get loss and log probs for the masked LM."""\n  input_tensor = gather_indexes(input_tensor, positions)\n  logits = tf.matmul(input_tensor, output_weights, transpose_b=True)\n  log_probs = tf.nn.log_softmax(logits, axis=-1)\n  per_example_loss = -tf.reduce_sum(log_probs * one_hot_labels, axis=[-1])\n  return (loss, per_example_loss, log_probs)',
   NULL);

/* IDENTITY 시퀀스를 수동 삽입한 최대값 뒤로 이동 (이후 INSERT에서 PK 충돌 방지) */
SELECT setval(pg_get_serial_sequence('papers',       'id'), (SELECT max(id) FROM papers));
SELECT setval(pg_get_serial_sequence('paper_chunks', 'id'), (SELECT max(id) FROM paper_chunks));
SELECT setval(pg_get_serial_sequence('repositories', 'id'), (SELECT max(id) FROM repositories));
SELECT setval(pg_get_serial_sequence('code_blocks',  'id'), (SELECT max(id) FROM code_blocks));
