package com.codeatlas.backend.mcp.port;

import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.NlSqlResult;
import com.codeatlas.backend.mcp.dto.McpDtos.ScopedCandidates;

import java.util.List;
import java.util.Optional;

/**
 * 포트 인터페이스 모음. 담당자가 서로 다르니 주의:
 *   - PaperChunkSearchPort, CodeSearchPort → A(Knowledge Retrieval) 구현
 *   - MetadataSqlPort(NL2SQL) → B(Agent & AI Product) 본인 구현 (RACI표: NL2SQL은 B가 R/A)
 * B는 이 인터페이스에만 의존해서 MCP tool을 짜면 되고,
 * A는 pgvector/JPA 기반 실제 구현체를 backend/src/.../paper, .../mapping 패키지 등에 만들면 됩니다.
 * (같은 Spring Boot 앱 안이면 @Service 구현체를 등록하기만 하면 자동으로 주입됩니다)
 */
public final class CodeAtlasPorts {

    private CodeAtlasPorts() {}

    /** paper_chunks 검색 — A의 pgvector 유사도 검색 로직을 감쌈 */
    public interface PaperChunkSearchPort {
        List<ChunkResult> search(String queryText, Long paperId, int topK);
        Optional<ChunkResult> getChunkById(Long paperId, Long chunkId);
    }

    /** code_blocks 검색 — A의 POST /api/mapping/search 로직을 감쌈 */
    public interface CodeSearchPort {
        List<CodeCandidate> findImplementations(Long chunkId, int topK);

        /**
         * 후보와 함께 <b>그 논문에 연결된 저장소 안에서 찾았는지</b>를 돌려줍니다.
         *
         * <p>검색은 chunk 가 속한 논문의 저장소로 후보를 한정하지만, 연결된 저장소가 하나도 없는
         * 논문은 스코프가 비어 전체 코퍼스로 폴백합니다. 그 결과는 정의상 전부 다른 논문의 코드라,
         * <b>결과를 영구 저장하는 호출자는 반드시 이 값을 확인해야 합니다.</b>
         * ({@code ingest.py} 가 저장소 없는 논문의 적재를 허용하므로 실제로 나올 수 있는 상태입니다)
         *
         * <p>읽고 버리는 호출자(MCP tool, REST)는 {@link #findImplementations}로 충분합니다.
         */
        ScopedCandidates findImplementationsScoped(Long chunkId, int topK);
    }

    /** metadata(papers/repositories) 대상 read-only NL2SQL 엔진 — QueryMetadataSQL과 /api/nl2sql이 공유 */
    public interface MetadataSqlPort {
        NlSqlResult runReadOnlyQuery(String naturalLanguageQuery);
    }

    /**
     * paper_code_mappings에 미리 저장된 결과를 읽는 포트 (B 구현).
     * 큐레이션 배치가 이미 계산해둔 chunk는 여기서 즉시 반환 — 요청마다 Ollama를 부르지 않음.
     * 결과가 비어있으면(아직 큐레이션 안 된 chunk) 호출 측이 라이브 경로(CodeSearchPort + CurateContextTool)로 폴백.
     */
    public interface MappingReadPort {
        List<com.codeatlas.backend.mcp.dto.McpDtos.PrecomputedMapping> findMappings(Long chunkId, int topK);
    }
}
