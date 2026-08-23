package com.codeatlas.backend.chat;

import com.codeatlas.backend.mcp.dto.McpDtos.ChunkResult;
import com.codeatlas.backend.mcp.dto.McpDtos.PrecomputedMapping;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.MappingReadPort;
import com.codeatlas.backend.mcp.port.CodeAtlasPorts.PaperChunkSearchPort;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.ollama.api.OllamaChatOptions;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 서비스 챗봇 — 검색 기반(RAG)으로 답하되 대화는 자연스럽게.
 *
 * <pre>
 *   마지막 사용자 메시지 → SearchPaperChunk(top 4) → 각 chunk 의 사전계산 1위 코드
 *        → [서비스 설명 + 참고 자료] 시스템 프롬프트 + 최근 대화 → qwen3:8b 스트리밍
 * </pre>
 *
 * 응답은 SSE 로 흘린다 — 첫 이벤트 {@code sources} 에 검색된 근거를, 이어서 {@code token},
 * 끝에 {@code done}. 생성에 수십 초가 걸리는 로컬 모델에서 "자연스러운 챗봇"의 체감은
 * 첫 토큰까지의 시간이 결정하므로 전체를 기다렸다 한 번에 주지 않는다.
 *
 * DB 에 쓰지 않고, 사전계산 매핑은 읽기만 한다. 대화 기록은 클라이언트가 들고 와서
 * 매 요청에 함께 보낸다(서버 무상태).
 */
@RestController
public class ChatController {

    private static final Logger log = LoggerFactory.getLogger(ChatController.class);
    private static final int SOURCE_COUNT = 4;
    /** 이 아래 유사도의 단락은 근거로 쓰지 않는다 — 서비스 사용법 질문에 엉뚱한 논문이 인용되는 것 방지 */
    private static final double SOURCE_MIN_SCORE = 0.60;
    private static final int HISTORY_LIMIT = 10;        // 최근 N 개 메시지만 모델에 넘긴다
    private static final int CHUNK_CHARS = 700;          // 참고 자료 chunk 본문 상한 — 프롬프트 평가 시간이 첫 토큰 지연의 절반
    private static final int CODE_CHARS = 450;           // 참고 자료 코드 상한
    private static final long STREAM_TIMEOUT_MS = 180_000;

    private final PaperChunkSearchPort chunkSearch;
    private final MappingReadPort mappingRead;
    private final JdbcTemplate jdbc;
    private final ChatClient chatClient;

    public ChatController(PaperChunkSearchPort chunkSearch, MappingReadPort mappingRead,
                          JdbcTemplate jdbc, ChatClient.Builder chatClientBuilder) {
        this.chunkSearch = chunkSearch;
        this.mappingRead = mappingRead;
        this.jdbc = jdbc;
        this.chatClient = chatClientBuilder.build();
    }

    public record ChatMessage(String role, String content) {}

    public record ChatRequest(List<ChatMessage> messages) {}

    /** 토큰은 JSON 으로 감싸 보낸다 — 앞 공백·줄바꿈이 SSE 줄 규칙에 먹히지 않도록 */
    public record Token(String t) {}

    /** 화면이 답변 아래에 링크로 보여주는 근거 */
    public record Source(Long paperId, String paperTitle, Long chunkId, String sectionTitle, double score,
                         String codeRepository, String codeSymbol, String codeFile) {}

