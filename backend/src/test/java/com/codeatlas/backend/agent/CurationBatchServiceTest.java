package com.codeatlas.backend.agent;

import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;
import com.codeatlas.backend.mcp.dto.McpDtos.ScopedCandidates;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.tools.CurateContextTool;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 배치 동시 실행 가드 검증.
 *
 * HTTP 클라이언트가 끊겨도 서버 핸들러는 계속 돌기 때문에, curl 을 Ctrl-C 하고 다시
 * 호출하면 배치가 두 개가 됩니다. 2026-08-08 에 실제로 그렇게 만들어서 같은 chunk 를
 * 두 번씩 처리하고 Ollama 호출을 두 배로 썼습니다. 그 재발을 막는 테스트입니다.
 *
 * Ollama·DB 없이 돌도록 의존성은 전부 mock 입니다.
 */
class CurationBatchServiceTest {

    /** 첫 배치가 이 지점에서 멈춰 있는 동안 두 번째 호출을 시도합니다. */
    private final CountDownLatch batchEntered = new CountDownLatch(1);
    private final CountDownLatch releaseBatch = new CountDownLatch(1);

    private CurationBatchService serviceStuckInsideBatch() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        when(jdbcTemplate.queryForList(anyString()))
                .thenReturn(List.<Map<String, Object>>of(Map.of("id", 101L, "content", "chunk text")));

        CodeSearchPort codeSearchPort = mock(CodeSearchPort.class);
        when(codeSearchPort.findImplementationsScoped(anyLong(), anyInt())).thenAnswer(invocation -> {
            batchEntered.countDown();
            // 두 번째 호출이 가드에 막히는 것을 확인할 때까지 배치를 붙잡아 둡니다.
            releaseBatch.await(5, TimeUnit.SECONDS);
            return new ScopedCandidates(List.<CodeCandidate>of(), true);   // 후보 없음 → persist 없이 건너뜀
        });

        CurateContextTool curateContextTool = mock(CurateContextTool.class);
        when(curateContextTool.curateContext(any(), anyString(), anyInt()))
                .thenReturn(new CuratedContext(List.of(), 0, 0, ""));

        PlatformTransactionManager tx = mock(DataSourceTransactionManager.class);
        return new CurationBatchService(jdbcTemplate, codeSearchPort, curateContextTool, tx);
    }

    @Test
    @DisplayName("배치가 도는 중에 다시 호출하면 거절한다 — 중복 실행 금지")
    void rejectsConcurrentRun() throws Exception {
        CurationBatchService service = serviceStuckInsideBatch();

        AtomicReference<Throwable> firstRunFailure = new AtomicReference<>();
        Thread first = new Thread(() -> {
            try {
                service.curateAllPendingChunks(20, 5);
            } catch (Throwable t) {
                firstRunFailure.set(t);
            }
        });
        first.start();
        assertThat(batchEntered.await(5, TimeUnit.SECONDS))
                .as("첫 배치가 시작되어야 합니다").isTrue();

        assertThat(service.currentProgress()).isNotNull();
        assertThat(service.currentProgress().total()).isEqualTo(1);

        assertThat(catchThrowableOf(() -> service.curateAllPendingChunks(20, 5)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("이미 실행 중");

        releaseBatch.countDown();
        first.join(5_000);
        assertThat(firstRunFailure.get()).as("첫 배치는 정상 종료해야 합니다").isNull();
    }

    @Test
    @DisplayName("배치가 끝나면 다시 호출할 수 있다 — 플래그가 남지 않는다")
    void releasesGuardAfterCompletion() throws Exception {
        CurationBatchService service = serviceStuckInsideBatch();
        releaseBatch.countDown();   // 붙잡지 않고 바로 끝나게

        service.curateAllPendingChunks(20, 5);

        assertThat(service.currentProgress()).as("종료 후에는 진행 중이 아니어야 합니다").isNull();
        // 두 번째 호출이 가드에 막히지 않아야 합니다.
        CurationBatchService.BatchResult again = service.curateAllPendingChunks(20, 5);
        assertThat(again.chunksPending()).isEqualTo(1);
    }

    @Test
    @DisplayName("논문에 연결된 저장소가 없어 폴백된 후보는 저장하지 않는다")
    void skipsUnscopedFallbackCandidates() {
        JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
        when(jdbcTemplate.queryForList(anyString()))
                .thenReturn(List.<Map<String, Object>>of(Map.of("id", 101L, "content", "chunk text")));

        // 후보는 있지만 paperScoped=false — 다른 논문의 코드다.
        CodeSearchPort codeSearchPort = mock(CodeSearchPort.class);
        when(codeSearchPort.findImplementationsScoped(anyLong(), anyInt())).thenReturn(
                new ScopedCandidates(List.of(new CodeCandidate(
                        1L, "other-paper-repo", "model.py", "forward",
                        "METHOD", "SomeClass", "def forward(self): ...", 0.9)),
                        false));

        CurateContextTool curateContextTool = mock(CurateContextTool.class);
        PlatformTransactionManager tx = mock(DataSourceTransactionManager.class);
        CurationBatchService service =
                new CurationBatchService(jdbcTemplate, codeSearchPort, curateContextTool, tx);

        CurationBatchService.BatchResult result = service.curateAllPendingChunks(20, 5);

        assertThat(result.chunksSkipped()).as("폴백 chunk 는 건너뛰어야 합니다").isEqualTo(1);
        assertThat(result.chunksCurated()).isZero();
        assertThat(result.mappingsCreated()).as("잘못된 매핑이 저장되면 안 됩니다").isZero();
        // Qwen3 호출까지 가면 안 된다 — 후보가 애초에 쓸 수 없는 것이기 때문.
        verify(curateContextTool, never()).curateContext(any(), anyString(), anyInt());
    }

    private static Throwable catchThrowableOf(Runnable runnable) {
        try {
            runnable.run();
            return null;
        } catch (Throwable t) {
            return t;
        }
    }
}
