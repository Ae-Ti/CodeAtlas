package com.codeatlas.backend.mapping;

import com.codeatlas.backend.common.NotFoundException;
import com.codeatlas.backend.mapping.CodeSearchService.CodeMatch;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * docs/api-spec.md 의 {@code POST /api/mapping/search}.
 * AI 설명(TACC) 없이 순수 유사도 검색 결과만 돌려주는 엔드포인트로,
 * AgentQueryController(/api/agent/query)와 같은 CodeSearchService를 공유합니다.
 */
@RestController
public class MappingController {

    private final PaperChunkSearchPort paperChunkSearchPort;
    private final CodeSearchService codeSearchService;

    public MappingController(PaperChunkSearchPort paperChunkSearchPort, CodeSearchService codeSearchService) {
        this.paperChunkSearchPort = paperChunkSearchPort;
        this.codeSearchService = codeSearchService;
    }

    public record MappingSearchRequest(Long paperId, Long chunkId, Integer topK) {}

    /**
     * @param paperScoped 이 논문에 연결된 저장소 안에서 찾은 결과면 true.
     *                    false면 연결된 저장소가 없어 전체 코퍼스로 폴백한 것이라
     *                    결과가 전부 <b>다른 논문의 구현</b>입니다 — 화면에서 그렇게 밝혀야 합니다.
     */
    public record MappingSearchResponse(ChunkResult queryChunk, List<CodeMatch> results, boolean paperScoped) {}

    @PostMapping("/api/mapping/search")
    public MappingSearchResponse search(@RequestBody MappingSearchRequest request) {
        int topK = (request.topK() != null) ? request.topK() : 5;

        ChunkResult queryChunk = paperChunkSearchPort
                .getChunkById(request.paperId(), request.chunkId())
                .orElseThrow(() -> new NotFoundException("chunk를 찾을 수 없습니다: " + request.chunkId()));

        CodeSearchService.ScopedMatches found = codeSearchService.findMatchesScoped(request.chunkId(), topK);
        return new MappingSearchResponse(queryChunk, found.matches(), found.paperScoped());
    }
}
