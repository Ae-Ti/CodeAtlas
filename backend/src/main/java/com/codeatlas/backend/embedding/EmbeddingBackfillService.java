package com.codeatlas.backend.embedding;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * embedding 이 비어 있는 행을 Ollama(nomic-embed-text)로 채운다.
 *
 * 호출처 둘: 기동 시 스위치({@link EmbeddingBackfillRunner}) 와 업로드 작업
 * (UploadJobService — 적재 직후 새 논문의 chunk·code block 만 NULL 이므로 그것만 채워진다).
 *
 * 코드 block은 code_content만 넣으면 논문 문장과 임베딩 공간이 잘 맞지 않아
 * file_path + 상위 심볼명 + 심볼명을 함께 이어붙여 임베딩합니다.
 *
 * ⚠️ A의 Python 파이프라인도 **같은 방식으로 이어붙여야** 합니다. 조합이 다르면
 *    같은 모델을 써도 검색 품질이 달라집니다. demo seed 6쌍 기준 비교 결과:
 *      상위심볼+심볼+심볼타입+코드      → Top-1 3/6
 *      상위심볼+심볼+코드                → Top-1 4/6
 *      file_path+상위심볼+심볼+코드      → Top-1 5/6  ← 채택
 *    표본이 6쌍뿐이라 잠정 선택입니다. 로드맵 2주차의 정답셋(30쌍)으로
 *    A가 Top-1/3·MRR을 다시 측정해 확정해 주세요.
 *
 * embedding_model 컬럼은 Script-3의 DEFAULT('nomic-embed-text')를 그대로 씁니다 —
 * 다른 모델로 바꾸면 이 클래스도 함께 수정해야 합니다.
 */
@Service
public class EmbeddingBackfillService {

    private static final Logger log = LoggerFactory.getLogger(EmbeddingBackfillService.class);

    private final JdbcTemplate jdbcTemplate;
    private final EmbeddingModel embeddingModel;

    public EmbeddingBackfillService(JdbcTemplate jdbcTemplate, EmbeddingModel embeddingModel) {
        this.jdbcTemplate = jdbcTemplate;
        this.embeddingModel = embeddingModel;
    }

    public record BackfillResult(int chunks, int codeBlocks) {}

    /** embedding 이 NULL 인 paper_chunks · code_blocks 를 전부 채운다. 채운 행 수를 돌려준다. */
    public synchronized BackfillResult backfillPending() {
        return new BackfillResult(backfillChunks(), backfillCodeBlocks());
    }

    private int backfillChunks() {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList("""
                SELECT id, section_title, subsection_title, content
                FROM paper_chunks
                WHERE embedding IS NULL
                ORDER BY id
                """);
        if (rows.isEmpty()) {
            return 0;
        }
        log.info("paper_chunks embedding backfill 시작: {}건", rows.size());

        for (Map<String, Object> row : rows) {
            String text = join(
                    (String) row.get("section_title"),
                    (String) row.get("subsection_title"),
                    (String) row.get("content"));
            jdbcTemplate.update(
                    "UPDATE paper_chunks SET embedding = ?::vector WHERE id = ?",
                    VectorSupport.toVectorLiteral(embeddingModel.embed(text)),
                    row.get("id"));
        }
        log.info("paper_chunks embedding backfill 완료");
        return rows.size();
    }

    private int backfillCodeBlocks() {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList("""
                SELECT id, file_path, parent_symbol_name, symbol_name, code_content
                FROM code_blocks
                WHERE embedding IS NULL
                ORDER BY id
                """);
        if (rows.isEmpty()) {
            return 0;
        }
        log.info("code_blocks embedding backfill 시작: {}건", rows.size());

        for (Map<String, Object> row : rows) {
            String text = join(
                    (String) row.get("file_path"),
                    (String) row.get("parent_symbol_name"),
                    (String) row.get("symbol_name"),
                    (String) row.get("code_content"));
            jdbcTemplate.update(
                    "UPDATE code_blocks SET embedding = ?::vector WHERE id = ?",
                    VectorSupport.toVectorLiteral(embeddingModel.embed(text)),
                    row.get("id"));
        }
        log.info("code_blocks embedding backfill 완료");
        return rows.size();
    }

    private static String join(String... parts) {
        StringBuilder sb = new StringBuilder();
        for (String part : parts) {
            if (part != null && !part.isBlank()) {
                if (!sb.isEmpty()) {
                    sb.append('\n');
                }
                sb.append(part);
            }
        }
        return sb.toString();
    }
}
