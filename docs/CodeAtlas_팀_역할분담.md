# CodeAtlas 팀 역할분담

## 핵심 원칙

> **A는 "찾는 AI"를 만들고, B는 "판단하고 보여주는 AI"를 만든다.**

| 팀원 | 역할 | AI 관점 |
|---|---|---|
| 팀원 A | Knowledge Retrieval Engineer | 논문/코드 임베딩, pgvector 검색 |
| 팀원 B | Agent & AI Product Engineer | MCP, NL2SQL, TACC, 시각화 |

---

## 팀원 A — Knowledge Retrieval Engineer

**핵심 질문:** 논문 설명과 코드 구현을 어떤 단위로 쪼개고, 어떤 벡터로 저장하고, 어떻게 유사한 코드를 찾을 것인가?

### 담당 범위

| 구분 | 작업 |
|---|---|
| 논문 데이터 | arXiv 논문 metadata 수집, PDF 텍스트 추출 |
| 논문 chunking | 섹션 단위 분리, 500~800 token chunk 생성 |
| 코드 데이터 | GitHub repo clone, Python 코드 파일 수집 |
| 코드 parsing | 함수, 클래스, docstring, start/end line 추출 |
| embedding | 논문 chunk & 코드 block embedding 생성 |
| pgvector | PostgreSQL + pgvector 저장 및 유사도 검색 |
| 검색 API | 논문 chunk → 관련 코드 Top-K 반환 |
| 평가 | 수동 정답 매핑셋 제작, Top-1/3 Accuracy 계산 |

### 최종 산출물

| 산출물 | 설명 |
|---|---|
| `papers` 테이블 | 논문 metadata |
| `paper_chunks` 테이블 | 논문 section/chunk + embedding |
| `repositories` 테이블 | GitHub repo metadata |
| `code_blocks` 테이블 | 함수/클래스 단위 코드 + embedding |
| `GET /api/papers` | 논문 목록 API |
| `GET /api/papers/{id}/chunks` | 논문 chunk 조회 API |
| `POST /api/mapping/search` | 논문 chunk 기반 코드 검색 API |
| 평가 결과 | Top-1, Top-3, MRR, 응답시간 |

### 학습 우선순위

| 순위 | 영역 | 목표 |
|---|---|---|
| 1 | PostgreSQL + pgvector | vector 저장, cosine similarity 검색 |
| 2 | Python PDF parsing | PyMuPDF로 논문 텍스트 추출 |
| 3 | Python AST | 함수, 클래스, docstring 추출 |
| 4 | SentenceTransformer | embedding 생성 |
| 5 | Spring Boot API | 검색 결과 JSON 반환 |
| 6 | 검색 품질 개선 | vector similarity + keyword overlap 결합 |
| 7 | 평가 지표 | Top-K Accuracy, MRR 계산 |

---

## 팀원 B — Agent & AI Product Engineer

**핵심 질문:** 검색된 후보 중 무엇을 최종 근거로 선택하고, 사용자가 이해할 수 있게 어떻게 설명할 것인가?

### 담당 범위

| 구분 | 작업 |
|---|---|
| MCP Agent | MCP tool 구조 설계 및 호출 흐름 구현 |
| MCP Parallel | SearchPaperChunk, FindCodeImplementation, QueryMetadataSQL 병렬 실행 |
| TACC | 검색 후보 context 선별, 중복 제거, 최종 context 구성 |
| NL2SQL | 자연어 질의 → read-only SQL 변환 |
| AI 응답 생성 | 연결 근거, 코드 추천 이유 설명 |
| React UI | 논문-코드 매핑 시연 화면 |
| 코드 뷰어 | Monaco Editor 코드 하이라이트 |
| Agent UI | MCP tool 실행 상태, TACC 결과 표시 |
| 발표 시연 | 데모 시나리오, 시연영상, 발표자료 구성 |

### 최종 산출물

| 산출물 | 설명 |
|---|---|
| `SearchPaperChunk` Tool | 논문 chunk 검색 도구 |
| `FindCodeImplementation` Tool | 관련 코드 검색 도구 |
| `QueryMetadataSQL` Tool | 논문/repo metadata SQL 조회 도구 |
| `CurateContext` Tool | TACC context 선별 도구 |
| `POST /api/agent/query` | MCP Agent 질의 API |
| `POST /api/nl2sql` | 자연어 SQL 질의 API |
| React 대시보드 | 논문 섹션, 코드, 연결 근거 표시 |
| 발표 시연 흐름 | 3개 demo scenario |

### 학습 우선순위

