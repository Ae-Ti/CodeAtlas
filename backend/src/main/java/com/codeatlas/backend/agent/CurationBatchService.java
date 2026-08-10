package com.codeatlas.backend.agent;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.tools.CurateContextTool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * B 구현. FindCodeImplementation(A의 CodeSearchPort)과 CurateContext(TACC+Qwen3)를
 * 그대로 재사용해서, 아직 매핑이 없는 chunk에 대해 결과를 미리 계산하고
 * paper_code_mappings에 저장합니다.
 *
 * 실행 시점:
 *   - 새 논문/repo를 큐레이션에 추가한 직후 (PWC/GitHub Search API 후보 승인 후)
 *   - 데모 리허설 전 최종 점검 시
 * AdminCurationController를 통해 수동으로 트리거합니다.
 *
 * 트랜잭션 경계는 **chunk 1건 단위**입니다. 배치 전체를 한 트랜잭션으로 묶으면
 * chunk 수만큼의 Ollama 호출 시간 내내 커넥션을 붙잡게 되고,
 * 중간에 한 건 실패하면 이미 성공한 큐레이션까지 전부 롤백됩니다.
 */
@Service
public class CurationBatchService {

    private static final Logger log = LoggerFactory.getLogger(CurationBatchService.class);

    private final JdbcTemplate jdbcTemplate;
    private final CodeSearchPort codeSearchPort;
    private final CurateContextTool curateContextTool;
    private final TransactionTemplate transactionTemplate;

    public CurationBatchService(
            JdbcTemplate jdbcTemplate,
            CodeSearchPort codeSearchPort,
            CurateContextTool curateContextTool,
            PlatformTransactionManager transactionManager
    ) {
        this.jdbcTemplate = jdbcTemplate;
        this.codeSearchPort = codeSearchPort;
        this.curateContextTool = curateContextTool;
        this.transactionTemplate = new TransactionTemplate(transactionManager);
    }

    public record BatchResult(int chunksPending, int chunksCurated, int chunksSkipped, int mappingsCreated) {}

    /** 진행 중인 배치의 현황. 중복 호출을 거절할 때 응답에 실어 보냅니다. */
    public record Progress(int done, int total) {}

    /**
     * 배치는 한 번에 하나만 돕니다.
     *
     * HTTP 클라이언트가 끊겨도 서버 핸들러는 계속 돌기 때문에, curl 을 Ctrl-C 하고
     * "다시 시작"하면 배치가 두 개가 됩니다. 실제로 그렇게 만들어서 chunk 를 두 번씩
     * 처리하고 Ollama 호출을 두 배로 쓴 적이 있습니다(2026-08-08). 진행률 로그가 각자
     * 분모를 쓰기 때문에(n/65, n/18) 밖에서는 하나만 도는 것처럼 보입니다.
     */
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final AtomicInteger progressDone = new AtomicInteger();
    private final AtomicInteger progressTotal = new AtomicInteger();

    /** 배치가 진행 중이면 현황을, 아니면 null 을 돌려줍니다. */
    public Progress currentProgress() {
        return running.get() ? new Progress(progressDone.get(), progressTotal.get()) : null;
    }

    /**
     * 아직 paper_code_mappings에 없는 chunk 전체를 대상으로 큐레이션 수행.
     *
     * @throws IllegalStateException 이미 배치가 돌고 있을 때
     */
    public BatchResult curateAllPendingChunks(int candidatesPerChunk, int selectedPerChunk) {
        if (!running.compareAndSet(false, true)) {
            Progress p = currentProgress();
            throw new IllegalStateException(p == null
                    ? "큐레이션 배치가 이미 실행 중입니다."
                    : "큐레이션 배치가 이미 실행 중입니다 (%d/%d). 진행 상황은 서버 로그를 보세요."
                            .formatted(p.done(), p.total()));
        }
        try {
            return runBatch(candidatesPerChunk, selectedPerChunk);
        } finally {
            running.set(false);
            progressDone.set(0);
            progressTotal.set(0);
        }
    }

    private BatchResult runBatch(int candidatesPerChunk, int selectedPerChunk) {
        List<Map<String, Object>> pending = jdbcTemplate.queryForList("""
                SELECT pc.id, pc.content
                FROM paper_chunks pc
                WHERE pc.embedding IS NOT NULL
                  AND NOT EXISTS (
                      -- 'AI' 매핑이 없는 chunk만 대상. A가 수동 매핑(MANUAL)을 넣어둔 chunk도
                      -- AI 근거는 따로 생성해야 하므로 mapping_method까지 봐야 합니다.
                      SELECT 1 FROM paper_code_mappings m
                      WHERE m.paper_chunk_id = pc.id AND m.mapping_method = 'AI'
                  )
                ORDER BY pc.id
                """);

        log.info("큐레이션 배치 시작: 대상 chunk {}건", pending.size());
        progressTotal.set(pending.size());
        progressDone.set(0);

        int curated = 0;
        int skipped = 0;
        int mappingsCreated = 0;

        for (Map<String, Object> row : pending) {
            Long chunkId = ((Number) row.get("id")).longValue();
            String content = (String) row.get("content");

            List<CodeCandidate> candidates = codeSearchPort.findImplementations(chunkId, candidatesPerChunk);
            if (candidates.isEmpty()) {
                // code_blocks가 아직 임베딩되지 않았거나 매칭 후보가 전혀 없는 chunk
                log.debug("chunk {} 건너뜀 — 후보 없음", chunkId);
                skipped++;
                progressDone.incrementAndGet();
                continue;
            }

            CuratedContext curatedContext = curateContextTool.curateContext(candidates, content, selectedPerChunk);
            Integer created = transactionTemplate.execute(status -> persist(chunkId, curatedContext));

            curated++;
            mappingsCreated += (created != null) ? created : 0;
            progressDone.incrementAndGet();
            log.info("chunk {} 큐레이션 완료 ({}/{}) — 매핑 {}건",
                    chunkId, curated + skipped, pending.size(), created);
        }

        log.info("큐레이션 배치 종료: 큐레이션 {}건, 건너뜀 {}건, 매핑 {}건", curated, skipped, mappingsCreated);
        return new BatchResult(pending.size(), curated, skipped, mappingsCreated);
    }

    /** 반환값은 저장(또는 갱신)한 매핑 행 수 */
    private int persist(Long chunkId, CuratedContext curated) {
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
