package com.codeatlas.backend.chat;

import com.codeatlas.backend.chat.ChatController.ThinkFilter;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** 스트리밍 토큰에서 qwen3 의 think 블록을 걷어내는 필터 — 태그가 토큰 경계에서 잘리는 경우까지 */
class ThinkFilterTest {

    private static String run(List<String> tokens) {
        ThinkFilter f = new ThinkFilter();
        StringBuilder out = new StringBuilder();
        tokens.forEach(t -> out.append(f.accept(t)));
        return out.append(f.flush()).toString();
    }

    @Test
    @DisplayName("think 블록으로 시작하면 닫는 태그까지 버리고 그 뒤만 흘린다")
    void dropsLeadingThinkBlock() {
        assertThat(run(List.of("<think>", "생각 ", "중", "</think>", "\n답변", " 본문")))
                .isEqualTo("답변 본문");
    }

    @Test
    @DisplayName("태그가 토큰 경계에서 잘려도 인식한다")
    void handlesSplitTags() {
        assertThat(run(List.of("<th", "ink>추론</th", "ink>정답"))).isEqualTo("정답");
    }

    @Test
    @DisplayName("think 블록이 없으면 첫 토큰부터 그대로 흘린다")
    void passesThroughWithoutThink() {
        assertThat(run(List.of("안녕", "하세요"))).isEqualTo("안녕하세요");
    }

    @Test
    @DisplayName("'<' 로 시작하지만 think 가 아니면 모아둔 것을 그대로 내보낸다")
    void releasesNonThinkPrefix() {
        assertThat(run(List.of("<b>", "굵게</b>"))).isEqualTo("<b>굵게</b>");
    }

    @Test
    @DisplayName("짧은 응답이 판단 전에 끝나도 flush 로 내보낸다")
    void flushesShortAnswer() {
        assertThat(run(List.of("<t"))).isEqualTo("<t");
        assertThat(run(List.of("네"))).isEqualTo("네");
    }
}
