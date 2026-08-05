package com.codeatlas.backend.nl2sql;

import com.codeatlas.backend.mcp.dto.McpDtos.NlSqlResult;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MetadataSqlPort;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.rowset.SqlRowSet;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * B(Agent & AI Product) 구현 대상 — NL2SQL은 RACI표 기준 B가 R/A입니다.
 * CurateContextTool과 동일한 Ollama(Qwen3:8b) ChatClient를 재사용해 SQL을 생성합니다.
 *
 * 안전장치 4중 (검사 로직은 {@link ReadOnlySqlGuard}에 모아 단위 테스트합니다):
 *   1) 생성된 SQL이 SELECT로 시작하는지 검사
 *   2) DDL/DML 키워드 블록리스트 검사 (단어 경계 기준 — created_at 같은 컬럼명 오탐 방지)
 *   3) 세미콜론(다중 구문)/주석 차단 + LIMIT 없으면 100행 상한 강제
 *   4) read-only 트랜잭션에서만 실행 (PostgreSQL이 쓰기 자체를 거부)
 *
 * 운영 배포 시 추가 권장: DB 계정 자체를 SELECT 권한만 있는 read-only 유저로 분리
 * (애플리케이션 레벨 검사만으로는 우회 가능성이 완전히 차단되지 않음)
 */
@Service
public class MetadataSqlService implements MetadataSqlPort {

    private static final Logger log = LoggerFactory.getLogger(MetadataSqlService.class);

    // Script-2.sql 기준 실제 스키마. metadata 테이블만 노출합니다
    // (paper_chunks/code_blocks의 embedding은 NL2SQL 대상이 아님).
    private static final String SCHEMA_CONTEXT = """
            papers(
                id BIGINT PK, title TEXT, abstract TEXT, arxiv_id VARCHAR, doi VARCHAR,
                pdf_url TEXT, published_date DATE,
                authors JSONB (예: [{"name": "Ashish Vaswani"}, ...]),
                processing_status VARCHAR  -- PENDING/PROCESSING/COMPLETED/FAILED
            )
            repositories(
                id BIGINT PK, github_url TEXT, owner_name VARCHAR, repository_name VARCHAR,
                default_branch VARCHAR, license_name VARCHAR, primary_language VARCHAR,
                star_count INTEGER, processing_status VARCHAR
            )
            paper_repositories(
                paper_id BIGINT FK, repository_id BIGINT FK,
                relation_type VARCHAR,  -- OFFICIAL/AUTHOR/COMMUNITY/REFERENCE
                is_primary BOOLEAN
            )

            -- papers/repositories는 paper_repositories로 다대다 연결됨 (repositories에 paper_id 없음)
            -- authors 안의 이름으로 필터링하려면 예: authors @> '[{"name": "Ashish Vaswani"}]'::jsonb 사용
            -- repository_name 값 예시: 'annotated-transformer', 'transformers'
            """;

    private final ChatClient chatClient;
    private final JdbcTemplate jdbcTemplate;
    private final TransactionTemplate readOnlyTx;

    public MetadataSqlService(ChatClient.Builder chatClientBuilder,
                              JdbcTemplate jdbcTemplate,
                              PlatformTransactionManager transactionManager) {
        this.chatClient = chatClientBuilder.build();
        this.jdbcTemplate = jdbcTemplate;
        this.readOnlyTx = new TransactionTemplate(transactionManager);
        this.readOnlyTx.setReadOnly(true);
    }

    @Override
    public NlSqlResult runReadOnlyQuery(String naturalLanguageQuery) {
        String sql = ReadOnlySqlGuard.clean(generateSql(naturalLanguageQuery));

        if (!ReadOnlySqlGuard.isReadOnly(sql)) {
            // 규정 위반 소지 있는 쿼리는 실행 자체를 막고 isReadOnly=false로 응답
            log.warn("read-only 검사에서 거부된 SQL: {}", sql);
            return new NlSqlResult(sql, List.of(), List.of(), false);
        }

        String boundedSql = ReadOnlySqlGuard.withRowLimit(sql);
        try {
            return readOnlyTx.execute(status -> execute(boundedSql));
        } catch (Exception e) {
            // 문법 오류 등 실행 실패 — 생성된 SQL은 그대로 보여주고 결과만 비움
            log.warn("생성된 SQL 실행 실패: {}", boundedSql, e);
            return new NlSqlResult(boundedSql, List.of(), List.of(), true);
        }
    }

    private String generateSql(String naturalLanguageQuery) {
        String prompt = """
                당신은 PostgreSQL 전문가입니다. 아래 스키마만 참고해서 사용자 질문에 맞는
                read-only SELECT 쿼리 단 한 줄만 생성하세요.
                설명, 마크다운 코드블록, 세미콜론, 세미콜론 뒤 텍스트는 절대 포함하지 마세요.
                WHERE 조건 값은 스키마의 값 예시를 따르고, 질문에 붙은 수식어를 값에 그대로 넣지 마세요.

                [스키마]
                %s

                [사용자 질문]
                %s

                SQL:
                """.formatted(SCHEMA_CONTEXT, naturalLanguageQuery);

        return chatClient.prompt().user(prompt).call().content();
    }

    private NlSqlResult execute(String sql) {
        SqlRowSet rs = jdbcTemplate.queryForRowSet(sql);

        int columnCount = rs.getMetaData().getColumnCount();
        List<String> columns = new ArrayList<>();
        for (int i = 1; i <= columnCount; i++) {
            columns.add(rs.getMetaData().getColumnName(i));
        }

        List<Map<String, Object>> rows = new ArrayList<>();
        while (rs.next()) {
            Map<String, Object> row = new LinkedHashMap<>();
            for (int i = 1; i <= columnCount; i++) {
                // 같은 이름의 컬럼이 여러 개일 수 있으므로 이름이 아닌 인덱스로 읽습니다
                row.put(columns.get(i - 1), rs.getObject(i));
            }
            rows.add(row);
        }

        return new NlSqlResult(sql, columns, rows, true);
    }
}
