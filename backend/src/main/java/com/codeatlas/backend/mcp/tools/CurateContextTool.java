package com.codeatlas.backend.mcp.tools;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.mcp.annotation.McpTool;
import org.springframework.ai.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.codeatlas.backend.common.LlmText;
import com.codeatlas.backend.mcp.dto.McpDtos.CodeCandidate;
import com.codeatlas.backend.mcp.dto.McpDtos.CuratedContext;

import java.util.*;
import java.util.stream.Collectors;

/**
 * TACC (Task-Aware Context Curation) 구현체.
 * 1) 후보 중복 제거 (codeBlockId 기준, 가장 높은 similarityScore만 남김)
 * 2) similarityScore 내림차순 정렬 후 상위 maxSelected개만 선택
 * 3) 선택된 후보들을 근거로 Qwen3(Ollama, 오픈웨이트)에게 선택 이유를 자연어로 요약시킴
 *
 * AI 응답 생성 모델은 운영규정 제9조(오픈웨이트 이상 공개 수준 필요) 대응을 위해
 * Claude/GPT API 대신 로컬 Ollama(Qwen3:8b)를 사용합니다.
 * application-ai.yml의 spring.ai.ollama 설정을 참고하세요.
 */
@Component
public class CurateContextTool {

    private static final int MAX_CODE_CHARS = 2000;

    private final ChatClient chatClient;

    public CurateContextTool(ChatClient.Builder chatClientBuilder) {
        // ChatClient.Builder는 spring-ai-starter-model-ollama 의존성을 추가하면
        // application-ai.yml 설정을 바탕으로 자동 구성됩니다.
        this.chatClient = chatClientBuilder.build();
    }

    @McpTool(
            name = "CurateContext",
            description = "검색된 코드 후보 중 중복을 제거하고 최종 context를 선별한 뒤, 선택 근거를 자연어로 설명한다."
    )
    public CuratedContext curateContext(
            @McpToolParam(description = "FindCodeImplementation 등에서 얻은 코드 후보 목록", required = true)
            List<CodeCandidate> candidates,
            @McpToolParam(description = "근거가 되는 원본 논문 chunk 텍스트", required = true)
            String queryChunkText,
            @McpToolParam(description = "최종 선택할 최대 개수 (기본 5)", required = false)
            Integer maxSelected
    ) {
        int limit = (maxSelected != null) ? maxSelected : 5;
        int initialCount = candidates.size();

        List<CodeCandidate> deduped = dedupeByCodeBlockId(candidates);
        List<CodeCandidate> selected = deduped.stream()
                .sorted(Comparator.comparingDouble(CodeCandidate::similarityScore).reversed())
                .limit(limit)
                .collect(Collectors.toList());

        int removedCount = initialCount - selected.size();
        String explanation = generateExplanation(queryChunkText, selected);

        return new CuratedContext(selected, initialCount, removedCount, explanation);
    }

    private List<CodeCandidate> dedupeByCodeBlockId(List<CodeCandidate> candidates) {
        Map<Long, CodeCandidate> best = new LinkedHashMap<>();
        for (CodeCandidate c : candidates) {
            best.merge(c.codeBlockId(), c,
                    (existing, incoming) -> incoming.similarityScore() > existing.similarityScore() ? incoming : existing);
        }
        return new ArrayList<>(best.values());
    }

    private String generateExplanation(String queryChunkText, List<CodeCandidate> selected) {
        if (selected.isEmpty()) {
            return "조건에 맞는 코드 구현체를 찾지 못했습니다.";
        }
        CodeCandidate top = selected.get(0);

        String prompt = """
                다음은 논문의 한 섹션과, 그 섹션과 매칭된 코드 구현입니다.
                왜 이 코드가 해당 섹션의 구현으로 적절한지 한국어로 2~3문장 이내로 설명하세요.
                과장하지 말고 코드에 실제로 드러난 근거만 언급하세요.

                [논문 섹션]
                %s

                [코드 구현: %s / %s — %s %s]
                %s
                """.formatted(queryChunkText, top.repositoryName(), top.filePath(),
                        top.symbolType(), symbolLabel(top), truncate(top.codeContent()));

        String raw = chatClient.prompt()
                .user(prompt)
                .call()
                .content();

        // qwen3는 reasoning 모델이라 <think> 블록이 섞여 나올 수 있어 제거 후 반환
        return LlmText.stripThinking(raw);
    }

    /** METHOD면 상위 클래스까지 붙여 {@code MultiHeadedAttention.forward} 형태로 보여줍니다. */
    private String symbolLabel(CodeCandidate candidate) {
        return (candidate.parentSymbolName() != null)
                ? candidate.parentSymbolName() + "." + candidate.symbolName()
                : String.valueOf(candidate.symbolName());
    }

    /** 코드 block 하나가 지나치게 길면 context window를 낭비하므로 앞부분만 사용 */
    private String truncate(String codeText) {
        if (codeText == null) {
            return "";
        }
        return codeText.length() <= MAX_CODE_CHARS
                ? codeText
                : codeText.substring(0, MAX_CODE_CHARS) + "\n... (생략)";
    }
}
