package com.codeatlas.backend.mapping;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * A 담당 영역(Knowledge Retrieval) — 논문 chunk ↔ 코드 block 매핑 검색.
 * 이 구현체 하나를 세 곳에서 재사용합니다:
 *   1) POST /api/mapping/search ({@link MappingController})
 *   2) FindCodeImplementation MCP tool
 *   3) CurationBatchService (사전계산 배치)
 *
 * chunk의 embedding은 이미 DB에 있으므로 재계산하지 않고 SQL 안에서 그대로 사용합니다.
 */
@Service
public class CodeSearchService implements CodeSearchPort {

    /**
     * REST(/api/mapping/search) 응답에만 필요한 라인 번호·GitHub URL까지 담은 확장 결과.
     * MCP 계약({@code McpDtos.CodeCandidate})은 그대로 두고 여기서만 추가 필드를 노출합니다.
     */
    public record CodeMatch(
            Long codeBlockId,
            String repositoryName,
            String filePath,
            String symbolName,
            String symbolType,
            String parentSymbolName,
            Integer startLine,
            Integer endLine,
            String codeContent,
            double similarityScore,
            String githubUrl
    ) {
        CodeCandidate toCandidate() {
            return new CodeCandidate(codeBlockId, repositoryName, filePath, symbolName,
                    symbolType, parentSymbolName, codeContent, similarityScore);
        }
    }

    /**
     * 검색 결과와 그 결과가 어떤 범위에서 나왔는지.
     *
     * @param matches     유사도 내림차순 결과
     * @param paperScoped true면 그 논문에 연결된 저장소 안에서만 찾은 결과,
     *                    false면 연결된 저장소가 없어 전체 코퍼스로 폴백한 결과(= 다른 논문의 구현)
     */
    public record ScopedMatches(List<CodeMatch> matches, boolean paperScoped) {}

    private static final String SELECT_CLAUSE = """
            SELECT cb.id AS code_block_id,
                   r.repository_name,
                   cb.file_path,
                   cb.symbol_name,
                   cb.symbol_type,
                   cb.parent_symbol_name,
                   cb.start_line,
                   cb.end_line,
                   cb.code_content,
                   r.github_url,
                   1 - (cb.embedding <=> pc.embedding) AS similarity_score
            """;

    /**
     * 기본 경로 — 후보를 <b>그 chunk가 속한 논문에 연결된 저장소</b>로 한정합니다.
     *
     * <p>제한이 없으면 논문 9편·저장소 12곳의 코드가 한 풀에 섞이는데, 트랜스포머 계열 구현은
     * 서로 어휘가 거의 같아 임베딩이 구분하지 못합니다. 정답셋 315 chunk 실측에서
     * <b>Top-1 오답의 47.6%가 다른 논문 저장소</b>였고 ViT는 그 비율이 91%였습니다
     * (ViT §3.1을 누르면 1~4위가 BERT·SAM 코드, 정답은 5위).
     *
     * <pre>
     *                              Top-1    Top-5      MRR
     *   전체 풀(182블록)            17.8%    40.6%   0.2614
     *   논문 범위 제한(평균 22블록)  28.9%    62.9%   0.4121
     * </pre>
     *
     * <p>대안도 같은 정답셋에서 재봤지만 이 방식을 넘지 못했습니다.
     * 다른 논문 코드를 빼지 않고 점수만 깎는 소프트 페널티는 가중치를 올릴수록 이 결과에
     * 수렴할 뿐이었고(w=0.15에서 완전히 동일), 임베딩 텍스트에 논문 제목·저장소 이름을
     * 넣는 방식은 Top-1이 17.8%로 그대로였습니다. 즉 <b>다른 논문 코드가 정답보다 실제로
     * 나은 경우가 없어서</b>, 후보에서 빼는 편이 단순하고 동등하게 좋습니다.
     *
     * <p>{@code paper_repositories}의 PK가 (paper_id, repository_id)라 조인으로 행이 늘지 않습니다.
     * 한 논문에 저장소가 여럿 붙은 경우(공식+커뮤니티)는 그 안에서 계속 비교됩니다.
     */
    private static final String SEARCH_SQL_SCOPED = SELECT_CLAUSE + """
            FROM code_blocks cb
            JOIN repositories r ON r.id = cb.repository_id
            JOIN paper_repositories pr ON pr.repository_id = cb.repository_id
            CROSS JOIN (SELECT paper_id, embedding FROM paper_chunks WHERE id = ?) pc
            WHERE pr.paper_id = pc.paper_id
              AND cb.embedding IS NOT NULL
              AND pc.embedding IS NOT NULL
            ORDER BY cb.embedding <=> pc.embedding
            LIMIT ?
            """;

