package com.codeatlas.backend.agent;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.PrecomputedMapping;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MappingReadPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * B 구현. paper_code_mappings + code_blocks + repositories를 조인해서
 * CurationBatchService가 미리 계산해둔 결과를 그대로 읽어옵니다.
 * (요청마다 Ollama를 부르지 않아서 빠르고, 발표 데모 중 실패 리스크가 없음)
 */
@Service
public class MappingReadService implements MappingReadPort {

    private final JdbcTemplate jdbcTemplate;

    public MappingReadService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public List<PrecomputedMapping> findMappings(Long chunkId, int topK) {
        String sql = """
                SELECT cb.id AS code_block_id,
                       r.repository_name,
                       cb.file_path,
                       cb.symbol_name,
                       cb.symbol_type,
                       cb.parent_symbol_name,
                       cb.code_content,
                       m.similarity_score,
                       m.mapping_reason,
                       m.explanation,
                       m.is_verified
                FROM paper_code_mappings m
                JOIN code_blocks cb ON cb.id = m.code_block_id
                JOIN repositories r ON r.id = cb.repository_id
                WHERE m.paper_chunk_id = ?
                ORDER BY m.similarity_score DESC NULLS LAST
                LIMIT ?
                """;

        return jdbcTemplate.query(sql,
                (rs, rowNum) -> new PrecomputedMapping(
                        new CodeCandidate(
                                rs.getLong("code_block_id"),
                                rs.getString("repository_name"),
                                rs.getString("file_path"),
                                rs.getString("symbol_name"),
                                rs.getString("symbol_type"),
                                rs.getString("parent_symbol_name"),
                                rs.getString("code_content"),
                                rs.getObject("similarity_score") != null ? rs.getDouble("similarity_score") : 0.0
                        ),
                        rs.getString("mapping_reason"),
                        rs.getString("explanation"),
                        rs.getBoolean("is_verified")
                ),
                chunkId, topK);
    }
}
