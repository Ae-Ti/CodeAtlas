package com.codeatlas.backend.paper;

import com.codeatlas.backend.embedding.VectorSupport;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * A 담당 영역(Knowledge Retrieval) — Script-2.sql + Script-3_pgvector.sql 스키마 기준 구현체.
 * &#64;Service 이므로 B의 SearchPaperChunkTool / AgentQueryController에 자동 주입됩니다.
 *
 * ⚠️ EmbeddingModel은 반드시 A의 Python 파이프라인(offline 임베딩 생성)과 동일한 모델
 *    (nomic-embed-text)을 가리켜야 합니다. 모델이 다르면 벡터 공간이 달라져
 *    유사도 검색 결과가 무의미해집니다.
 *    (application-ai.yml의 spring.ai.ollama.embedding.options.model 참고)
 */
@Service
public class PaperChunkSearchService implements PaperChunkSearchPort {

    private static final RowMapper<ChunkResult> CHUNK_MAPPER = (rs, rowNum) -> new ChunkResult(
            rs.getLong("id"),
            rs.getLong("paper_id"),
            rs.getString("section_title"),
            rs.getString("content"),
            rs.getDouble("score")
    );

    private final JdbcTemplate jdbcTemplate;
    private final EmbeddingModel embeddingModel;

    public PaperChunkSearchService(JdbcTemplate jdbcTemplate, EmbeddingModel embeddingModel) {
        this.jdbcTemplate = jdbcTemplate;
        this.embeddingModel = embeddingModel;
    }

    @Override
    public List<ChunkResult> search(String queryText, Long paperId, int topK) {
        // JDBC 드라이버가 vector 타입을 모르므로 리터럴 문자열 + ?::vector 캐스팅으로 넘깁니다.
        String queryVector = VectorSupport.toVectorLiteral(embeddingModel.embed(queryText));

        StringBuilder sql = new StringBuilder("""
                SELECT id, paper_id, section_title, content,
                       1 - (embedding <=> ?::vector) AS score
                FROM paper_chunks
                WHERE embedding IS NOT NULL
                """);
        List<Object> params = new ArrayList<>();
        params.add(queryVector);

        if (paperId != null) {
            sql.append("  AND paper_id = ?\n");
            params.add(paperId);
        }
        sql.append("ORDER BY embedding <=> ?::vector\nLIMIT ?");
        params.add(queryVector);
        params.add(topK);

        return jdbcTemplate.query(sql.toString(), CHUNK_MAPPER, params.toArray());
    }

    @Override
    public Optional<ChunkResult> getChunkById(Long paperId, Long chunkId) {
        // 대상 chunk 자신을 꺼내오는 것이므로 유사도 계산 없이 score = 1.0 고정.
        // paperId는 선택 조건입니다 — MCP tool 호출 등 paperId 없이 chunkId만 아는 경로가 있습니다.
        StringBuilder sql = new StringBuilder("""
                SELECT id, paper_id, section_title, content, 1.0 AS score
                FROM paper_chunks
                WHERE id = ?
                """);
        List<Object> params = new ArrayList<>();
        params.add(chunkId);

        if (paperId != null) {
            sql.append("  AND paper_id = ?");
            params.add(paperId);
        }

        return jdbcTemplate.query(sql.toString(), CHUNK_MAPPER, params.toArray())
                .stream()
                .findFirst();
    }
}
