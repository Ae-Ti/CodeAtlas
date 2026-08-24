# CodeAtlas API / MCP Tool 명세 (최종본 v2 — 실제 스키마 반영)

> A↔B 인터페이스 계약. 구현체는 `backend/` — 실행/구조는 [backend/README.md](../backend/README.md) 참고.
> v2 변경점: Script-2.sql 실제 컬럼명 반영, pgvector embedding 컬럼 추가(Script-3),
> `paper_code_mappings` 사전계산 아키텍처 도입, 임베딩 모델을 nomic-embed-text(Ollama)로 통일.
> **v2.1(구현 반영)**: 아래 "구현하면서 확정된 것" 절 참고.

---

## 아키텍처 변경 — 사전계산 우선, 라이브는 폴백

```
[큐레이션 배치] CurationBatchService
  = CodeSearchPort(A) 후보 검색 → CurateContextTool(TACC+Qwen3) → paper_code_mappings 저장
  트리거: POST /api/admin/curate-pending

[실시간 조회] AgentQueryController
  1) MappingReadPort로 paper_code_mappings 먼저 조회 (빠름, Ollama 미호출)
  2) 없으면(신규/미큐레이션 chunk) 라이브 경로 폴백: FindCodeImplementation → CurateContext
     (ad-hoc 검색 스트레치 기능과 동일 경로)
```

**왜 이렇게 바꿨나**: 매 요청마다 Ollama를 호출하면 느리고, 발표 데모 중 Ollama가 잠깐 멈추면 그대로 장애로 이어짐. 큐레이션된 10~20개 논문은 미리 계산해두고, 신규/ad-hoc만 라이브로 처리.

---

## 임베딩 모델 (중요)

**nomic-embed-text (Ollama, 768차원)** 로 통일. A의 Python 파이프라인도 sentence-transformers 대신 Ollama HTTP API(`POST /api/embed`)를 호출해야 B의 Java 코드가 만드는 벡터와 같은 공간에 있게 됩니다. 모델이 다르면 `<=>` 유사도 계산 자체가 무의미해집니다.

---

## MCP Tools (B 담당)

### SearchPaperChunk

| 항목 | 내용 |
|---|---|
| Input | `queryText`(필수), `paperId`(선택), `topK`(선택, 기본 5) |
| Output | `ChunkResult[]` — `chunkId, paperId, sectionTitle, chunkText, score` |
| 내부 구현 | `PaperChunkSearchPort`(A 구현) — `paper_chunks.embedding <=> query embedding` |

### FindCodeImplementation

| 항목 | 내용 |
|---|---|
| Input | `chunkId`(필수), `topK`(선택, 기본 5) |
| Output | `CodeCandidate[]` — `codeBlockId, repositoryName, filePath, symbolName, symbolType, parentSymbolName, codeContent, similarityScore` |
| 내부 구현 | `CodeSearchPort`(A 구현) — `code_blocks.embedding <=> paper_chunks.embedding` |

### QueryMetadataSQL

| 항목 | 내용 |
|---|---|
| Input | `naturalLanguageQuery`(필수) |
| Output | `NlSqlResult` — `generatedSql, columns, rows, isReadOnly` |
| 내부 구현 | `MetadataSqlPort`(**B 구현**, RACI 기준) — `POST /api/nl2sql`과 엔진 완전 공유 |

### CurateContext

| 항목 | 내용 |
|---|---|
| Input | `candidates`(필수), `queryChunkText`(필수), `maxSelected`(선택, 기본 5) |
| Output | `CuratedContext` — `selectedContexts, initialContexts, removedContexts, explanation` |
| ⚠️ explanation 범위 | **1위 후보 하나에 대한 설명**입니다 (`selected.get(0)`). 2위 이하는 순수 pgvector 유사도 순위이며 AI가 판단하지 않습니다. `paper_code_mappings.explanation`은 행 단위 컬럼이므로 **1위 행에만 저장**하고 나머지는 NULL로 둡니다 |
| 내부 구현 | 중복 제거(codeBlockId) → similarityScore 정렬 → 상위 N개 → Qwen3:8b로 근거 생성 |
| 호출 시점 | ① `CurationBatchService`(배치, 사전계산) ② `AgentQueryController` 라이브 폴백 경로 |

---

## REST API

### `POST /api/agent/query`

