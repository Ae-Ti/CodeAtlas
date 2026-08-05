package com.codeatlas.backend.paper;

import com.codeatlas.backend.common.NotFoundException;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import com.codeatlas.backend.paper.PaperCatalogService.ChunkSummary;
import com.codeatlas.backend.paper.PaperCatalogService.PaperSummary;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** docs/api-spec.md 의 논문 조회 API. */
@RestController
@RequestMapping("/api/papers")
public class PaperController {

    private final PaperCatalogService paperCatalogService;
    private final PaperChunkSearchPort paperChunkSearchPort;

    public PaperController(PaperCatalogService paperCatalogService, PaperChunkSearchPort paperChunkSearchPort) {
        this.paperCatalogService = paperCatalogService;
        this.paperChunkSearchPort = paperChunkSearchPort;
    }

    @GetMapping
    public List<PaperSummary> papers() {
        return paperCatalogService.findAllPapers();
    }

    @GetMapping("/{paperId}/chunks")
    public List<ChunkSummary> chunks(@PathVariable Long paperId) {
        if (!paperCatalogService.paperExists(paperId)) {
            throw new NotFoundException("논문을 찾을 수 없습니다: " + paperId);
        }
        return paperCatalogService.findChunks(paperId);
    }

    public record ChunkSearchRequest(String queryText, Long paperId, Integer topK) {}

    /** SearchPaperChunk MCP tool과 같은 엔진을 쓰는 REST 진입점 (프론트 검색창용). */
    @PostMapping("/chunks/search")
    public List<ChunkResult> searchChunks(@RequestBody ChunkSearchRequest request) {
        int topK = (request.topK() != null) ? request.topK() : 5;
        return paperChunkSearchPort.search(request.queryText(), request.paperId(), topK);
    }
}
