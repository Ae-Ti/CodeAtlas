# CodeAtlas Backend

논문 chunk ↔ 코드 구현을 연결하는 Spring Boot 백엔드. MCP tool 4종, TACC context 선별,
사전계산 큐레이션, NL2SQL, pgvector 유사도 검색을 제공합니다.

- Java 21 / Spring Boot 4.1.0 / Spring AI 2.0.0
- PostgreSQL 17 + pgvector
- AI 모델: **Ollama 로컬 구동** (`qwen3:8b` 생성, `nomic-embed-text` 임베딩) — 운영규정 제9조(오픈웨이트) 대응

---

## 빠른 실행

```bash
# 1. DB (repo 루트에서)
docker compose up -d          # pgvector 컨테이너 → localhost:5433
                              # Script-2 → Script-3 → seed_demo 순으로 자동 적재

# 2. 모델
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve                  # localhost:11434

# 3. seed 데이터 임베딩 (최초 1회)
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run

# 4. 큐레이션 사전계산 (chunk당 Qwen3 1회 — 수 분 소요)
curl -X POST localhost:8080/api/admin/curate-pending

# 5. 이후 기동
./mvnw spring-boot:run        # localhost:8080

# 6. 확인
../scripts/smoke.sh
```

> DB 컨테이너는 **5433** 포트를 씁니다. 로컬에 이미 PostgreSQL이 5432에 떠 있는 경우가 많아
> 충돌을 피하려고 옮겨 두었습니다. 바꾸려면 `docker-compose.yml`과 `application.yml`을 함께 수정하세요.

---

## 아키텍처 — 사전계산 우선, 라이브는 폴백

```
[큐레이션 배치]  POST /api/admin/curate-pending
   CodeSearchService(후보 검색) → CurateContextTool(TACC + Qwen3) → paper_code_mappings 저장

[실시간 조회]    POST /api/agent/query
   1) paper_code_mappings 조회 → 있으면 즉시 반환   source="precomputed"
   2) 없으면 FindCodeImplementation → CurateContext  source="live"
```

매 요청마다 Qwen3를 부르면 느리고, 데모 중 Ollama가 멈추면 그대로 장애가 됩니다.
큐레이션된 논문은 미리 계산해두고 신규/ad-hoc만 라이브로 처리합니다.

실측(demo seed, M4 macOS): **live 27.3초 → precomputed 0.049초**.

---

## API

| Method | Path | 설명 | 담당 |
|---|---|---|---|
| GET | `/api/papers` | 논문 목록 (authors JSONB → 이름 배열) | A |
| GET | `/api/papers/{paperId}/chunks` | 논문 chunk 목록 | A |
| POST | `/api/papers/chunks/search` | 자연어 → chunk 벡터 검색 | A |
| POST | `/api/mapping/search` | chunk → 코드 Top-K (AI 설명 없음) | A |
| POST | `/api/agent/query` | 사전계산 조회 + 라이브 폴백 | B |
| POST | `/api/admin/curate-pending` | 배치 큐레이션 (내부용, 인증 없음) | B |
| POST | `/api/nl2sql` | 자연어 → read-only SQL 조회 | B |

요청/응답 스키마는 [docs/api-spec.md](../docs/api-spec.md) 참고.
데이터 적재·검증 절차(A 담당)는 [docs/A_논문DB구축_가이드.md](../docs/A_논문DB구축_가이드.md) 참고.

에러 응답은 전부 `{"error": "...", "detail": "..."}` 형태입니다.

| status | error | 상황 |
|---|---|---|
| 404 | `NOT_FOUND` | 논문/chunk 없음 |
| 400 | `BAD_REQUEST` | 잘못된 파라미터 |
| 503 | `MODEL_UNAVAILABLE` | Ollama 미기동 |
| 500 | `DATABASE_ERROR` | DB 접근 실패 |

### MCP 서버

SSE 전송 방식으로 노출됩니다.

- 연결: `GET /sse`
- 요청: `POST /mcp/message?sessionId=...`

등록 tool 4종: `SearchPaperChunk`, `FindCodeImplementation`, `QueryMetadataSQL`, `CurateContext`.
`application.yml`의 `spring.ai.mcp.server.protocol`을 `STREAMABLE`로 바꾸면 단일 엔드포인트 `POST /mcp`를 씁니다.

---

## 패키지 구조

```
com.codeatlas.backend
├── agent/          AgentQueryController      — 사전계산 조회 + 라이브 폴백 (B)
│                   MappingReadService        — paper_code_mappings 조회 (B)
│                   CurationBatchService      — 사전계산 배치 (B)
│                   AdminCurationController   — 배치 트리거 (B)
├── nl2sql/         Nl2SqlController          — 자연어 SQL API (B)
│                   MetadataSqlService        — SQL 생성 + 실행 (B)
│                   ReadOnlySqlGuard          — read-only 검증 (B)
├── mcp/
│   ├── dto/        McpDtos                   — A↔B 공용 DTO 계약
│   ├── port/       CodeAtlasPorts            — A↔B 인터페이스 계약
│   └── tools/      MCP tool 4종              — (B)
├── paper/          PaperChunkSearchService   — chunk 벡터 검색 (A)
│                   PaperCatalogService/Controller
├── mapping/        CodeSearchService         — 코드 매핑 검색 (A)
│                   MappingController
├── embedding/      VectorSupport             — pgvector 바인딩
│                   EmbeddingBackfillRunner   — seed 임베딩 채우기(임시)
├── common/         LlmText, NotFoundException, ApiExceptionHandler
└── config/         WebCorsConfig
```

