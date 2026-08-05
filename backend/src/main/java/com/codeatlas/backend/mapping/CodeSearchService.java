package com.codeatlas.backend.mapping;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * A 담당 영역(Knowledge Retrieval) — 논문 chunk ↔ 코드 block 매핑 검색.
 * 이 구현체 하나를 세 곳에서 재사용합니다:
 *   1) POST /api/mapping/search ({@link MappingController})
 *   2) FindCodeImplementation MCP tool
 *   3) CurationBatchService (사전계산 배치)
 *
 * chunk의 embedding은 이미 DB에 있으므로 재계산하지 않고 SQL 안에서 그대로 사용합니다.
 */
@Service
public class CodeSearchService implements CodeSearchPort {

    /**
     * REST(/api/mapping/search) 응답에만 필요한 라인 번호·GitHub URL까지 담은 확장 결과.
     * MCP 계약({@code McpDtos.CodeCandidate})은 그대로 두고 여기서만 추가 필드를 노출합니다.
     */
    public record CodeMatch(
            Long codeBlockId,
            String repositoryName,
            String filePath,
            String symbolName,
            String symbolType,
            String parentSymbolName,
            Integer startLine,
            Integer endLine,
            String codeContent,
            double similarityScore,
            String githubUrl
    ) {
        CodeCandidate toCandidate() {
            return new CodeCandidate(codeBlockId, repositoryName, filePath, symbolName,
                    symbolType, parentSymbolName, codeContent, similarityScore);
        }
    }

    // pgvector cosine distance(<=>) 기준 정렬 — similarity = 1 - distance
    private static final String SEARCH_SQL = """
            SELECT cb.id AS code_block_id,
                   r.repository_name,
                   cb.file_path,
                   cb.symbol_name,
                   cb.symbol_type,
                   cb.parent_symbol_name,
                   cb.start_line,
                   cb.end_line,
                   cb.code_content,
                   r.github_url,
                   1 - (cb.embedding <=> pc.embedding) AS similarity_score
            FROM code_blocks cb
            JOIN repositories r ON r.id = cb.repository_id
            CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = ?) pc
            WHERE cb.embedding IS NOT NULL
              AND pc.embedding IS NOT NULL
            ORDER BY cb.embedding <=> pc.embedding
            LIMIT ?
            """;

    private static final RowMapper<CodeMatch> MATCH_MAPPER = (rs, rowNum) -> new CodeMatch(
            rs.getLong("code_block_id"),
            rs.getString("repository_name"),
            rs.getString("file_path"),
            rs.getString("symbol_name"),
            rs.getString("symbol_type"),
            rs.getString("parent_symbol_name"),
            (Integer) rs.getObject("start_line"),
            (Integer) rs.getObject("end_line"),
            rs.getString("code_content"),
            rs.getDouble("similarity_score"),
            rs.getString("github_url")
    );

    private final JdbcTemplate jdbcTemplate;

    public CodeSearchService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public List<CodeCandidate> findImplementations(Long chunkId, int topK) {
        return findMatches(chunkId, topK).stream()
                .map(CodeMatch::toCandidate)
                .toList();
    }

    /** REST 응답용 — MCP 계약에 없는 라인 번호/GitHub URL까지 포함. */
    public List<CodeMatch> findMatches(Long chunkId, int topK) {
        return jdbcTemplate.query(SEARCH_SQL, MATCH_MAPPER, chunkId, topK);
    }
}
