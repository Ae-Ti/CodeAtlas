package com.codeatlas.backend.common;

import java.util.regex.Pattern;

/**
 * 로컬 오픈웨이트 모델 응답 후처리.
 *
 * qwen3는 reasoning 모델이라 응답 본문 앞에 {@code <think> ... </think>} 블록을 붙일 수 있습니다.
 * 이 블록이 그대로 SQL이나 설명 텍스트에 섞이면 안 되므로 공통으로 제거합니다.
 */
public final class LlmText {

    private static final Pattern THINK_BLOCK = Pattern.compile("(?is)<think>.*?</think>");
    // 응답이 잘려 닫는 태그가 없는 경우까지 방어
    private static final Pattern UNCLOSED_THINK = Pattern.compile("(?is)<think>.*");

    private LlmText() {}

    public static String stripThinking(String raw) {
        if (raw == null) {
            return "";
        }
        String cleaned = THINK_BLOCK.matcher(raw).replaceAll("");
        cleaned = UNCLOSED_THINK.matcher(cleaned).replaceAll("");
        return cleaned.trim();
    }
}
