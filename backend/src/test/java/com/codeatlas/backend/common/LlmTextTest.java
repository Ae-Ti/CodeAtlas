package com.codeatlas.backend.common;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class LlmTextTest {

    @Test
    @DisplayName("<think> 블록을 제거한다")
    void stripsThinkBlock() {
        assertThat(LlmText.stripThinking("<think>추론 과정</think>\n실제 답변"))
                .isEqualTo("실제 답변");
    }

    @Test
    @DisplayName("응답이 잘려 닫는 태그가 없어도 제거한다")
    void stripsUnclosedThinkBlock() {
        assertThat(LlmText.stripThinking("답변 앞부분 <think>추론이 잘림"))
                .isEqualTo("답변 앞부분");
    }

    @Test
    @DisplayName("think 블록이 없으면 원문을 그대로 둔다")
    void leavesPlainTextUntouched() {
        assertThat(LlmText.stripThinking("  평범한 설명  ")).isEqualTo("평범한 설명");
    }

    @Test
    @DisplayName("null은 빈 문자열로 처리한다")
    void handlesNull() {
        assertThat(LlmText.stripThinking(null)).isEmpty();
    }
}
