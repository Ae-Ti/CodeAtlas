package com.codeatlas.backend.common;

/** 조회 대상(논문/chunk)이 없을 때 — {@link ApiExceptionHandler}가 404로 변환합니다. */
public class NotFoundException extends RuntimeException {

    public NotFoundException(String message) {
        super(message);
    }
}
