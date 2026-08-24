package com.codeatlas.backend.agent;

import com.codeatlas.backend.common.LlmText;
import com.codeatlas.backend.common.LlmTimeoutException;
import com.codeatlas.backend.common.NotFoundException;
import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.CodeSearchPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MappingReadPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * 사용자의 질문 텍스트에 실제로 답하는 유일한 경로.
 *
 * /api/agent/query 는 질문을 chunk 선택에만 쓰고 설명은 chunk↔코드 매핑 근거로
 * 고정돼 있다 — 같은 chunk 에 걸리는 서로 다른 두 질문이 같은 설명을 받는다.
 * 이 엔드포인트는 그 간극을 채우되, 사전계산 경로와 완전히 분리된다:
 *
 *   - DB 에 아무것도 쓰지 않는다. 응답 전용 — paper_code_mappings.explanation 은
 *     측정이 끝난 산출물이라 라이브 생성물로 오염시키지 않는다 (#51 리뷰 합의).
 *   - 매 호출이 Qwen3 라이브 생성이라 수십 초 걸린다. 프론트는 이 응답을
 *     사전계산 설명을 덮지 않고 별도 섹션에 live 배지로 표시한다.
 */
@RestController
public class AgentAnswerController {

    /**
     * 하드 타임아웃. 시연 중 Ollama 가 물리면 안 끝나는 스피너가 되므로
     * 여기서 끊고 프론트가 실패 카드로 떨어지게 한다 (#51 리뷰 합의).
     */
    private static final long ANSWER_TIMEOUT_SECONDS = 60;

    /** CurateContextTool 과 같은 이유 — 코드 하나가 지나치게 길면 앞부분만 쓴다. */
    private static final int MAX_CODE_CHARS = 2000;

    private final PaperChunkSearchPort paperChunkSearchPort;
    private final MappingReadPort mappingReadPort;
    private final CodeSearchPort codeSearchPort;
    private final ChatClient chatClient;

    public AgentAnswerController(
            PaperChunkSearchPort paperChunkSearchPort,
            MappingReadPort mappingReadPort,
            CodeSearchPort codeSearchPort,
            ChatClient.Builder chatClientBuilder
    ) {
        this.paperChunkSearchPort = paperChunkSearchPort;
        this.mappingReadPort = mappingReadPort;
        this.codeSearchPort = codeSearchPort;
        this.chatClient = chatClientBuilder.build();
    }

    public record AgentAnswerRequest(String query, Long paperId, Long chunkId) {}

    public record AgentAnswerResponse(String answer, long latencyMs) {}

    @PostMapping("/api/agent/answer")
    public AgentAnswerResponse answer(@RequestBody AgentAnswerRequest request) {
        if (request.query() == null || request.query().isBlank()) {
            throw new IllegalArgumentException("query가 비어 있습니다");
        }

        ChunkResult chunk = paperChunkSearchPort
                .getChunkById(request.paperId(), request.chunkId())
                .orElseThrow(() -> new NotFoundException("chunk를 찾을 수 없습니다: " + request.chunkId()));

        // 근거 코드는 사전계산 1위를 우선, 없으면(미큐레이션 chunk) 라이브 검색 1위.
        // 어느 쪽이든 조회만 한다 — 여기서 검색한 결과도 저장하지 않는다.
        CodeCandidate topCode = mappingReadPort.findMappings(request.chunkId(), 1).stream()
                .findFirst()
                .map(m -> m.candidate())
                .orElseGet(() -> codeSearchPort.findImplementationsScoped(request.chunkId(), 1)
                        .candidates().stream().findFirst().orElse(null));

        String prompt = buildPrompt(request.query(), chunk, topCode);

        long t0 = System.currentTimeMillis();
        String raw = callWithTimeout(prompt);
        return new AgentAnswerResponse(LlmText.stripThinking(raw), System.currentTimeMillis() - t0);
    }

    private String buildPrompt(String query, ChunkResult chunk, CodeCandidate topCode) {
        String codeBlock = (topCode == null)
                ? "(이 단락에 매핑된 코드가 없습니다 — 논문 섹션만으로 답하세요)"
                : "[매핑된 코드: %s / %s]\n%s".formatted(
                        topCode.repositoryName(), topCode.filePath(), truncate(topCode.codeContent()));
        return """
                다음은 사용자의 질문과, 그 질문에 가장 가까운 논문 섹션, 그리고 그 섹션에 매핑된 코드입니다.
                아래 자료에 실제로 드러난 내용만 근거로 사용자의 질문에 한국어 3~5문장으로 답하세요.
                자료에 없는 내용은 지어내지 말고 "이 섹션에는 나와 있지 않다"고 말하세요.

                [질문]
                %s

                [논문 섹션: %s]
                %s

                %s
                """.formatted(query, chunk.sectionTitle(), chunk.chunkText(), codeBlock);
    }

    private String callWithTimeout(String prompt) {
        CompletableFuture<String> call = CompletableFuture.supplyAsync(
                () -> chatClient.prompt().user(prompt).call().content());
        try {
            return call.get(ANSWER_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            call.cancel(true);
            throw new LlmTimeoutException(
                    "답변 생성이 %d초 안에 끝나지 않았습니다".formatted(ANSWER_TIMEOUT_SECONDS));
        } catch (ExecutionException e) {
            // Ollama 미기동(ResourceAccessException → 503) 등은 원래 핸들러가 처리하도록 풀어서 던진다
            if (e.getCause() instanceof RuntimeException cause) {
                throw cause;
            }
            throw new IllegalStateException("답변 생성 실패", e.getCause());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("답변 생성이 중단되었습니다", e);
        }
    }

    private String truncate(String codeText) {
        if (codeText == null) {
            return "";
        }
        return codeText.length() <= MAX_CODE_CHARS
                ? codeText
                : codeText.substring(0, MAX_CODE_CHARS) + "\n... (생략)";
    }
}
