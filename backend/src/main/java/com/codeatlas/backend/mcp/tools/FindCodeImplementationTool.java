package com.codeatlas.backend.mcp.tools;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;

import java.util.List;

@Component
public class FindCodeImplementationTool {

    private final CodeSearchPort codeSearchPort;

    public FindCodeImplementationTool(CodeSearchPort codeSearchPort) {
        this.codeSearchPort = codeSearchPort;
    }

    @McpTool(
            name = "FindCodeImplementation",
            description = "논문 chunk에 대응하는 관련 코드 구현체를 유사도 순으로 검색한다."
    )
    public List<CodeCandidate> findCodeImplementation(
            @McpToolParam(description = "대상 논문 chunk의 chunkId", required = true) Long chunkId,
            @McpToolParam(description = "반환할 최대 결과 수 (기본 5)", required = false) Integer topK
    ) {
        int k = (topK != null) ? topK : 5;
        // 내부적으로 A가 만든 POST /api/mapping/search와 동일한 서비스 로직을 재사용합니다.
        return codeSearchPort.findImplementations(chunkId, k);
    }
}
