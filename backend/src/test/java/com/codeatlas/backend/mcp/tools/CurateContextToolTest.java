package com.codeatlas.backend.mcp.tools;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * TACC의 선별 로직(중복 제거 → 정렬 → 상위 N개) 검증.
 * 설명 생성은 Ollama 호출이라 mock으로 대체합니다 — 도구를 Ollama 없이 단위 테스트할 수 있습니다.
 */
class CurateContextToolTest {

    private static final String CHUNK_TEXT = "Multi-head attention allows the model to jointly attend...";

    private CurateContextTool tool;

    @BeforeEach
    void setUp() {
        ChatClient chatClient = mock(ChatClient.class, RETURNS_DEEP_STUBS);
        when(chatClient.prompt().user(anyString()).call().content())
                .thenReturn("<think>고민중</think>이 코드는 multi-head attention을 구현합니다.");

        ChatClient.Builder builder = mock(ChatClient.Builder.class);
        when(builder.build()).thenReturn(chatClient);

        tool = new CurateContextTool(builder);
    }

    private static CodeCandidate candidate(long id, double score) {
        return new CodeCandidate(id, "annotated-transformer", "model/attention.py",
                "forward", "METHOD", "MultiHeadedAttention", "def forward(...): ...", score);
    }

    @Test
    @DisplayName("같은 codeBlockId는 가장 높은 점수만 남기고 중복 제거한다")
    void dedupesByCodeBlockId() {
        List<CodeCandidate> candidates = List.of(
                candidate(501, 0.61),
                candidate(502, 0.72),
                candidate(501, 0.87)   // 501 중복 — 더 높은 0.87이 살아남아야 함
        );

        CuratedContext result = tool.curateContext(candidates, CHUNK_TEXT, 5);

        assertThat(result.selectedContexts())
                .extracting(CodeCandidate::codeBlockId)
                .containsExactly(501L, 502L);
        assertThat(result.selectedContexts().get(0).similarityScore()).isEqualTo(0.87);
        assertThat(result.initialContexts()).isEqualTo(3);
        assertThat(result.removedContexts()).isEqualTo(1);
    }

    @Test
    @DisplayName("similarityScore 내림차순으로 maxSelected개만 선택한다")
    void selectsTopNBySimilarity() {
        List<CodeCandidate> candidates = List.of(
                candidate(501, 0.55), candidate(502, 0.91), candidate(503, 0.73), candidate(504, 0.88));

        CuratedContext result = tool.curateContext(candidates, CHUNK_TEXT, 2);

        assertThat(result.selectedContexts())
                .extracting(CodeCandidate::codeBlockId)
                .containsExactly(502L, 504L);
        assertThat(result.removedContexts()).isEqualTo(2);
    }

    @Test
    @DisplayName("maxSelected가 null이면 기본 5개를 선택한다")
    void defaultsToFiveWhenMaxSelectedIsNull() {
        List<CodeCandidate> candidates = List.of(
                candidate(501, 0.9), candidate(502, 0.8), candidate(503, 0.7),
                candidate(504, 0.6), candidate(505, 0.5), candidate(506, 0.4));

        CuratedContext result = tool.curateContext(candidates, CHUNK_TEXT, null);

        assertThat(result.selectedContexts()).hasSize(5);
    }

    @Test
    @DisplayName("모델 응답의 <think> 블록은 explanation에 남지 않는다")
    void stripsThinkBlockFromExplanation() {
        CuratedContext result = tool.curateContext(List.of(candidate(501, 0.9)), CHUNK_TEXT, 5);

        assertThat(result.explanation())
                .isEqualTo("이 코드는 multi-head attention을 구현합니다.")
                .doesNotContain("<think>");
    }

    @Test
    @DisplayName("후보가 없으면 모델을 호출하지 않고 안내 문구를 반환한다")
    void handlesEmptyCandidates() {
        CuratedContext result = tool.curateContext(List.of(), CHUNK_TEXT, 5);

        assertThat(result.selectedContexts()).isEmpty();
        assertThat(result.explanation()).isEqualTo("조건에 맞는 코드 구현체를 찾지 못했습니다.");
    }
}