| 순위 | 영역 | 목표 |
|---|---|---|
| 1 | Spring AI MCP | tool 등록, tool 호출 구조 이해 |
| 2 | MCP Parallel 패턴 | 여러 tool 병렬 실행 구조 |
| 3 | TACC | context ranking, deduplication, selection |
| 4 | NL2SQL | 자연어를 제한된 SQL로 변환 |
| 5 | React + TypeScript | 시연 UI 구현 |
| 6 | Monaco Editor | 코드 하이라이트 |
| 7 | React Flow | 논문-코드 연결 시각화 |
| 8 | 발표 설계 | 심사위원이 바로 이해하는 시연 구성 |

---

## A↔B 인터페이스 계약 (API Spec)

> **핵심:** API 명세를 먼저 고정해야 둘이 동시에 개발할 수 있다.

### 1. 논문 목록 조회

`GET /api/papers`

```json
[
  {
    "paperId": 1,
    "title": "Attention Is All You Need",
    "authors": "Vaswani et al.",
    "task": "NLP",
    "pdfUrl": "https://arxiv.org/pdf/1706.03762"
  }
]
```

### 2. 논문 chunk 조회

`GET /api/papers/{paperId}/chunks`

```json
[
  {
    "chunkId": 101,
    "sectionTitle": "Multi-Head Attention",
    "chunkType": "method",
    "chunkText": "Multi-head attention allows the model..."
  }
]
```

### 3. 논문 chunk 기반 코드 검색

`POST /api/mapping/search`

```json
// Request
{ "paperId": 1, "chunkId": 101, "topK": 5 }

// Response
{
  "queryChunk": {
    "sectionTitle": "Multi-Head Attention",
    "chunkText": "Multi-head attention allows..."
  },
  "results": [
    {
      "codeBlockId": 501,
      "repoName": "annotated-transformer",
      "filePath": "model/attention.py",
      "className": "MultiHeadedAttention",
      "functionName": "forward",
      "startLine": 42,
      "endLine": 89,
      "codeText": "def forward(self, query, key, value, mask=None): ...",
      "similarityScore": 0.87,
      "githubUrl": "https://github.com/..."
    }
  ]
}
```

---

## Mock 우선 전략

B는 A의 백엔드가 완성될 때까지 기다리지 않는다. **1주차부터 mock JSON으로 화면을 먼저 만든다.**

```json
{
  "queryChunk": {
    "sectionTitle": "Multi-Head Attention",
    "chunkText": "Multi-head attention allows the model to jointly attend..."
  },
  "results": [
    {
      "repoName": "annotated-transformer",
      "filePath": "model/attention.py",
      "functionName": "forward",
      "codeText": "def forward(self, query, key, value, mask=None): ...",
      "similarityScore": 0.87,
      "explanation": "The selected code implements scaled dot-product attention..."
    }
  ],
  "tacc": {
    "initialContexts": 20,
    "removedContexts": 15,
    "selectedContexts": 5
  },
  "mcpTools": [
    { "toolName": "SearchPaperChunk", "status": "done", "latencyMs": 410 },
    { "toolName": "FindCodeImplementation", "status": "done", "latencyMs": 620 }
  ]
}
```

---

## 코드 소유권 경계

### A 전담 영역

```
data-pipeline/
backend/src/.../paper
backend/src/.../code
backend/src/.../embedding
backend/src/.../mapping
database/schema.sql
```

### B 전담 영역

```
frontend/
backend/src/.../agent
backend/src/.../nl2sql
backend/src/.../tacc
backend/src/.../mcp
```

### 공동 관리

```
backend/src/.../api
docs/api-spec.md
README.md
docker-compose.yml
```

---

## 브랜치 전략

```
main
 └── develop
      ├── feature/retrieval-pipeline    → A
      ├── feature/vector-search-api     → A
      ├── feature/agent-mcp             → B
      ├── feature/nl2sql-tacc           → B
      ├── feature/frontend-dashboard    → B
      └── feature/demo-deploy           → B 주도, A 보조
```

### 병합 규칙

- `main`에는 최종 안정 버전만 merge
- 개발은 `develop` 기준, 기능 브랜치는 하루 1회 PR
- PR 시 "API 변경 여부" 반드시 명시
- DB schema 변경 → A 승인 필요
- API response 변경 → B 확인 후 merge

---

## 5주 로드맵

### 1주차 — 계약 먼저 잡기

| 팀원 | 작업 |
|---|---|
| A | DB schema 초안, 논문 seed CSV 10개, PDF 추출 테스트, 코드 block 추출 방식 결정 |
| B | 화면 와이어프레임, API 명세 문서, MCP Tool 목록 정의, React 프로젝트 생성 |
| 공동 | API response schema 합의, demo 논문 3개 선정, repo 구조 확정 |

