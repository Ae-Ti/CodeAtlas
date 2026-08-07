package com.codeatlas.backend.mcp.tools;

// Spring AI 2.0.0 기준 확정 경로 (spring-ai-mcp-annotations).
// @McpTool 이 붙은 @Component 는 McpServerAnnotationScannerAutoConfiguration이 자동으로 MCP tool로 등록합니다.
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;

import java.util.List;

@Component
public class SearchPaperChunkTool {

    private final PaperChunkSearchPort paperChunkSearchPort;

    public SearchPaperChunkTool(PaperChunkSearchPort paperChunkSearchPort) {
        this.paperChunkSearchPort = paperChunkSearchPort;
    }

    @McpTool(
            name = "SearchPaperChunk",
            description = "자연어 질의로 관련 논문 chunk를 검색한다. 특정 논문으로 범위를 좁힐 수도 있다."
    )
    public List<ChunkResult> searchPaperChunk(
            @McpToolParam(description = "검색할 자연어 질의", required = true) String queryText,
            @McpToolParam(description = "특정 논문으로 범위를 좁히고 싶을 때의 paperId", required = false) Long paperId,
            @McpToolParam(description = "반환할 최대 결과 수 (기본 5)", required = false) Integer topK
    ) {
        int k = (topK != null) ? topK : 5;
        return paperChunkSearchPort.search(queryText, paperId, k);
    }
}
