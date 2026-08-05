/* =========================================================
   Script-3. pgvector 확장 + embedding 컬럼 추가
   Script-2.sql 실행 이후에 적용할 것
   ========================================================= */

CREATE EXTENSION IF NOT EXISTS vector;

/* nomic-embed-text(Ollama, 768차원) 기준.
   다른 임베딩 모델로 바꾸면 이 숫자도 반드시 같이 바꿔야 합니다. */

ALTER TABLE paper_chunks
    ADD COLUMN embedding vector(768),
    ADD COLUMN embedding_model VARCHAR(100) NOT NULL DEFAULT 'nomic-embed-text';

ALTER TABLE code_blocks
    ADD COLUMN embedding vector(768),
    ADD COLUMN embedding_model VARCHAR(100) NOT NULL DEFAULT 'nomic-embed-text';

/* 소규모 카탈로그(10~20건)라 인덱스 없어도 성능엔 문제 없지만,
   나중에 카탈로그가 커질 걸 대비해 HNSW 인덱스 미리 추가.
   (pgvector 0.5.0+ 필요, ivfflat과 달리 별도 학습 데이터 없이 바로 사용 가능) */

CREATE INDEX idx_paper_chunks_embedding
    ON paper_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_code_blocks_embedding
    ON code_blocks USING hnsw (embedding vector_cosine_ops);


/* 확인용 */
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name IN ('paper_chunks', 'code_blocks') AND column_name LIKE '%embedding%';
