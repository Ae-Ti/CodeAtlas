package com.codeatlas.backend.agent;

import com.codeatlas.backend.agent.AgentQueryController.AgentQueryRequest;
import com.codeatlas.backend.agent.AgentQueryController.AgentQueryResponse;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import com.codeatlas.backend.mcp.dto.McpDtos.PrecomputedMapping;
import com.codeatlas.backend.mcp.dto.McpDtos.ScopedCandidates;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MappingReadPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import com.codeatlas.backend.mcp.tools.CurateContextTool;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 라이브 폴백 결과 캐싱 검증.
 *
 * 핵심은 paperScoped 가드입니다 — 폴백(paperScoped=false) 결과를 저장하면
 * 다른 논문의 코드가 mapping_method='AI'로 영구히 남습니다. 큐레이션 배치가
 * 밟았던 것과 같은 함정이라(CurationBatchServiceTest 참고) 라이브 경로에도
 * 같은 테스트를 둡니다. Ollama·DB 없이 돌도록 의존성은 전부 mock 입니다.
 */
class AgentQueryControllerTest {

    private static final Long PAPER_ID = 1L;
    private static final Long CHUNK_ID = 42L;

    private final PaperChunkSearchPort paperChunkSearchPort = mock(PaperChunkSearchPort.class);
    private final MappingReadPort mappingReadPort = mock(MappingReadPort.class);
    private final CodeSearchPort codeSearchPort = mock(CodeSearchPort.class);
    private final CurateContextTool curateContextTool = mock(CurateContextTool.class);
    private final MappingPersistService persistService = mock(MappingPersistService.class);

    private final AgentQueryController controller = new AgentQueryController(
            paperChunkSearchPort, mappingReadPort, codeSearchPort, curateContextTool, persistService);

    private static final CodeCandidate CANDIDATE = new CodeCandidate(
            7L, "some-repo", "model.py", "forward", "METHOD", "SomeClass",
            "def forward(self): ...", 0.9);

    @BeforeEach
    void chunkExists() {
        when(paperChunkSearchPort.getChunkById(PAPER_ID, CHUNK_ID)).thenReturn(Optional.of(
                new ChunkResult(CHUNK_ID, PAPER_ID, "3.1 Attention", "chunk text", 1.0)));
    }

    @Test
    @DisplayName("라이브 결과는 저장한다 — 같은 chunk 의 다음 조회부터 precomputed 로 응답하기 위해")
    void cachesLiveResultWhenPaperScoped() {
        when(mappingReadPort.findMappings(anyLong(), anyInt())).thenReturn(List.of());
        when(codeSearchPort.findImplementationsScoped(eq(CHUNK_ID), anyInt()))
                .thenReturn(new ScopedCandidates(List.of(CANDIDATE), true));
        CuratedContext curated = new CuratedContext(List.of(CANDIDATE), 1, 0, "설명");
        when(curateContextTool.curateContext(any(), anyString(), anyInt())).thenReturn(curated);

        AgentQueryResponse response = controller.query(new AgentQueryRequest("q", PAPER_ID, CHUNK_ID));

        assertThat(response.source()).isEqualTo("live");
        assertThat(response.paperScoped()).isTrue();
        verify(persistService).persistCurated(CHUNK_ID, curated);
    }

    @Test
    @DisplayName("폴백(paperScoped=false) 결과는 저장하지 않는다 — 다른 논문의 코드이기 때문")
    void doesNotCacheUnscopedFallback() {
        when(mappingReadPort.findMappings(anyLong(), anyInt())).thenReturn(List.of());
        when(codeSearchPort.findImplementationsScoped(eq(CHUNK_ID), anyInt()))
                .thenReturn(new ScopedCandidates(List.of(CANDIDATE), false));
        when(curateContextTool.curateContext(any(), anyString(), anyInt()))
                .thenReturn(new CuratedContext(List.of(CANDIDATE), 1, 0, "설명"));

        AgentQueryResponse response = controller.query(new AgentQueryRequest("q", PAPER_ID, CHUNK_ID));

        // 응답 자체는 내려주되(읽고 버리는 경로) 화면이 걸러낼 수 있게 플래그를 실어 보낸다.
        assertThat(response.source()).isEqualTo("live");
        assertThat(response.paperScoped()).isFalse();
        verify(persistService, never()).persistCurated(anyLong(), any());
    }

    @Test
    @DisplayName("선택된 후보가 없으면 저장하지 않는다 — 빈 큐레이션은 캐시할 것이 없다")
    void doesNotCacheEmptySelection() {
        when(mappingReadPort.findMappings(anyLong(), anyInt())).thenReturn(List.of());
        when(codeSearchPort.findImplementationsScoped(eq(CHUNK_ID), anyInt()))
                .thenReturn(new ScopedCandidates(List.of(), true));
        when(curateContextTool.curateContext(any(), anyString(), anyInt()))
                .thenReturn(new CuratedContext(List.of(), 0, 0, ""));

        controller.query(new AgentQueryRequest("q", PAPER_ID, CHUNK_ID));

        verify(persistService, never()).persistCurated(anyLong(), any());
    }

    @Test
    @DisplayName("사전계산 결과가 있으면 검색·저장 경로를 아예 타지 않는다")
    void precomputedPathDoesNotSearchOrPersist() {
        when(mappingReadPort.findMappings(eq(CHUNK_ID), anyInt())).thenReturn(List.of(
                new PrecomputedMapping(CANDIDATE, "TACC: …", "저장된 설명", false)));

        AgentQueryResponse response = controller.query(new AgentQueryRequest("q", PAPER_ID, CHUNK_ID));

        assertThat(response.source()).isEqualTo("precomputed");
        assertThat(response.paperScoped()).as("저장된 매핑은 항상 스코프 안이다").isTrue();
        verify(codeSearchPort, never()).findImplementationsScoped(anyLong(), anyInt());
        verify(persistService, never()).persistCurated(anyLong(), any());
    }
}
