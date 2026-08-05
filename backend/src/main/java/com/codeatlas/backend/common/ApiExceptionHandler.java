package com.codeatlas.backend.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;

import java.util.Map;

/**
 * 프론트가 항상 같은 모양의 에러 JSON을 받도록 통일합니다: {@code {"error": "...", "detail": "..."}}
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<Map<String, String>> handleNotFound(NotFoundException e) {
        return body(HttpStatus.NOT_FOUND, "NOT_FOUND", e.getMessage());
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> handleBadRequest(IllegalArgumentException e) {
        return body(HttpStatus.BAD_REQUEST, "BAD_REQUEST", e.getMessage());
    }

    /** Ollama 미기동 등 외부 모델 서버 접속 실패 — 데모 중 원인을 바로 알 수 있게 503으로 구분합니다. */
    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<Map<String, String>> handleModelUnavailable(ResourceAccessException e) {
        log.error("AI 모델 서버 접속 실패", e);
        return body(HttpStatus.SERVICE_UNAVAILABLE, "MODEL_UNAVAILABLE",
                "Ollama에 접속할 수 없습니다. `ollama serve` 실행 여부와 base-url을 확인하세요. (" + e.getMessage() + ")");
    }

    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<Map<String, String>> handleDatabase(DataAccessException e) {
        log.error("DB 접근 실패", e);
        return body(HttpStatus.INTERNAL_SERVER_ERROR, "DATABASE_ERROR", e.getMostSpecificCause().getMessage());
    }

    private ResponseEntity<Map<String, String>> body(HttpStatus status, String error, String detail) {
        return ResponseEntity.status(status)
                .body(Map.of("error", error, "detail", detail != null ? detail : ""));
    }
}
