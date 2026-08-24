package com.codeatlas.backend.common;

/** LLM 라이브 생성이 하드 타임아웃을 넘긴 경우. ApiExceptionHandler가 504로 변환한다. */
public class LlmTimeoutException extends RuntimeException {
    public LlmTimeoutException(String message) {
        super(message);
    }
}