```jsonc
// Request
{ "query": "이 논문의 attention 부분은 코드로 어떻게 구현됐어?", "paperId": 1, "chunkId": 101 }

// Response (사전계산된 경우, source="precomputed")
{
  "queryChunk": { "chunkId": 101, "paperId": 1, "sectionTitle": "Multi-Head Attention", "chunkText": "...", "score": 1.0 },
  "results": [
    { "codeBlockId": 501, "repositoryName": "annotated-transformer", "filePath": "model/attention.py",
      "symbolName": "forward", "symbolType": "METHOD", "parentSymbolName": "MultiHeadedAttention",
      "codeContent": "...", "similarityScore": 0.87 }
  ],
  "explanation": "...",
  "source": "precomputed",
  "paperScoped": true,
  "mappingReason": "TACC: 후보 7개 중 중복·저점수 2개 제외 후 5개 선택",
  "tacc": { "initialContexts": null, "removedContexts": null, "selectedContexts": 5 },
  "mcpTools": [
    { "toolName": "getChunkById", "status": "done", "latencyMs": 4 },
    { "toolName": "MappingReadPort", "status": "done", "latencyMs": 8 }
  ]
}
```

`source: "live"`이면 미큐레이션 chunk라 그 자리에서 검색 → `CurateContext`를 돌린 것.
이 경우 `mappingReason`은 null이고 `tacc`에 정확한 수치가 채워집니다.
실측(demo seed, M4 macOS, qwen3:8b): **live 27.3초 vs precomputed 0.049초**.
라이브 결과는 저장되므로 같은 chunk 의 두 번째 조회부터 `precomputed`로 응답합니다.

`paperScoped: false`는 이 논문에 연결된 저장소가 없어 전체 코퍼스로 폴백한 것 —
`results`가 전부 **다른 논문의 구현**이므로 화면이 반드시 그렇게 밝혀야 하고,
이 결과는 저장되지 않습니다(다음 조회도 다시 live). `POST /api/mapping/search`의
같은 이름 필드와 의미가 동일하며, 사전계산 경로는 항상 `true`입니다.

> `tacc`는 v2 명세에 없던 필드를 **되살린 것**입니다. 프론트의 TACC 퍼널 UI
> (`frontend/src/data/agentResponses.ts`의 `TaccResult`)와 로드맵 "TACC 전후 수치 표시"
> 완료 기준이 이 수치를 요구합니다. 사전계산 경로에서는 배치 시점 후보/제외 개수가
> DB에 없어 `null`이고, 사람이 읽을 수 있는 요약만 `mappingReason`으로 제공합니다.
> 사전계산 경로에서도 정확한 수치가 필요하면 `paper_code_mappings`에
> `initial_contexts` / `removed_contexts` 컬럼 추가가 필요합니다 — **A 승인 대상**.

### `POST /api/agent/answer`

```jsonc
// Request — query는 /api/agent/query에 넣었던 질문 그대로, chunk는 그 응답의 queryChunk
{ "query": "In multi-head attention with h=8 heads, what dropout rate was applied?", "paperId": 1, "chunkId": 19 }

// Response
{ "answer": "이 섹션에는 드롭아웃률에 대한 정보가 나와 있지 않다. …", "latencyMs": 18412 }
```

