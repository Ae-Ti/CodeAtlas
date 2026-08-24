package com.codeatlas.backend.agent;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 대시보드/그래프 화면용 읽기 전용 집계 API.
 * paper_code_mappings(사전계산 결과)를 화면 단위로 펼쳐 보여주는 용도라 agent 패키지에 둡니다.
 */
@RestController
public class OverviewController {

    public record Stats(int papers, int chunks, int repositories, int codeBlocks, int mappings) {}

    /** 논문 chunk ↔ 코드 매핑 한 줄. 대시보드 카드와 React Flow 그래프가 같이 씁니다. */
    public record MappingRow(
            Long paperId,
            String paperTitle,
            Long chunkId,
            String sectionTitle,
            Long codeBlockId,
            String repositoryName,
            String filePath,
            String symbolName,
            String parentSymbolName,
            double similarityScore,
            boolean verified
    ) {}

    private static final RowMapper<MappingRow> MAPPING_MAPPER = (rs, rowNum) -> new MappingRow(
            rs.getLong("paper_id"),
            rs.getString("title"),
            rs.getLong("paper_chunk_id"),
            rs.getString("section_title"),
            rs.getLong("code_block_id"),
            rs.getString("repository_name"),
            rs.getString("file_path"),
            rs.getString("symbol_name"),
            rs.getString("parent_symbol_name"),
            rs.getObject("similarity_score") != null ? rs.getDouble("similarity_score") : 0.0,
            rs.getBoolean("is_verified")
    );

    private final JdbcTemplate jdbcTemplate;

    public OverviewController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping("/api/stats")
    public Stats stats() {
        Map<String, Object> row = jdbcTemplate.queryForMap("""
                SELECT (SELECT count(*) FROM papers)              AS papers,
                       (SELECT count(*) FROM paper_chunks)        AS chunks,
                       (SELECT count(*) FROM repositories)        AS repositories,
                       (SELECT count(*) FROM code_blocks)         AS code_blocks,
                       (SELECT count(*) FROM paper_code_mappings) AS mappings
                """);
        return new Stats(
                toInt(row.get("papers")),
                toInt(row.get("chunks")),
                toInt(row.get("repositories")),
                toInt(row.get("code_blocks")),
                toInt(row.get("mappings")));
    }

    /**
     * 사전계산된 매핑을 논문별로 고르게 섞어서 반환합니다. limit은 그래프가 감당할 수 있는 범위로 제한합니다.
     * 전체 유사도순으로만 자르면 상위권이 소수 논문에 쏠려(실측: 상위 60건이 9편 중 4편)
     * 나머지 논문이 그래프·대시보드에 아예 등장하지 않는다 — 논문별 순위를 1차 정렬로 두어
     * 모든 논문의 1위 매핑이 어떤 논문의 2위보다 먼저 나오게 한다.
     */
    @GetMapping("/api/mappings")
    public List<MappingRow> mappings(@RequestParam(defaultValue = "50") int limit) {
        int bounded = Math.max(1, Math.min(limit, 500));
        return jdbcTemplate.query("""
                SELECT paper_id, title, paper_chunk_id, section_title,
                       code_block_id, repository_name, file_path,
                       symbol_name, parent_symbol_name, similarity_score, is_verified
                FROM (
                    SELECT p.id AS paper_id, p.title,
                           m.paper_chunk_id, pc.section_title,
                           m.code_block_id, r.repository_name, cb.file_path,
                           cb.symbol_name, cb.parent_symbol_name,
                           m.similarity_score, m.is_verified,
                           row_number() OVER (PARTITION BY p.id
                                              ORDER BY m.similarity_score DESC NULLS LAST,
                                                       m.paper_chunk_id) AS paper_rank
                    FROM paper_code_mappings m
                    JOIN paper_chunks pc ON pc.id = m.paper_chunk_id
                    JOIN papers p        ON p.id  = pc.paper_id
                    JOIN code_blocks cb  ON cb.id = m.code_block_id
                    JOIN repositories r  ON r.id  = cb.repository_id
                ) ranked
                ORDER BY paper_rank, similarity_score DESC NULLS LAST, paper_chunk_id
                LIMIT ?
                """, MAPPING_MAPPER, bounded);
    }

    private static int toInt(Object value) {
        return (value instanceof Number n) ? n.intValue() : 0;
    }
}
