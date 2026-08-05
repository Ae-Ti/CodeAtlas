package com.codeatlas.backend.nl2sql;

import com.codeatlas.backend.common.LlmText;

import java.util.List;
import java.util.regex.Pattern;

/**
 * LLM이 생성한 SQL을 실행 가능한 형태로 정리하고, read-only인지 검증합니다.
 * 순수 함수라 DB/모델 없이 단위 테스트할 수 있게 {@link MetadataSqlService}에서 분리했습니다.
 */
final class ReadOnlySqlGuard {

    static final int MAX_ROWS = 100;

    private static final List<String> FORBIDDEN_KEYWORDS = List.of(
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
            "CREATE", "GRANT", "REVOKE", "EXEC", "COPY", "MERGE", "CALL",
            "PG_SLEEP", "PG_READ_FILE", "DBLINK"
    );

    /**
     * created_at 같은 식별자 안의 부분 문자열을 키워드로 오인하지 않도록 단어 경계로 매칭합니다.
     * (단순 contains 검사는 "ORDER BY created_at"을 CREATE로 잘못 차단합니다)
     */
    private static final Pattern FORBIDDEN_PATTERN =
            Pattern.compile("\\b(" + String.join("|", FORBIDDEN_KEYWORDS) + ")\\b", Pattern.CASE_INSENSITIVE);

    private ReadOnlySqlGuard() {}

    /** 모델 응답에서 실행 가능한 SQL 한 구문만 뽑아냅니다. */
    static String clean(String raw) {
        String cleaned = LlmText.stripThinking(raw)   // qwen3의 <think> 블록 제거
                .replaceAll("(?i)```sql", "")
                .replace("```", "")
                .trim();

        // 모델이 앞뒤로 설명을 붙였을 때를 대비해 첫 SELECT부터 사용
        int selectIdx = cleaned.toUpperCase().indexOf("SELECT");
        if (selectIdx > 0) {
            cleaned = cleaned.substring(selectIdx);
        }
        // 첫 구문만 사용 (세미콜론 이후는 버림)
        int semicolon = cleaned.indexOf(';');
        if (semicolon >= 0) {
            cleaned = cleaned.substring(0, semicolon);
        }
        return cleaned.trim();
    }

    /** SELECT 단일 구문이고 DDL/DML 키워드가 없는지 검사합니다. */
    static boolean isReadOnly(String sql) {
        if (sql == null || sql.isBlank() || !sql.toUpperCase().startsWith("SELECT")) {
            return false;
        }
        if (sql.contains(";") || sql.contains("--") || sql.contains("/*")) {
            return false;   // 다중 구문 / 주석을 이용한 우회 차단
        }
        return !FORBIDDEN_PATTERN.matcher(sql).find();
    }

    /** LIMIT이 없으면 응답 폭주를 막기 위해 상한을 붙입니다. */
    static String withRowLimit(String sql) {
        return sql.toUpperCase().contains("LIMIT") ? sql : sql + " LIMIT " + MAX_ROWS;
    }
}