    @PostMapping(value = "/api/chat", produces = "text/event-stream")
    public SseEmitter chat(@RequestBody ChatRequest request) {
        List<ChatMessage> history = request.messages() == null ? List.of() : request.messages();
        String question = history.stream()
                .filter(m -> "user".equals(m.role()))
                .reduce((a, b) -> b).map(ChatMessage::content).orElse("");
        if (question.isBlank()) {
            throw new IllegalArgumentException("사용자 메시지가 비어 있습니다");
        }

        SseEmitter emitter = new SseEmitter(STREAM_TIMEOUT_MS);
        long t0 = System.currentTimeMillis();

        // 1) 검색 — 동기. 첫 이벤트로 근거를 먼저 내려 화면이 바로 "무엇을 읽고 있는지" 보여준다.
        List<Source> sources;
        try {
            sources = retrieve(question);
            sendJson(emitter, "sources", sources);
        } catch (Exception e) {
            log.warn("챗봇 검색 실패 — 근거 없이 답합니다: {}", e.getMessage());
            sources = List.of();
        }

        // 2) 생성 — 스트리밍. qwen3 의 <think> 블록은 흘리지 않는다.
        List<Message> messages = buildMessages(history, sources);
        ThinkFilter filter = new ThinkFilter();
        List<Source> finalSources = sources;
        chatClient.prompt()
                .messages(messages)
                // qwen3 의 추론(think) 단계를 끈다 — 첫 토큰까지의 시간이 곧 챗봇의 체감 속도다.
                // 대화 답변은 추론 없이도 충분하고, 근거는 프롬프트에 이미 들어 있다.
                .options(OllamaChatOptions.builder().disableThinking())
                .stream()
                .content()
                .timeout(Duration.ofMillis(STREAM_TIMEOUT_MS))
                .subscribe(
                        token -> {
                            String visible = filter.accept(token);
                            if (!visible.isEmpty()) {
                                sendJson(emitter, "token", new Token(visible));
                            }
                        },
                        err -> {
                            log.error("챗봇 생성 실패", err);
                            send(emitter, "error", err.getMessage() == null ? err.getClass().getSimpleName() : err.getMessage());
                            emitter.complete();
                        },
                        () -> {
                            String tail = filter.flush();
                            if (!tail.isEmpty()) {
                                sendJson(emitter, "token", new Token(tail));
                            }
                            send(emitter, "done", "{\"latencyMs\":" + (System.currentTimeMillis() - t0)
                                    + ",\"sources\":" + finalSources.size() + "}");
                            emitter.complete();
                        });
        return emitter;
    }

    // ── 검색 ────────────────────────────────────────────────────

    private List<Source> retrieve(String question) {
        List<ChunkResult> chunks = chunkSearch.search(question, null, SOURCE_COUNT).stream()
                .filter(c -> c.score() >= SOURCE_MIN_SCORE).toList();
        if (chunks.isEmpty()) {
            return List.of();
        }
        Map<Long, String> titles = paperTitles(chunks.stream().map(ChunkResult::paperId).distinct().toList());
        List<Source> out = new ArrayList<>();
        for (ChunkResult c : chunks) {
            PrecomputedMapping top = mappingRead.findMappings(c.chunkId(), 1).stream().findFirst().orElse(null);
            out.add(new Source(c.paperId(), titles.getOrDefault(c.paperId(), "논문 " + c.paperId()),
                    c.chunkId(), c.sectionTitle(), c.score(),
                    top == null ? null : top.candidate().repositoryName(),
                    top == null ? null : symbolLabel(top),
                    top == null ? null : top.candidate().filePath()));
        }
        return out;
    }

    private Map<Long, String> paperTitles(List<Long> ids) {
        String in = ids.stream().map(String::valueOf).collect(Collectors.joining(","));
        Map<Long, String> out = new HashMap<>();
        jdbc.query("SELECT id, title FROM papers WHERE id IN (" + in + ")",
                rs -> { out.put(rs.getLong("id"), rs.getString("title")); });
        return out;
    }

    private static String symbolLabel(PrecomputedMapping m) {
        var c = m.candidate();
        return c.parentSymbolName() != null ? c.parentSymbolName() + "." + c.symbolName() : String.valueOf(c.symbolName());
    }

    // ── 프롬프트 ────────────────────────────────────────────────

    private List<Message> buildMessages(List<ChatMessage> history, List<Source> sources) {
        List<Message> out = new ArrayList<>();
        out.add(new SystemMessage(systemPrompt(sources)));
        List<ChatMessage> recent = history.size() > HISTORY_LIMIT
                ? history.subList(history.size() - HISTORY_LIMIT, history.size()) : history;
        for (int i = 0; i < recent.size(); i++) {
            ChatMessage m = recent.get(i);
            if (m.content() == null || m.content().isBlank()) continue;
            if ("assistant".equals(m.role())) {
                out.add(new AssistantMessage(m.content()));
            } else {
                out.add(new UserMessage(m.content()));
            }
        }
        return out;
    }

