package com.codeatlas.backend.agent;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;

/**
 * 큐레이션 결과(paper_code_mappings) 저장을 한 곳으로 모은 서비스.
 * CurationBatchService(배치)와 AgentQueryController(라이브 폴백 캐싱)가 같이 씁니다 —
 * 저장 규칙(MANUAL 보호, 1위에만 explanation, 점수 clamp)이 갈라지면 안 되기 때문입니다.
 *
 * ⚠️ 호출자 책임: 폴백(paperScoped=false) 결과를 여기로 넘기면 안 됩니다.
 * 다른 논문의 코드가 mapping_method='AI'로 영구히 남고, paper_code_mappings에는
 * 화면에서 걸러낼 표시를 남길 컬럼이 없습니다. 저장 전 반드시
 * {@code findImplementationsScoped(...).paperScoped()}를 확인하세요.
 */
@Service
public class MappingPersistService {

    private final JdbcTemplate jdbcTemplate;
    private final TransactionTemplate transactionTemplate;

    public MappingPersistService(JdbcTemplate jdbcTemplate, PlatformTransactionManager transactionManager) {
        this.jdbcTemplate = jdbcTemplate;
        this.transactionTemplate = new TransactionTemplate(transactionManager);
    }

    /**
     * chunk 1건의 큐레이션 결과를 하나의 트랜잭션으로 저장합니다.
     * 반환값은 저장(또는 갱신)한 매핑 행 수.
     */
    public int persistCurated(Long chunkId, CuratedContext curated) {
        Integer created = transactionTemplate.execute(status -> doPersist(chunkId, curated));
        return (created != null) ? created : 0;
    }

    private int doPersist(Long chunkId, CuratedContext curated) {
        // 배치 시점의 TACC 수치를 사람이 읽을 수 있는 형태로 남깁니다.
        // 사전계산 경로 응답에는 정확한 수치를 실을 수 없어(컬럼 없음) 이 문장이 근거 역할을 합니다.
        String mappingReason = "TACC: 후보 %d개 중 중복·저점수 %d개 제외 후 %d개 선택"
                .formatted(curated.initialContexts(), curated.removedContexts(),
                        curated.selectedContexts().size());

        List<CodeCandidate> selected = curated.selectedContexts();
        for (int i = 0; i < selected.size(); i++) {
            CodeCandidate c = selected.get(i);

            // CurateContextTool은 "1위 코드가 왜 이 섹션의 구현인지"만 설명합니다.
            // explanation은 행(chunk↔code_block) 단위 컬럼이라, 그 문장을 2~5위 행에도
            // 복사하면 해당 코드에 대한 사실과 다른 설명이 DB에 남습니다.
            // 따라서 1위 행에만 저장하고 나머지는 NULL로 둡니다.
            String explanation = (i == 0) ? curated.explanation() : null;

            jdbcTemplate.update("""
                    INSERT INTO paper_code_mappings
                        (paper_chunk_id, code_block_id, similarity_score, mapping_method,
                         mapping_reason, explanation, is_verified)
                    VALUES (?, ?, ?, 'AI', ?, ?, FALSE)
                    ON CONFLICT (paper_chunk_id, code_block_id) DO UPDATE
                        SET similarity_score = EXCLUDED.similarity_score,
                            explanation      = EXCLUDED.explanation,
                            -- A가 손으로 적어둔 매핑 근거(MANUAL)는 절대 덮어쓰지 않습니다.
                            -- mapping_method / is_verified 도 SET에 없으므로 그대로 유지됩니다.
                            mapping_reason   = CASE
                                WHEN paper_code_mappings.mapping_method = 'MANUAL'
                                THEN paper_code_mappings.mapping_reason
                                ELSE EXCLUDED.mapping_reason END,
                            updated_at       = CURRENT_TIMESTAMP
                    """,
                    chunkId, c.codeBlockId(), clampScore(c.similarityScore()),
                    mappingReason, explanation);
        }
        return selected.size();
    }

    /**
     * Script-2.sql의 ck_mapping_similarity는 0~1 범위만 허용합니다.
     * cosine distance 기반 계산은 부동소수 오차로 1을 아주 살짝 넘거나 음수가 될 수 있어 잘라냅니다.
     */
    private static double clampScore(double score) {
        return Math.min(1.0, Math.max(0.0, score));
    }
}
