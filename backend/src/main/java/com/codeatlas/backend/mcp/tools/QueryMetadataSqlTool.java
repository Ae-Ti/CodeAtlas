package com.codeatlas.backend.mcp.tools;

import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.codeatlas.backend.mcp.dto.McpDtos.NlSqlResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MetadataSqlPort;

@Component
public class QueryMetadataSqlTool {

    private final MetadataSqlPort metadataSqlPort;

    public QueryMetadataSqlTool(MetadataSqlPort metadataSqlPort) {
        this.metadataSqlPort = metadataSqlPort;
    }

    @McpTool(
            name = "QueryMetadataSQL",
            description = "논문/repository metadata에 대한 자연어 질의를 read-only SQL로 변환해 조회한다."
    )
    public NlSqlResult queryMetadataSql(
            @McpToolParam(description = "자연어 질의 (예: 'annotated-transformer repo의 star 수 알려줘')", required = true)
            String naturalLanguageQuery
    ) {
        // POST /api/nl2sql과 완전히 같은 엔진(MetadataSqlPort)을 공유합니다.
        // -> read-only 강제 로직을 한 곳(MetadataSqlPort 구현체)에서만 관리하면 됩니다.
        return metadataSqlPort.runReadOnlyQuery(naturalLanguageQuery);
    }
}
