package com.codeatlas.backend.mcp.dto;

import java.util.List;
import java.util.Map;

/**
 * CodeAtlas MCP tool 간에 주고받는 DTO 모음.
 * 여러 record를 한 파일에 묶어두었습니다 — 필요하면 각자 파일로 분리해도 무방합니다.
 * 실제 base package(com.codeatlas.backend)는 프로젝트 구조에 맞게 바꿔주세요.
 */
public final class McpDtos {

    private McpDtos() {}

    /** 논문 chunk 검색 결과 (SearchPaperChunk 출력) */
    public record ChunkResult(
            Long chunkId,
            Long paperId,
            String sectionTitle,
            String chunkText,
            double score
    ) {}

    /** 코드 후보 (FindCodeImplementation 출력, CurateContext 입력) — code_blocks 실제 컬럼명 기준 */
    public record CodeCandidate(
            Long codeBlockId,
            String repositoryName,
            String filePath,
            String symbolName,
            String symbolType,        // FILE / CLASS / FUNCTION / METHOD / MODULE
            String parentSymbolName,  // 예: METHOD의 상위 CLASS 이름 (없으면 null)
            String codeContent,
            double similarityScore
    ) {}

    /**
     * 코드 후보 + 그 후보가 어떤 범위에서 나왔는지.
     *
     * @param candidates  유사도 내림차순 후보
     * @param paperScoped true면 그 chunk 가 속한 논문에 연결된 저장소 안에서 찾은 결과.
     *                    false면 연결된 저장소가 없어 전체 코퍼스로 폴백한 것이라
     *                    후보가 전부 <b>다른 논문의 구현</b>이다.
     *
     * <p>사전계산 배치는 이 값이 false면 큐레이션을 건너뛰어야 한다 —
     * 폴백 결과를 저장하면 다른 논문 코드가 {@code mapping_method='AI'} 로 영구히 남고,
     * REST 응답과 달리 화면에서 걸러낼 수단이 없다.
     */
    public record ScopedCandidates(List<CodeCandidate> candidates, boolean paperScoped) {}

    /** paper_code_mappings 테이블에서 읽은 사전계산 결과 (설명·검증여부 포함) */
    public record PrecomputedMapping(
            CodeCandidate candidate,
            String mappingReason,
            String explanation,
            boolean verified
    ) {}

    /** NL2SQL / QueryMetadataSQL 공용 결과 */
    public record NlSqlResult(
            String generatedSql,
            List<String> columns,
            List<Map<String, Object>> rows,
            boolean isReadOnly
    ) {}

    /** TACC(CurateContext) 결과 */
    public record CuratedContext(
            List<CodeCandidate> selectedContexts,
            int initialContexts,
            int removedContexts,
            String explanation
    ) {}
}