    private String systemPrompt(List<Source> sources) {
        Map<String, Object> stats = jdbc.queryForMap("""
                SELECT (SELECT count(*) FROM papers) AS papers, (SELECT count(*) FROM paper_chunks) AS chunks,
                       (SELECT count(*) FROM repositories) AS repos, (SELECT count(*) FROM code_blocks) AS blocks,
                       (SELECT count(*) FROM paper_code_mappings) AS mappings
                """);
        StringBuilder refs = new StringBuilder();
        int i = 1;
        for (Source s : sources) {
            ChunkResult chunk = chunkSearch.getChunkById(s.paperId(), s.chunkId()).orElse(null);
            if (chunk == null) continue;
            refs.append("[%d] 「%s」 §%s (유사도 %.2f)\n%s\n".formatted(
                    i, s.paperTitle(), s.sectionTitle(), s.score(), truncate(chunk.chunkText(), CHUNK_CHARS)));
            PrecomputedMapping top = mappingRead.findMappings(s.chunkId(), 1).stream().findFirst().orElse(null);
            if (top != null) {
                refs.append("  ↳ 매핑된 코드: %s / %s — %s\n%s\n".formatted(
                        top.candidate().repositoryName(), top.candidate().filePath(), symbolLabel(top),
                        truncate(top.candidate().codeContent(), CODE_CHARS)));
                if (top.explanation() != null) {
                    refs.append("  ↳ 매핑 근거: ").append(top.explanation()).append('\n');
                }
            }
            refs.append('\n');
            i++;
        }

        return """
                당신은 CodeAtlas 의 안내 챗봇입니다. 사용자와 자연스럽게 한국어로 대화하되(사용자가 영어로 쓰면 영어로),
                사실은 아래 [서비스 설명]과 [참고 자료]에 있는 것만 말합니다. 자료에 없는 수치·파일명·함수명을
                지어내지 마세요. 자료에 없으면 "카탈로그에서 찾지 못했다"고 말하고, 논문 상세 화면이나 AI Agent
                화면에서 직접 단락을 고르거나 질문해 보라고 안내하세요. 답은 보통 3~6문장, 필요하면 짧은 목록.
                논문 내용이나 코드 위치를 [참고 자료]에서 가져와 답할 때만 근거 번호를 (예: [1]) 붙이세요 —
                서비스 설명에서 나온 사실에는 번호를 붙이지 마세요. 참고 자료가 질문과 무관하면 무시하세요.

                [서비스 설명]
                - CodeAtlas: 논문의 한 단락을 고르면 그 내용을 실제로 구현한 GitHub 코드 위치(파일·함수)를 찾아주는
                  서비스. Papers with Code 종료(2025-07) 이후 "논문 안의 어느 단락이 코드의 어느 함수인가"를 다루는 도구.
                - 현재 카탈로그: 논문 %s편, 단락 %s개, 저장소 %s곳, 코드 블록 %s개, 사전계산 매핑 %s건.
                - 동작: ① 적재(논문 단락 + 저장소 코드 블록, nomic-embed-text 임베딩 → PostgreSQL 17 + pgvector)
                  ② 사전계산 큐레이션(pgvector 코사인 거리로 후보 Top-K → TACC 가 중복·저점수 제거 후 5개 선별 →
                  qwen3:8b 가 "왜 이 코드인가" 설명 생성 → paper_code_mappings 저장) ③ 조회(사전계산이 있으면 0.05초,
                  없으면 그 자리에서 생성 = live 배지, 20~30초). 순위는 LLM 이 아니라 pgvector 거리가 정한다.
                - 화면: Dashboard(현황·논문별 대표 매핑) / Papers(목록) / 논문 상세(단락 클릭 → 코드 Top-5, Monaco 뷰어,
                  1위 매칭 근거) / AI Agent(자연어 질의 → 단락 검색 → 매핑·근거, 질문에 대한 AI 답변 버튼, NL2SQL) /
                  Graph(논문–코드 연결 그래프) / Upload(arXiv ID + GitHub URL 로 새 논문 자동 적재: 단락 분리 →
                  적재 → 임베딩 → 큐레이션, 10~30분) / Chat(이 화면).
                - NL2SQL: 자연어 → read-only SQL. SELECT 만 허용, DDL/DML 블록리스트, 세미콜론·주석 차단, 100행 상한,
                  read-only 트랜잭션, 노출 테이블은 메타데이터 3종(papers·repositories·paper_repositories).
                - MCP 서버(SSE): SearchPaperChunk · FindCodeImplementation · QueryMetadataSQL · CurateContext.
                - 모든 모델은 오픈웨이트 로컬 구동(qwen3:8b 생성, nomic-embed-text 임베딩, Ollama). 상용 AI API 호출 없음.
                - 검색 품질(정답셋 315쌍, 논문 내 저장소 한정): Top-1 29.8%%, Top-3 53.3%%, Top-5 65.4%%, MRR@10 0.454.
                  미매핑의 39.3%%는 저장소가 그 구현을 배포하지 않는 경우.
                - 새 논문 추가: Upload 화면(arXiv 에 LaTeX 소스가 있는 논문 + Python 저장소) 또는 ingest JSON 업로드.

                [참고 자료] — 사용자의 마지막 질문으로 카탈로그에서 검색한 단락과 그 단락에 매핑된 코드
                %s
                """.formatted(stats.get("papers"), stats.get("chunks"), stats.get("repos"), stats.get("blocks"),
                stats.get("mappings"), refs.isEmpty() ? "(검색 결과 없음)" : refs.toString());
    }