**완료 기준:** A는 논문 5개 DB 적재 / B는 mock data로 화면 구동 / 실제 API 없이 병렬 개발 가능

### 2주차 — Retrieval 엔진 + UI 병렬 개발

| 팀원 | 작업 |
|---|---|
| A | paper_chunks, code_blocks 생성, embedding, pgvector Top-K 검색 구현 |
| B | 논문 리스트/상세 화면, 코드 추천 결과 화면, Monaco Editor 코드 뷰어 |
| 공동 | A API + B UI 1차 통합, demo 1개 end-to-end 확인 |

**완료 기준:** 논문 chunk 클릭 시 관련 코드 Top-5가 화면에 표시

### 3주차 — AI Agent 기능 구현

| 팀원 | 작업 |
|---|---|
| A | keyword overlap 점수 추가, 검색 API 응답속도 개선, demo 논문 10개 확장 |
| B | MCP Tool 3종 구현, TACC 후보 선별 로직, NL2SQL read-only 질의 구현 |
| 공동 | MCP Tool ↔ A 검색 API 연결, TACC 결과 UI 표시, NL2SQL 결과 검증 |

**완료 기준:** MCP tool 3개 이상 실행 / 자연어 질의로 metadata 조회 / TACC 전후 수치 표시

### 4주차 — 시연 완성도 집중

| 팀원 | 작업 |
|---|---|
| A | demo 논문 3개 수동 검수, 정답 매핑셋 30개 제작, Top-1/3 Accuracy 계산, 검색 실패 케이스 보정 |
| B | React Flow 연결 그래프, MCP Parallel 실행 카드, TACC 비교 카드, 발표용 UI polish |
| 공동 | Demo 3개 시나리오 완성, 장애 대비 영상 촬영 |

**완료 기준:** 발표용 3개 시나리오 확정 / 검수된 데이터로 안정적 시연 / 정량 수치 초안 확보

### 5주차 — 문서화 & 제출물 완성

| 팀원 | 작업 |
|---|---|
| A | backend README, API 문서 정리, SBOM 백엔드/AI 라이브러리, AI 모델 활용 명세, 평가 결과 표 |
| B | frontend README, Docker Compose 정리, AWS 배포/로컬 실행 영상, 시연영상 녹화, 보고서 UI 캡처 |
| 공동 | 최종 README 검토, 결과보고서 작성, 발표자료 제작, 제출 전 체크 |

**완료 기준:** GitHub 공개 / README 실행 가능 / 결과보고서 완성 / 시연영상 URL / SBOM / AI 모델 활용 명세

---

## RACI 역할표

| 작업 | A | B |
|---|---|---|
| DB schema 설계 | **R/A** | C |
| 논문 수집 | **R/A** | I |
| PDF parsing | **R/A** | I |
| 코드 parsing | **R/A** | C |
| embedding 생성 | **R/A** | I |
| pgvector 검색 | **R/A** | C |
| 검색 API | **R/A** | C |
| MCP Tool 설계 | C | **R/A** |
| MCP Parallel 구현 | C | **R/A** |
| NL2SQL | C | **R/A** |
| TACC | C | **R/A** |
| React UI | C | **R/A** |
| 코드 뷰어 | C | **R/A** |
| 연결 그래프 | C | **R/A** |
| 평가 지표 | **R/A** | C |
| demo data 검수 | **R/A** | C |
| 시연 시나리오 | C | **R/A** |
| README | R | R |
| SBOM | R | R |
| 결과보고서 | R | R |
| 발표자료 | C | **R/A** |
| 배포 | C | **R/A** |

> R: 실제 작업자 / A: 최종 책임자 / C: 검토·자문 / I: 공유만 받음

---

## 결과보고서용 역할분담 문장

본 프로젝트는 2인 팀의 제한된 개발 기간을 고려하여 AI 기능을 **Retrieval AI**와 **Agent AI**로 분리하여 개발하였다. 팀원 A는 논문 및 코드 데이터를 수집·분할·임베딩하고 PostgreSQL pgvector 기반 유사도 검색 엔진을 구현하였다. 팀원 B는 검색 결과를 활용하는 MCP 기반 병렬 도구 호출 구조, NL2SQL, TACC 기반 context 선별 로직, React 기반 시각화 대시보드를 구현하였다. 이를 통해 한 명에게 AI 기능이 집중되지 않도록 역할을 분산하였으며, API 명세와 mock JSON을 기준으로 병렬 개발을 진행하였다.
