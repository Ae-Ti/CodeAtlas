package com.codeatlas.backend.agent;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import com.codeatlas.backend.mcp.dto.McpDtos.ScopedCandidates;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.tools.CurateContextTool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

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
    private final MappingPersistService mappingPersistService;

    public CurationBatchService(
            JdbcTemplate jdbcTemplate,
            CodeSearchPort codeSearchPort,
            CurateContextTool curateContextTool,
            MappingPersistService mappingPersistService
    ) {
        this.jdbcTemplate = jdbcTemplate;
        this.codeSearchPort = codeSearchPort;
        this.curateContextTool = curateContextTool;
        this.mappingPersistService = mappingPersistService;
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

            // 읽고 버리는 REST/MCP 경로와 달리 이 배치는 결과를 paper_code_mappings 에 영구 저장합니다.
            // 그래서 후보만 받지 않고 "그 논문 저장소 안에서 찾은 것인지"까지 확인합니다.
            ScopedCandidates found = codeSearchPort.findImplementationsScoped(chunkId, candidatesPerChunk);
            List<CodeCandidate> candidates = found.candidates();

            if (candidates.isEmpty()) {
                // code_blocks가 아직 임베딩되지 않았거나 매칭 후보가 전혀 없는 chunk
                log.debug("chunk {} 건너뜀 — 후보 없음", chunkId);
                skipped++;
                progressDone.incrementAndGet();
                continue;
            }
            if (!found.paperScoped()) {
                // 이 논문에 연결된 저장소가 없어 전체 코퍼스로 폴백한 경우다.
                // 후보가 전부 다른 논문의 코드이므로 저장하면 잘못된 매핑이 mapping_method='AI'로
                // 영구히 남는다. REST 응답에는 paperScoped 플래그가 실려 화면이 걸러낼 수 있지만
                // paper_code_mappings 에는 그런 표시를 남길 컬럼이 없다. 그래서 건너뛴다.
                log.warn("chunk {} 건너뜀 — 논문에 연결된 저장소가 없어 폴백됨. "
                        + "ingest JSON 의 repositories 를 확인하세요.", chunkId);
                skipped++;
                progressDone.incrementAndGet();
                continue;
            }

            CuratedContext curatedContext = curateContextTool.curateContext(candidates, content, selectedPerChunk);
            int created = mappingPersistService.persistCurated(chunkId, curatedContext);

            curated++;
            mappingsCreated += created;
            progressDone.incrementAndGet();
            log.info("chunk {} 큐레이션 완료 ({}/{}) — 매핑 {}건",
                    chunkId, curated + skipped, pending.size(), created);
        }

        log.info("큐레이션 배치 종료: 큐레이션 {}건, 건너뜀 {}건, 매핑 {}건", curated, skipped, mappingsCreated);
        return new BatchResult(pending.size(), curated, skipped, mappingsCreated);
    }

}
