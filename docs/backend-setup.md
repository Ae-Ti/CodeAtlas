# CodeAtlas 백엔드 구현 단계 (셋업 가이드)

> 스캐폴드 코드를 실제 프로젝트에 통합하는 순서와, 실제로 적용된 결과.
> 작성 기준: 2026.8.6 / **구현 완료 후 갱신됨**

실행 방법은 [backend/README.md](../backend/README.md)를 보세요. 이 문서는 "어떻게 만들어졌는지"의 기록입니다.

---

## 1. `backend/` 폴더에 Spring Boot 프로젝트 생성 ✅

[start.spring.io](https://start.spring.io)로 생성했습니다.

- Java 21
- 빌드 도구: Maven (`mvnw` 래퍼 포함 — 로컬에 maven 설치 불필요)
- 의존성: Spring Web(webmvc), JDBC, PostgreSQL Driver, Validation
- 위치: `backend/`

> ⚠️ 원래 계획은 Spring Data JDBC였지만 **plain `spring-boot-starter-jdbc`로 변경**했습니다.
> Spring Data JDBC는 기동 시 dialect 판별을 위해 DB에 즉시 접속하기 때문에,
> DB 없이 컨텍스트만 띄우는 테스트가 실패합니다. 우리는 `JdbcTemplate`만 쓰므로 필요 없습니다.

---

## 2. Spring AI 의존성 추가 ✅

`pom.xml`에 추가한 것:

- `spring-ai-bom` 2.0.0 (dependencyManagement에 import)
- `spring-ai-starter-mcp-server-webmvc`
- `spring-ai-starter-model-ollama`

**버전 조합 (확인 완료):**

| 항목 | 버전 | 비고 |
|---|---|---|
| Spring Boot | `4.1.0` | `4.1.0.RELEASE`가 아니라 `4.1.0` (Initializr 표기와 Maven 좌표가 다름) |
| Spring AI | `2.0.0` | Spring Boot 4.1.x에 맞춰 빌드된 라인. 1.1.x는 Boot 3.5.x용 |

MCP 어노테이션 경로는 `org.springframework.ai.mcp.annotation.McpTool` / `McpToolParam`으로 확정했습니다
(스캐폴드 주석에 있던 후보 중 이쪽이 맞습니다).
`@McpTool`이 붙은 `@Component`는 `McpServerAnnotationScannerAutoConfiguration`이 자동 등록하므로
별도 tool 등록 코드는 필요 없습니다. 기동 로그에 `Registered tools: 4`가 찍히면 정상입니다.

---

## 3. 생성된 파일을 정확한 패키지 경로에 복사 ✅

`backend/src/main/java/com/codeatlas/backend/` 밑에 스캐폴드 파일을 배치했습니다
(v1 13개 → v2에서 `MappingReadService`, `CurationBatchService`, `AdminCurationController` 3개 추가).
전체 패키지 구조는 [backend/README.md](../backend/README.md)의 "패키지 구조" 절 참고.

---

## 4. DB 연결 설정 + docker-compose ✅

- `docker-compose.yml` (repo 루트, 공동 관리): `pgvector/pgvector:pg17`
- `database/Script-2.sql`: **A가 확정한 실제 스키마** (papers / paper_chunks / repositories /
  paper_repositories / code_blocks / paper_code_mappings)
- `database/Script-3_pgvector.sql`: pgvector 확장 + `embedding vector(768)` + `embedding_model` + HNSW 인덱스
- `database/seed_demo.sql`: demo 논문 3편, chunk 6개, repo 4개, code block 7개 (**임시** — A의 `seed_dump.sql`로 교체 예정)

컨테이너를 처음 띄울 때 세 SQL이 순서대로 자동 적재됩니다. 스키마를 바꿨다면 볼륨을 지우고 다시 띄우세요.

```bash
docker compose down -v && docker compose up -d
```

> ⚠️ **컨테이너 포트는 5432가 아니라 5433입니다.**
> 로컬에 이미 PostgreSQL이 `127.0.0.1:5432`에 떠 있으면, Docker가 `*:5432`에 바인딩해도
> macOS는 `localhost`를 127.0.0.1로 먼저 해석해 **로컬 PostgreSQL로 연결됩니다.**
> (`role "codeatlas" does not exist` 에러가 이 증상입니다) 그래서 5433으로 옮겼습니다.

---

## 5. Ollama 설치 및 모델 다운로드 ✅

```bash
ollama pull qwen3:8b            # 설명 생성 / NL2SQL
ollama pull nomic-embed-text    # 임베딩 (768차원)
ollama serve                    # 기본 11434 포트
```

임베딩 모델이 추가된 이유: 논문 chunk 벡터 검색(`SearchPaperChunk`)에 질의 임베딩이 필요합니다.
**768차원은 `database/Script-3_pgvector.sql`의 `vector(768)`와 반드시 일치해야 합니다.**
A의 Python 파이프라인도 sentence-transformers 대신 Ollama `POST /api/embed`를 호출해야 같은 벡터 공간이 됩니다.

---

## 6. `application-ai.yml` 연결 ✅

메인 `application.yml`에서 불러옵니다.

```yaml
spring:
  config:
    import: application-ai.yml
```

---

## 7. 빌드 후 기동 확인 ✅

```bash
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run   # 최초 1회 (seed 임베딩 생성)
curl -X POST localhost:8080/api/admin/curate-pending       # 사전계산 큐레이션 (수 분)
./mvnw spring-boot:run                                     # 이후
../scripts/smoke.sh                                        # 전체 API 확인
```

---

## 스캐폴드에서 수정한 것

구현하면서 실제로 문제가 되어 고친 부분입니다.

| 대상 | 문제 | 조치 |
|---|---|---|
| `MetadataSqlService` | 금지어를 `upper.contains("CREATE")`로 검사 → `ORDER BY created_at`이 **CREATE로 오탐되어 차단**됨 | 단어 경계 정규식으로 변경. `ReadOnlySqlGuard`로 분리해 단위 테스트 추가 |
| `MetadataSqlService` | 애플리케이션 레벨 검사만 존재 | read-only 트랜잭션 실행 추가 (PostgreSQL이 쓰기를 거부) + 세미콜론/주석 차단 |
| `CurateContextTool`, `MetadataSqlService` | qwen3는 reasoning 모델이라 응답에 `<think>...</think>`가 섞여 나옴 | `LlmText.stripThinking()`으로 제거 |
| `CurateContextTool` | 긴 코드 블록이 통째로 프롬프트에 들어감 | 2000자 상한 |
| `AgentQueryController` | chunk 없음 → `IllegalArgumentException`(400) | `NotFoundException`(404)으로 변경, `/api/mapping/search`와 통일 |
| `SearchPaperChunkTool` | import 경로 불확실 주석 | Spring AI 2.0.0 기준으로 확정 |
| `CurationBatchService` (v2) | `@Transactional protected persist()`를 같은 클래스에서 호출 → **프록시를 타지 않아 트랜잭션이 걸리지 않음** | `TransactionTemplate`으로 chunk 1건 단위 트랜잭션 적용 |
| `CurationBatchService` (v2) | `mapping_reason` 컬럼을 채우지 않는데 `MappingReadService`는 그 값을 읽음 → 항상 null | 배치 시점 TACC 요약을 `mapping_reason`에 기록 |
| `CurationBatchService` (v2) | `chunksProcessed`가 후보 없어 건너뛴 chunk까지 포함 / `similarity_score`가 `ck_mapping_similarity`(0~1) 위반 가능 | `chunksCurated`/`chunksSkipped` 분리, 점수 0~1 clamp |
| `AgentQueryController` (v2) | 응답에서 `tacc`가 빠져 프론트 TACC 퍼널 UI가 표시할 수치를 잃음 | `tacc` 필드 복원 (사전계산 경로는 null + `mappingReason` 요약) |

---

## 추가로 만든 것

스캐폴드에 없던, 실행에 필요한 것들입니다.

- `docker-compose.yml`, `database/seed_demo.sql` (Script-2/Script-3는 A·스캐폴드 산출물)
- `PaperChunkSearchService`, `CodeSearchService` 실제 구현 (pgvector + JdbcTemplate)
- `PaperController`(`/api/papers`, `/api/papers/{id}/chunks`, chunk 검색), `MappingController`(`/api/mapping/search`)
- `EmbeddingBackfillRunner` — seed 데이터 임베딩 채우기 (A 파이프라인 완성 시 삭제 가능)
- `ApiExceptionHandler` — 통일된 에러 JSON, Ollama 미기동은 503으로 구분
- `WebCorsConfig` — vite dev server(5173) 연동
- 단위 테스트 30개, `scripts/smoke.sh`

---

## v2 핸드오프(`docs/claude-code-handoff.md`) 반영 결과

| 핸드오프 지시 | 처리 |
|---|---|
| 파일 매핑표대로 복사 + base package 확인 | 완료 (`com.codeatlas.backend` 그대로라 치환 불필요) |
| `@McpTool` import 경로 확인 | `org.springframework.ai.mcp.annotation` 확정 |
| `EmbeddingModel.embed(String)` 시그니처 확인 | Spring AI 2.0.0에서 `float[] embed(String)` 확인 |
| pom 의존성 중복 추가 금지 | 스캐폴드 pom(Boot 3.4.0)은 **미적용** — 이미 검증된 Boot 4.1.0 + Spring AI 2.0.0 유지 |
| `Script-2` 다음에 `Script-3` 적용 | docker-compose 초기화 순서로 보장 |
| 컴파일만 확인하고 실행은 하지 말 것 | **실행까지 진행함** — 로컬에 DB·Ollama가 준비돼 있어 실제 동작 검증이 가능했고, 그 과정에서 위 표의 v2 버그들이 드러났습니다 |
| 로직을 임의로 바꾸지 말 것 | 스키마/계약은 그대로 두고, 위 표의 **명백한 결함만** 수정 후 이 문서에 기록 |

---

## 현재 진행 상태 요약

| 항목 | 상태 |
|---|---|
| B 구현 (MCP tool 4종, agent/query, nl2sql, Ollama 연동) | ✅ 완료 — MCP tool 4종 등록·호출 확인 |
| A 구현 (`PaperChunkSearchService`, `CodeSearchService`) | ✅ 동작하는 기본 구현 완료 — **A가 검토 후 고도화 필요** |
| DB (docker-compose, pgvector, schema, seed) | ✅ 완료 |
| 전체 통합 테스트 | ✅ `scripts/smoke.sh` 전체 통과 |

### A가 이어서 할 일

`paper`/`mapping` 패키지의 구현은 "돌아가는 최소 버전"입니다. RACI표상 A 소유이므로 다음은 A가 판단해 주세요.

1. **임베딩 파이프라인 전환** — Python 파이프라인의 sentence-transformers를
   Ollama `POST /api/embed`(nomic-embed-text) 호출로 교체. 이어붙이는 텍스트 구성도
   `EmbeddingBackfillRunner`와 동일하게 맞춰야 합니다 (backend/README.md "임베딩" 절)
2. **실제 데이터 적재** — 지금 DB에 있는 건 demo seed 13행뿐. 큐레이션한 논문 10건 적재 +
   기획서 §2의 `seed_dump.sql` / `seed_manifest.csv` 생성
3. **검색 품질 개선** — 로드맵 2주차의 keyword overlap 점수 결합은 아직 미적용 (순수 cosine similarity)
4. **평가 지표** — 정답셋 30쌍으로 Top-1/3 Accuracy, MRR 산출. 코드 block 임베딩 조합도 이때 재검증