**질문 텍스트에 실제로 답하는 유일한 경로.** `/api/agent/query`는 질문을 chunk 선택에만
쓰고 `explanation`은 chunk↔코드 매핑 근거라(라이브 경로도 `CurateContext`에 chunk 텍스트만
넘김) 같은 chunk에 걸리는 두 질문이 같은 설명을 받는다. 이 엔드포인트는 질문 + 매칭 chunk +
1위 코드(사전계산 우선, 없으면 라이브 검색 1위)를 qwen3:8b에 넘겨 **질문에 대한 답**을
생성하되, 사전계산 경로와 완전히 분리돼 있다 (#51 리뷰 합의):

- **DB에 쓰지 않는다.** 응답 전용 — `paper_code_mappings.explanation`은 측정이 끝난 산출물이라
  라이브 생성물로 오염시키지 않는다.
- **매 호출이 라이브 생성**이라 수십 초 걸린다. 실측(M4 macOS, qwen3:8b): 정상 15.6~19.1초(5회),
  모델 콜드 스타트 직후 36.1초, A 환경 31.2/32.9초. 프론트는 opt-in 버튼으로만 호출하고
  결과를 사전계산 설명 아래 `live 생성` 배지로 따로 표시한다.
- **60초 하드 타임아웃** → `504 { "error": "LLM_TIMEOUT" }`. 프론트는 실패 카드("위의 사전계산
  결과는 그대로 유효합니다") + 다시 시도로 떨어진다. Ollama 미기동은 Spring AI 자체 재시도
  때문에 즉시 503이 아니라 이 타임아웃으로 드러난다.
- 프롬프트가 "자료에 없으면 지어내지 말라"로 묶여 있어 근거 밖 질문은
  "이 섹션에는 나와 있지 않다"로 답한다 (실측).

### `POST /api/nl2sql`

```jsonc
// Request
{ "query": "star 수 상위 5개 repository 알려줘" }

// Response
{
  "generatedSql": "SELECT repository_name, star_count FROM repositories ORDER BY star_count DESC LIMIT 5",
  "columns": ["repository_name", "star_count"],
  "rows": [ { "repository_name": "annotated-transformer", "star_count": 3200 } ],
  "isReadOnly": true
}
```

### `POST /api/chat` (SSE)

```jsonc
// Request — 대화 전체를 클라이언트가 들고 온다 (서버 무상태). 마지막 user 메시지가 질문.
{ "messages": [ { "role": "user", "content": "multi-head attention은 어느 코드에 구현돼 있어?" } ] }

// Response: text/event-stream
event: sources   data: [ { "paperId": 1, "paperTitle": "Attention Is All You Need", "chunkId": 19,
                           "sectionTitle": "3.2.2 Multi-Head Attention", "score": 0.78,
                           "codeRepository": "attention-is-all-you-need-pytorch",
                           "codeSymbol": "MultiHeadAttention.forward", "codeFile": "transformer/SubLayers.py" } ]
event: token     data: 멀티헤드      ← 이어서 여러 번
event: done      data: { "latencyMs": 18230, "sources": 4 }
event: error     data: <메시지>      ← 생성 실패 시 (done 대신)
```

마지막 user 메시지로 `SearchPaperChunk`(top 4)를 돌리고, 각 단락의 사전계산 1위 코드와 매핑 근거를
[참고 자료]로 묶어 서비스 설명(화면·동작·수치)과 함께 시스템 프롬프트에 넣는다. 최근 10개 메시지만
모델에 넘긴다. DB 에 쓰지 않는다. qwen3 의 `<think>` 블록은 서버에서 걷어내고 흘린다. 180초 타임아웃.

### `POST /api/admin/upload` · `/ingest-json` · `GET /api/admin/upload/{id}`

```jsonc
// POST /api/admin/upload
{ "arxivId": "1505.04597", "githubUrl": "https://github.com/milesial/Pytorch-UNet", "relationType": "OFFICIAL" }
// POST /api/admin/upload/ingest-json?fileName=unet.json   본문 = ingest JSON (database/ingest_example.json 형식)

// 응답 (둘 다) / GET /api/admin/upload/{id} 는 log 까지
{ "id": "3f9a1c2e", "type": "arxiv", "label": "1505.04597 ← https://github.com/milesial/Pytorch-UNet",
  "status": "RUNNING",                       // QUEUED | RUNNING | DONE | FAILED
  "stage": "LATEX_SPLIT", "stageMessage": "qwen3 가 단락 경계 제안 — 섹션당 수십 초",
  "stages": ["ARXIV_META","EPRINT","REPO_CLONE","CODE_BLOCKS","LATEX_SPLIT","INGEST","EMBEDDING","CURATION"],
  "paperId": null, "chunks": null, "codeBlocks": null, "mappings": null, "error": null,
  "createdAt": "…", "startedAt": "…", "finishedAt": null, "log": ["▶ ARXIV_META — …", "   U-Net: …"] }
```

작업은 한 번에 하나만 돈다(단일 워커). 파이썬 단계는 `scripts/upload_pipeline.py` 가 서브프로세스로
돌며 `##STAGE` 줄로 단계를 보고하고, 임베딩·큐레이션은 백엔드 서비스가 이어서 수행한다. 작업 목록은
메모리에만 있어 재기동하면 사라지지만 적재 결과는 DB 에 남는다. 같은 arXiv ID 재업로드는 upsert.
JSON 경로는 `VALIDATE(ingest.py --dry-run) → INGEST → EMBEDDING → CURATION`.

### `POST /api/admin/curate-pending` (신규)

아직 `paper_code_mappings`에 없는 chunk 전체를 대상으로 배치 큐레이션을 수행한다. 인증 없는 내부용 — 데모 리허설 전, 또는 새 논문/repo 승인 직후 수동 트리거.

쿼리 파라미터로 후보/선택 개수를 조정할 수 있습니다 (기본 20 / 5).

```jsonc
// POST /api/admin/curate-pending?candidatesPerChunk=20&selectedPerChunk=5
// Response
{ "chunksPending": 6, "chunksCurated": 6, "chunksSkipped": 0, "mappingsCreated": 30 }
```

`chunksSkipped`는 후보 코드 block이 하나도 없어 건너뛴 chunk 수입니다
(보통 code_blocks 임베딩이 아직 안 채워진 경우).

### A 담당 REST (구현 완료)

| Method | Path | 응답 |
|---|---|---|
| GET | `/api/papers` | `paperId, title, authors[], arxivId, pdfUrl, publishedDate, processingStatus` |
| GET | `/api/papers/{paperId}/chunks` | `chunkId, sectionTitle, subsectionTitle, chunkIndex, chunkText` |
| POST | `/api/papers/chunks/search` | `{queryText, paperId?, topK?}` → `ChunkResult[]` (SearchPaperChunk와 동일 엔진) |
| POST | `/api/mapping/search` | `{paperId, chunkId, topK?}` → `{queryChunk, results[]}` |

`authors`는 DB에선 JSONB(`[{"name": "..."}]`)지만 API에선 **이름 문자열 배열**로 펴서 내보냅니다.
`/api/mapping/search`의 `results[]`는 `CodeCandidate` + `startLine`, `endLine`, `githubUrl`이며,
TACC·AI 설명 없이 순수 유사도 검색 결과만 반환합니다.

---

## 에러 응답 (공통)

```jsonc
{ "error": "NOT_FOUND", "detail": "chunk를 찾을 수 없습니다: 9999" }
```

| status | error | 상황 |
|---|---|---|
| 404 | `NOT_FOUND` | 논문/chunk 없음 |
| 400 | `BAD_REQUEST` | 잘못된 파라미터 |
| 503 | `MODEL_UNAVAILABLE` | Ollama 미기동 |
| 500 | `DATABASE_ERROR` | DB 접근 실패 |

## MCP 전송 방식

SSE — 연결 `GET /sse`, 요청 `POST /mcp/message?sessionId=...`
(`spring.ai.mcp.server.protocol: STREAMABLE`로 바꾸면 단일 엔드포인트 `POST /mcp`)

---

## 구현하면서 확정된 것 (v2.1)

| 항목 | 내용 |
|---|---|
| Spring Boot / Spring AI | **4.1.0 / 2.0.0** (스캐폴드 pom의 3.4.0이 아님 — Spring AI 2.0.0이 Boot 4.1.x 대응 라인) |
| MCP 어노테이션 | `org.springframework.ai.mcp.annotation.McpTool` / `McpToolParam` 확정 |
| JDBC 스타터 | `spring-boot-starter-jdbc` (Data JDBC는 기동 시 DB 접속을 강제해 무DB 테스트가 깨짐) |
| 코드 block 임베딩 입력 | `file_path + parent_symbol_name + symbol_name + code_content` — demo 6쌍 기준 Top-1 3/6 → 5/6. **A가 정답셋 30쌍으로 재검증 필요** |
| DB 포트 | docker-compose는 **5433** 노출 (로컬 PostgreSQL 5432와 충돌 회피) |

---

## A/B 작업 경계 요약

| 구현 대상 | 담당 | 위치 |
|---|---|---|
| `PaperChunkSearchPort` 구현체 | **A** | `backend/src/.../paper` |
| `CodeSearchPort` 구현체 (`POST /api/mapping/search`와 로직 공유) | **A** | `backend/src/.../mapping` |
| `MetadataSqlPort` 구현체 (NL2SQL) | **B** | `backend/src/.../nl2sql` |
| `MappingReadPort` 구현체 (사전계산 조회) | **B** | `backend/src/.../agent` |
| `CurationBatchService` (사전계산 배치) | **B** | `backend/src/.../agent` |
| MCP Tool 4종, `AgentQueryController`, `Nl2SqlController` | **B** | `backend/src/.../mcp`, `.../agent`, `.../nl2sql` |
| Ollama(qwen3:8b + nomic-embed-text) 설정 | **B** | `application-ai.yml` |
| Python 파이프라인의 임베딩 생성을 Ollama API 호출로 전환 | **A** | `data-pipeline/` |