A/B 경계는 `mcp/port/CodeAtlasPorts`의 인터페이스입니다. A는 `paper`/`mapping`의 구현체만
바꾸면 되고, B의 MCP tool 코드는 손대지 않아도 됩니다.

---

## DB

```
database/Script-2.sql            A가 확정한 스키마 (papers, paper_chunks, repositories,
                                 paper_repositories, code_blocks, paper_code_mappings)
database/Script-3_pgvector.sql   pgvector 확장 + embedding vector(768) 컬럼 + HNSW 인덱스
database/seed_demo.sql           데모용 임시 데이터 (A의 seed_dump.sql이 나오면 교체)
```

스키마를 바꿨다면 볼륨을 지우고 다시 띄워야 초기화 스크립트가 재실행됩니다.

```bash
docker compose down -v && docker compose up -d
```

> DB schema 변경은 **A 승인 필요** (팀 병합 규칙).

---

## 임베딩

- 모델: `nomic-embed-text` (768차원) → `Script-3_pgvector.sql`의 `vector(768)`와 일치해야 합니다.
- **A의 Python 파이프라인도 반드시 같은 모델을 Ollama HTTP API(`POST /api/embed`)로 호출**해야 합니다.
  모델이 다르면 벡터 공간이 달라져 `<=>` 유사도 계산 자체가 무의미해집니다.
- 이어붙이는 텍스트도 파이프라인과 맞춰야 합니다.
  - 논문 chunk: `section_title + subsection_title + content`
  - 코드 block: `file_path + parent_symbol_name + symbol_name + code_content`

코드 block 조합은 demo seed 6쌍으로 비교해 고른 잠정값입니다.

| 조합 | Top-1 |
|---|---|
| `parent + symbol + symbol_type + code` | 3/6 |
| `parent + symbol + code` | 4/6 |
| `file_path + parent + symbol + code` (채택) | **5/6** |

표본이 6쌍뿐이라 로드맵 2주차의 정답셋 30쌍으로 A가 Top-1/3·MRR을 다시 측정해 확정해야 합니다.

`EmbeddingBackfillRunner`는 A의 파이프라인이 임베딩을 채우게 되면 삭제해도 되는 임시 유틸리티입니다.

---

## NL2SQL 안전장치

`ReadOnlySqlGuard` + read-only 트랜잭션으로 4중 방어합니다.

1. `SELECT`로 시작하는지 검사
2. DDL/DML 키워드 블록리스트 — **단어 경계 기준**
   (단순 `contains` 검사는 `ORDER BY created_at`의 `CREATE`를 오탐해 정상 쿼리를 막습니다)
3. 세미콜론(다중 구문)/주석(`--`, `/* */`) 차단, `LIMIT` 없으면 100행 상한
4. read-only 트랜잭션에서만 실행 → PostgreSQL이 쓰기 자체를 거부

노출 대상은 metadata 3종(`papers`, `repositories`, `paper_repositories`)뿐입니다.
`authors` JSONB와 다대다 조인 힌트를 프롬프트에 넣어, 아래 같은 질의가 실제로 동작합니다.

```sql
-- "Ashish Vaswani가 저자인 논문 제목"
SELECT title FROM papers WHERE authors @> '[{"name": "Ashish Vaswani"}]'::jsonb LIMIT 100
```

> 운영 배포 시에는 SELECT 권한만 가진 별도 DB 계정으로 NL2SQL 전용 DataSource를 분리하는 것을 권장합니다.

qwen3는 reasoning 모델이라 응답에 `<think>...</think>` 블록이 섞여 나옵니다.
`LlmText.stripThinking()`으로 SQL·설명 텍스트 양쪽에서 제거합니다.

---

## 테스트

```bash
./mvnw test        # DB/Ollama 없이 전부 통과 (30개)
```

인프라가 필요한 통합 확인은 `../scripts/smoke.sh`로 합니다.

---

## 설정

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `CODEATLAS_DB_URL` | `jdbc:postgresql://localhost:5433/codeatlas` | DB 접속 URL |
| `CODEATLAS_DB_USER` / `CODEATLAS_DB_PASSWORD` | `codeatlas` | DB 계정 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 주소 |
| `CODEATLAS_EMBEDDING_BACKFILL` | `false` | 기동 시 빈 embedding 채우기 |

CORS는 `codeatlas.cors.allowed-origins` (기본 `localhost:5173`, `localhost:4173`)로 관리합니다.
