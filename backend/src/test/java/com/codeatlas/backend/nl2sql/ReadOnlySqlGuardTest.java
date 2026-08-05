package com.codeatlas.backend.nl2sql;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;

class ReadOnlySqlGuardTest {

    @Test
    @DisplayName("마크다운 코드블록과 qwen3의 <think> 블록을 제거한다")
    void cleansModelArtifacts() {
        String raw = """
                <think>사용자는 star 수를 원하니 repositories를 조회하면 되겠다</think>
                ```sql
                SELECT star_count FROM repositories WHERE repo_name = 'annotated-transformer';
                ```
                """;

        assertThat(ReadOnlySqlGuard.clean(raw))
                .isEqualTo("SELECT star_count FROM repositories WHERE repo_name = 'annotated-transformer'");
    }

    @Test
    @DisplayName("모델이 앞에 설명을 붙여도 첫 SELECT부터 잘라 쓴다")
    void cutsLeadingProse() {
        String raw = "다음 쿼리를 사용하세요:\nSELECT title FROM papers";

        assertThat(ReadOnlySqlGuard.clean(raw)).isEqualTo("SELECT title FROM papers");
    }

    @Test
    @DisplayName("세미콜론 뒤에 붙은 두 번째 구문은 버린다")
    void keepsOnlyFirstStatement() {
        String raw = "SELECT title FROM papers; DROP TABLE papers";

        String cleaned = ReadOnlySqlGuard.clean(raw);
        assertThat(cleaned).isEqualTo("SELECT title FROM papers");
        assertThat(ReadOnlySqlGuard.isReadOnly(cleaned)).isTrue();
    }

    @ParameterizedTest
    @DisplayName("SELECT 단일 구문은 허용한다")
    @ValueSource(strings = {
            "SELECT * FROM papers",
            "SELECT star_count FROM repositories WHERE repo_name = 'annotated-transformer'",
            // 회귀 테스트: 단순 contains 검사는 created_at 안의 'CREATE'를 오탐해 이 쿼리를 막았다
            "SELECT title FROM papers ORDER BY created_at DESC",
            "SELECT p.title, r.star_count FROM papers p JOIN repositories r ON r.paper_id = p.paper_id"
    })
    void allowsSelect(String sql) {
        assertThat(ReadOnlySqlGuard.isReadOnly(sql)).isTrue();
    }

    @ParameterizedTest
    @DisplayName("쓰기 구문·다중 구문·주석 우회는 거부한다")
    @ValueSource(strings = {
            "DROP TABLE papers",
            "INSERT INTO papers (title) VALUES ('x')",
            "UPDATE repositories SET star_count = 0",
            "DELETE FROM papers",
            "SELECT * FROM papers; DROP TABLE papers",
            "SELECT * FROM papers -- 주석",
            "SELECT * FROM papers /* 주석 */",
            "SELECT pg_sleep(10)",
            "WITH x AS (SELECT 1) SELECT * FROM x",   // SELECT로 시작하지 않음
            ""
    })
    void rejectsNonReadOnly(String sql) {
        assertThat(ReadOnlySqlGuard.isReadOnly(sql)).isFalse();
    }

    @Test
    @DisplayName("LIMIT이 없으면 상한을 붙이고, 있으면 그대로 둔다")
    void appliesRowLimit() {
        assertThat(ReadOnlySqlGuard.withRowLimit("SELECT * FROM papers"))
                .isEqualTo("SELECT * FROM papers LIMIT " + ReadOnlySqlGuard.MAX_ROWS);
        assertThat(ReadOnlySqlGuard.withRowLimit("SELECT * FROM papers LIMIT 3"))
                .isEqualTo("SELECT * FROM papers LIMIT 3");
    }
}
