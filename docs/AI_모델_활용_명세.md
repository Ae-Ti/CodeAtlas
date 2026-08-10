# AI 모델 활용 명세 (초안)

> 운영규정 **제9조④** 대응 문서입니다.
> 주최 측 **지정 서식이 배포되면 이 내용을 그대로 옮겨 적으면 됩니다.**
> 이 문서는 서식 제출본이 아니라 내용 확정본입니다.
>
> 작성: 2026-08-10 / 근거: 로컬 실행 환경 실측 (`ollama /api/show`)

---

## 1. 결론 — 오픈웨이트 모델 로컬 구동

기획서 §7의 열린 결정사항("오픈웨이트 로컬 구동 vs 상용 API")은 **오픈웨이트 로컬 구동으로 확정**합니다.
런타임에 외부 상용 AI API를 호출하는 경로는 **없습니다.**

| 규정 | 요구 | 본 프로젝트 |
|---|---|---|
| 제9조① | AI 모델 최소 오픈웨이트 이상 공개 수준 | ✅ 사용 모델 2종 모두 Apache License 2.0, 가중치 공개 |
| 제9조②1다 | 상용 API 전용 모델 서비스 단순 연결 제한 (MCP 연동 생태계는 예외) | ✅ 상용 API 미사용. 자체 MCP 서버(tool 4종) 구현 |
| 제9조④ | AI 모델 활용 명세 제출 | 본 문서 |

---

## 2. 사용 모델

실행 환경에서 `ollama /api/show` 로 확인한 실측값입니다.

| 항목 | 생성 모델 | 임베딩 모델 |
|---|---|---|
| 모델명 | `qwen3:8b` | `nomic-embed-text` |
| 아키텍처 | qwen3 | nomic-bert |
| 파라미터 | 8.2B | 137M |
| 양자화 | Q4_K_M | F16 |
| 컨텍스트 길이 | 40,960 | 2,048 |
| 임베딩 차원 | — | **768** |
| 라이선스 | **Apache License 2.0** | **Apache License 2.0** |
| 배포처 | Ollama 레지스트리 (가중치 공개) | Ollama 레지스트리 (가중치 공개) |
| 구동 방식 | 로컬 (`ollama serve`, `localhost:11434`) | 로컬 (동일) |

임베딩 차원 768은 `database/Script-3_pgvector.sql` 의 `vector(768)` 과 일치해야 하며,
`scripts/doctor.sh` 가 실제 임베딩을 호출해 이를 검증합니다.

---

## 3. 활용 지점

### 3.1 생성 모델 (`qwen3:8b`)

| 기능 | 위치 | 역할 |
|---|---|---|
| 논문 단락 ↔ 코드 연결 근거 생성 | `CurateContextTool` | TACC 로 선별한 상위 후보에 대해 "왜 이 코드인지" 설명 생성 |
| 사전계산 큐레이션 배치 | `CurationBatchService` | chunk 1건당 1회 호출, 결과를 `paper_code_mappings` 에 저장 |
| 자연어 → SQL 변환 | `MetadataSqlService` | 논문·저장소 메타데이터 조회 질의를 read-only SQL 로 변환 |

### 3.2 임베딩 모델 (`nomic-embed-text`)

| 기능 | 위치 | 역할 |
|---|---|---|
| 논문 chunk 임베딩 | `EmbeddingBackfillRunner` | `paper_chunks.embedding` 생성 |
| 코드 블록 임베딩 | `EmbeddingBackfillRunner` | `code_blocks.embedding` 생성 |
| 질의 임베딩 | `PaperChunkSearchService` | 검색어를 같은 벡터 공간으로 투영 |

유사도 검색은 모델이 아니라 **PostgreSQL + pgvector 의 코사인 거리**로 수행합니다
(`CodeSearchService.SEARCH_SQL`). 순위 결정에 LLM 은 관여하지 않습니다.

---

## 4. 아키텍처상 위치 — MCP 기반임을 명시

제9조②1다는 "상용 API 전용 모델 서비스 단순 연결"을 제한하되 MCP 연동 생태계를 예외로 둡니다.
본 프로젝트는 **양쪽 모두에 해당하지 않는 방향**입니다 — 상용 API 를 쓰지 않으면서, 자체 MCP 서버를 구현했습니다.

```
[MCP 서버 — Spring AI, tool 4종]
  SearchPaperChunk        논문 chunk 벡터 검색      → pgvector
  FindCodeImplementation  관련 코드 후보 검색        → pgvector
  QueryMetadataSQL        메타데이터 SQL 조회        → qwen3:8b (NL2SQL) + read-only 실행
  CurateContext           후보 선별 + 근거 생성      → qwen3:8b

[사전계산 우선, 라이브는 폴백]
  POST /api/agent/query
    1) paper_code_mappings 조회 → 있으면 즉시 반환   source="precomputed"
    2) 없으면 FindCodeImplementation → CurateContext  source="live"
```

모델은 "검색 결과를 설명하는 도구"로 쓰이고, **연결의 근거가 되는 검색 자체는 벡터 DB가 담당**합니다.
즉 단일 상용 모델에 기능을 위임한 구조가 아닙니다.

---

## 5. 안전장치

| 항목 | 조치 |
|---|---|
| NL2SQL 오남용 | `ReadOnlySqlGuard` — 단어 경계 정규식으로 DDL/DML 차단, 세미콜론·주석 차단, read-only 트랜잭션으로 이중 방어 (단위 테스트 18건) |
| reasoning 토큰 노출 | `LlmText.stripThinking()` — qwen3 의 `<think>...</think>` 제거 |
| 프롬프트 크기 | `CurateContextTool` 에서 코드 블록 2000자 상한 |
| 모델 장애 | Ollama 미기동/응답 없음은 503 으로 구분 (`ApiExceptionHandler`). 사전계산 결과가 있으면 모델 없이도 조회 동작 |

---

## 6. 재현 방법

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve                 # localhost:11434

./scripts/doctor.sh          # 모델 존재 + 실제 추론 + 임베딩 768차원 검증
```

`doctor.sh` 는 `/api/tags`(메타데이터)만 보지 않고 **실제 생성·임베딩을 호출**합니다.
추론 엔진이 멈춰도 `/api/tags` 는 200 을 돌려주기 때문입니다.

---

## 7. 남은 작업

- [ ] 주최 측 지정 서식 확보 후 본 문서 내용 이관
- [ ] 결과보고서에 제9조②1다 대응(MCP 기반 아키텍처) 서술 — §4 내용 사용
- [ ] 기획서 §2 "AI 모델 활용 방식 최종 결정 = 미결정" 항목을 확정으로 갱신
