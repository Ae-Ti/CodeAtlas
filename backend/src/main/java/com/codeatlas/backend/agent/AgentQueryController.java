package com.codeatlas.backend.agent;

import com.codeatlas.backend.common.NotFoundException;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import com.codeatlas.backend.mcp.dto.McpDtos.PrecomputedMapping;
import com.codeatlas.backend.mcp.dto.McpDtos.ScopedCandidates;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MappingReadPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import com.codeatlas.backend.mcp.tools.CurateContextTool;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Objects;

/**
 * 조회 우선순위:
 *   1) paper_code_mappings에 사전계산된 결과가 있으면 즉시 반환 (빠름, Ollama 호출 없음)
 *   2) 없으면(신규/미큐레이션 chunk) 라이브 경로로 폴백 — 검색 → CurateContext.
 *      라이브 결과는 저장해서 같은 chunk 의 다음 조회부터 1)로 응답합니다 —
 *      업로드 직후 사용자가 큐레이션 배치를 기다리지 않아도 두 번째부터는 빠릅니다.
 */
@RestController
public class AgentQueryController {

    /** 라이브 폴백 시 CurateContext에 넘길 후보 수 — CurationBatchService 배치 기준과 동일하게 유지 */
    private static final int CANDIDATE_COUNT = 20;
    private static final int SELECTED_COUNT = 5;

    private final PaperChunkSearchPort paperChunkSearchPort;
    private final MappingReadPort mappingReadPort;
    private final CodeSearchPort codeSearchPort;
    private final CurateContextTool curateContextTool;
    private final MappingPersistService mappingPersistService;

    public AgentQueryController(
            PaperChunkSearchPort paperChunkSearchPort,
            MappingReadPort mappingReadPort,
            CodeSearchPort codeSearchPort,
            CurateContextTool curateContextTool,
            MappingPersistService mappingPersistService
    ) {
        this.paperChunkSearchPort = paperChunkSearchPort;
        this.mappingReadPort = mappingReadPort;
        this.codeSearchPort = codeSearchPort;
        this.curateContextTool = curateContextTool;
        this.mappingPersistService = mappingPersistService;
    }

    public record AgentQueryRequest(String query, Long paperId, Long chunkId) {}

    public record ToolTiming(String toolName, String status, long latencyMs) {}

    /**
     * 프론트의 TACC 퍼널 UI(`frontend/src/data/agentResponses.ts`의 TaccResult)가 쓰는 수치.
     * 사전계산 경로에서는 배치 시점의 후보/제외 개수가 DB에 저장돼 있지 않아 null입니다
     * (정확한 수치가 필요하면 paper_code_mappings에 컬럼 추가 — A 승인 필요).
     * 대신 사람이 읽을 수 있는 요약은 mappingReason에 들어 있습니다.
     */
    public record TaccSummary(Integer initialContexts, Integer removedContexts, int selectedContexts) {}

    public record AgentQueryResponse(
            ChunkResult queryChunk,
            List<CodeCandidate> results,
            /**
             * "왜 이 코드가 이 논문 섹션의 구현으로 적절한가"에 대한 Qwen3 설명.
             * 대상은 <b>results의 1위 하나</b>입니다 — 2~5위는 순수 pgvector 유사도 순위일 뿐
             * AI가 판단한 결과가 아닙니다.
             */
            String explanation,
            String source,          // "precomputed" | "live"
            /**
             * false면 이 논문에 연결된 저장소가 없어 전체 코퍼스로 폴백한 결과 —
             * results가 전부 <b>다른 논문의 구현</b>이므로 화면이 그렇게 밝혀야 합니다.
             * 사전계산 경로는 항상 true입니다(배치·라이브 캐싱 모두 폴백 결과를 저장하지 않음).
             */
            boolean paperScoped,
            String mappingReason,   // 사전계산 경로의 배치 시점 TACC 요약 (live면 null)
            TaccSummary tacc,
            List<ToolTiming> mcpTools
    ) {}

    @PostMapping("/api/agent/query")
    public AgentQueryResponse query(@RequestBody AgentQueryRequest request) {

        long t0 = System.currentTimeMillis();
        ChunkResult queryChunk = paperChunkSearchPort
                .getChunkById(request.paperId(), request.chunkId())
                .orElseThrow(() -> new NotFoundException("chunk를 찾을 수 없습니다: " + request.chunkId()));
        long t1 = System.currentTimeMillis();

        // 1) 사전계산된 결과 먼저 조회
        List<PrecomputedMapping> precomputed = mappingReadPort.findMappings(request.chunkId(), SELECTED_COUNT);
        long t2 = System.currentTimeMillis();

        if (!precomputed.isEmpty()) {
            List<CodeCandidate> results = precomputed.stream().map(PrecomputedMapping::candidate).toList();
            PrecomputedMapping top = precomputed.get(0);

            // explanation은 1위 행에만 저장되지만, 부분 적재된 데이터에서도 죽지 않도록
            // 첫 non-null 값을 찾아 씁니다.
            String explanation = precomputed.stream()
                    .map(PrecomputedMapping::explanation)
                    .filter(Objects::nonNull)
                    .findFirst()
                    .orElse("이 매핑에 대한 AI 설명이 아직 생성되지 않았습니다.");

            return new AgentQueryResponse(
                    queryChunk,
                    results,
                    explanation,
                    "precomputed",
                    true,
                    top.mappingReason(),
                    new TaccSummary(null, null, results.size()),
                    List.of(
                            new ToolTiming("getChunkById", "done", t1 - t0),
                            new ToolTiming("MappingReadPort", "done", t2 - t1)
                    )
            );
        }

        // 2) 없으면 라이브 경로로 폴백 (ad-hoc 검색과 동일 흐름).
        //    결과를 저장하므로 Scoped 검색을 씁니다 (CodeAtlasPorts javadoc).
        ScopedCandidates found = codeSearchPort.findImplementationsScoped(request.chunkId(), CANDIDATE_COUNT);
        long t3 = System.currentTimeMillis();

        CuratedContext curated = curateContextTool
                .curateContext(found.candidates(), queryChunk.chunkText(), SELECTED_COUNT);
        long t4 = System.currentTimeMillis();

        // 3) 라이브 결과를 저장해 같은 chunk 의 다음 조회부터 precomputed 로 응답.
        //    폴백(paperScoped=false) 결과는 저장하지 않습니다 — 다른 논문의 코드가
        //    mapping_method='AI'로 영구히 남기 때문입니다. 배치(CurationBatchService)와 같은 판단.
        String persistStatus = "skipped";
        if (found.paperScoped() && !curated.selectedContexts().isEmpty()) {
            mappingPersistService.persistCurated(request.chunkId(), curated);
            persistStatus = "done";
        }
        long t5 = System.currentTimeMillis();

        return new AgentQueryResponse(
                queryChunk,
                curated.selectedContexts(),
                curated.explanation(),
                "live",
                found.paperScoped(),
                null,
                new TaccSummary(curated.initialContexts(), curated.removedContexts(),
                        curated.selectedContexts().size()),
                List.of(
                        new ToolTiming("getChunkById", "done", t1 - t0),
                        new ToolTiming("MappingReadPort", "empty", t2 - t1),
                        new ToolTiming("FindCodeImplementation", "done", t3 - t2),
                        new ToolTiming("CurateContext", "done", t4 - t3),
                        new ToolTiming("PersistMappings", persistStatus, t5 - t4)
                )
        );
    }
}