    /**
     * 폴백 경로 — 논문에 연결된 저장소가 하나도 없을 때만 씁니다.
     *
     * <p>{@code ingest.py}는 저장소 없는 논문도 적재를 허용하므로 이 상태가 실제로 나올 수 있습니다.
     * 그때 범위 제한만 걸어두면 검색이 조용히 0건이 되므로, 전체 코퍼스로 넓혀 결과는 주되
     * {@link ScopedMatches#paperScoped()}를 false로 내려 화면이 "이 논문에 연결된 저장소가 없어
     * 다른 논문의 구현을 보여준다"고 밝힐 수 있게 합니다.
     *
     * <p>이 경로의 결과는 정의상 전부 다른 논문의 코드입니다. 감추면 틀린 답을 맞는 답처럼
     * 보여주게 되므로 반드시 표시와 함께 써야 합니다.
     */
    private static final String SEARCH_SQL_GLOBAL = SELECT_CLAUSE + """
            FROM code_blocks cb
            JOIN repositories r ON r.id = cb.repository_id
            CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = ?) pc
            WHERE cb.embedding IS NOT NULL
              AND pc.embedding IS NOT NULL
            ORDER BY cb.embedding <=> pc.embedding
            LIMIT ?
            """;

    private static final RowMapper<CodeMatch> MATCH_MAPPER = (rs, rowNum) -> new CodeMatch(
            rs.getLong("code_block_id"),
            rs.getString("repository_name"),
            rs.getString("file_path"),
            rs.getString("symbol_name"),
            rs.getString("symbol_type"),
            rs.getString("parent_symbol_name"),
            (Integer) rs.getObject("start_line"),
            (Integer) rs.getObject("end_line"),
            rs.getString("code_content"),
            rs.getDouble("similarity_score"),
            rs.getString("github_url")
    );

    private final JdbcTemplate jdbcTemplate;

    public CodeSearchService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Override
    public List<CodeCandidate> findImplementations(Long chunkId, int topK) {
        return findMatches(chunkId, topK).stream()
                .map(CodeMatch::toCandidate)
                .toList();
    }

    /** REST 응답용 — MCP 계약에 없는 라인 번호/GitHub URL까지 포함. */
    public List<CodeMatch> findMatches(Long chunkId, int topK) {
        return findMatchesScoped(chunkId, topK).matches();
    }

    /**
     * 논문 범위로 한정해 찾고, 그 논문에 연결된 저장소가 없을 때만 전체 코퍼스로 넓힙니다.
     * 폴백이 일어났는지는 {@link ScopedMatches#paperScoped()}로 알 수 있습니다.
     *
     * <p>스코프 결과가 비는 경우는 두 가지인데 둘 다 폴백이 맞습니다 —
     * 연결된 저장소가 없거나, 있어도 임베딩이 아직 안 채워졌거나(backfill 이전).
     */
    public ScopedMatches findMatchesScoped(Long chunkId, int topK) {
        List<CodeMatch> scoped = jdbcTemplate.query(SEARCH_SQL_SCOPED, MATCH_MAPPER, chunkId, topK);
        if (!scoped.isEmpty()) {
            return new ScopedMatches(scoped, true);
        }
        return new ScopedMatches(jdbcTemplate.query(SEARCH_SQL_GLOBAL, MATCH_MAPPER, chunkId, topK), false);
    }
}