    private static String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max) + " …";
    }

    // ── SSE ─────────────────────────────────────────────────────

    /** 객체는 Spring 의 메시지 컨버터(Jackson)로 JSON 직렬화해 보낸다. */
    private static void sendJson(SseEmitter emitter, String event, Object data) {
        try {
            emitter.send(SseEmitter.event().name(event).data(data, MediaType.APPLICATION_JSON));
        } catch (IOException | IllegalStateException e) {
            log.debug("SSE 전송 실패 ({}): {}", event, e.getMessage());
        }
    }

    private static void send(SseEmitter emitter, String event, String data) {
        try {
            emitter.send(SseEmitter.event().name(event).data(data, MediaType.TEXT_PLAIN));
        } catch (IOException | IllegalStateException e) {
            // 클라이언트가 끊은 경우 — 생성은 구독 취소 없이 끝까지 돌지만 시연 규모에선 무해
            log.debug("SSE 전송 실패 ({}): {}", event, e.getMessage());
        }
    }

    /**
     * 스트림에서 qwen3 의 {@code <think>…</think>} 를 걷어낸다. 토큰 경계에서 태그가 잘릴 수 있어
     * 앞부분은 모아 두었다가 판단한다: 응답이 {@code <think>} 로 시작하면 {@code </think>} 까지 버린다.
     */
    static final class ThinkFilter {
        private static final String OPEN = "<think>";
        private static final String CLOSE = "</think>";
        private final StringBuilder buf = new StringBuilder();
        private int state = 0;  // 0 판단 전, 1 think 안, 2 통과
        private boolean trimLeading = false;  // think 블록 직후 줄바꿈·공백은 다음 토큰에 실려 올 수 있다

        String accept(String token) {
            if (state == 2) {
                if (!trimLeading) return token;
                String t = token.stripLeading();
                if (t.isEmpty()) return "";
                trimLeading = false;
                return t;
            }
            buf.append(token);
            if (state == 0) {
                String head = buf.toString().stripLeading();
                if (head.length() < OPEN.length()) {
                    return OPEN.startsWith(head) ? "" : release();
                }
                if (!head.startsWith(OPEN)) return release();
                state = 1;
            }
            int end = buf.indexOf(CLOSE);
            if (end < 0) return "";
            String rest = buf.substring(end + CLOSE.length()).stripLeading();
            buf.setLength(0);
            state = 2;
            trimLeading = rest.isEmpty();
            return rest;
        }

        String flush() {
            if (state == 0) return release();
            return "";
        }

        private String release() {
            state = 2;
            String s = buf.toString();
            buf.setLength(0);
            return s;
        }
    }
}
