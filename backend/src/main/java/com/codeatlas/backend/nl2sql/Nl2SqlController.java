package com.codeatlas.backend.nl2sql;

import com.codeatlas.backend.mcp.dto.McpDtos.NlSqlResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MetadataSqlPort;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class Nl2SqlController {

    private final MetadataSqlPort metadataSqlPort;

    public Nl2SqlController(MetadataSqlPort metadataSqlPort) {
        this.metadataSqlPort = metadataSqlPort;
    }

    public record Nl2SqlRequest(String query) {}

    @PostMapping("/api/nl2sql")
    public NlSqlResult nl2sql(@RequestBody Nl2SqlRequest request) {
        // QueryMetadataSQL MCP tool과 완전히 동일한 MetadataSqlPort를 호출합니다.
        // read-only 강제(SELECT 외 쿼리 차단)는 MetadataSqlPort 구현체 한 곳에서만 관리하세요.
        return metadataSqlPort.runReadOnlyQuery(request.query());
    }
}
