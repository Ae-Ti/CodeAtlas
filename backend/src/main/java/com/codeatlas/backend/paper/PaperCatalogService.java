package com.codeatlas.backend.paper;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import java.sql.Array;
import java.time.LocalDate;
import java.util.List;

/** 논문 목록/chunk 목록 조회 (검색·임베딩이 필요 없는 단순 read) — Script-2.sql 스키마 기준. */
@Service
public class PaperCatalogService {

    public record PaperSummary(
            Long paperId,
            String title,
            List<String> authors,
            String arxivId,
            String pdfUrl,
            LocalDate publishedDate,
            String processingStatus
    ) {}

    public record ChunkSummary(
            Long chunkId,
            String sectionTitle,
            String subsectionTitle,
            int chunkIndex,
            String chunkText
    ) {}

    /**
     * authors는 JSONB 배열 {@code [{"name": "..."}]}입니다.
     * 프론트가 쓰기 쉽게 이름 목록으로 펴서 내보내되, 변환은 Postgres에서 처리합니다
     * (Spring Boot 4는 Jackson 3(tools.jackson)를 쓰므로 애플리케이션에서 JSON을 직접
     *  파싱하면 Jackson 버전에 불필요하게 결합됩니다).
     * jsonb_typeof 가드는 파이프라인이 배열이 아닌 값을 넣었을 때 목록 조회 전체가
     * 500으로 죽는 것을 막아줍니다.
     */
    private static final String PAPER_SELECT = """
            SELECT p.id, p.title, p.arxiv_id, p.pdf_url, p.published_date, p.processing_status,
                   COALESCE(
                       CASE WHEN jsonb_typeof(p.authors) = 'array' THEN (
                           SELECT array_agg(a->>'name' ORDER BY ord)
                           FROM jsonb_array_elements(p.authors) WITH ORDINALITY AS t(a, ord)
                           WHERE a->>'name' IS NOT NULL
                       ) END,
                       ARRAY[]::text[]
                   ) AS author_names
            FROM papers p
            ORDER BY p.id
            """;

    private static final RowMapper<PaperSummary> PAPER_MAPPER = (rs, rowNum) -> new PaperSummary(
            rs.getLong("id"),
            rs.getString("title"),
            toList(rs.getArray("author_names")),
            rs.getString("arxiv_id"),
            rs.getString("pdf_url"),
            rs.getObject("published_date", LocalDate.class),
            rs.getString("processing_status")
    );

    private static final RowMapper<ChunkSummary> CHUNK_MAPPER = (rs, rowNum) -> new ChunkSummary(
            rs.getLong("id"),
            rs.getString("section_title"),
            rs.getString("subsection_title"),
            rs.getInt("chunk_index"),
            rs.getString("content")
    );

    private static List<String> toList(Array sqlArray) throws java.sql.SQLException {
        if (sqlArray == null) {
            return List.of();
        }
        return List.of((String[]) sqlArray.getArray());
    }

    private final JdbcTemplate jdbcTemplate;

    public PaperCatalogService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<PaperSummary> findAllPapers() {
        return jdbcTemplate.query(PAPER_SELECT, PAPER_MAPPER);
    }

    public List<ChunkSummary> findChunks(Long paperId) {
        return jdbcTemplate.query("""
                SELECT id, section_title, subsection_title, chunk_index, content
                FROM paper_chunks
                WHERE paper_id = ?
                ORDER BY chunk_index, id
                """, CHUNK_MAPPER, paperId);
    }

    public boolean paperExists(Long paperId) {
        Integer count = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM papers WHERE id = ?", Integer.class, paperId);
        return count != null && count > 0;
    }
}
