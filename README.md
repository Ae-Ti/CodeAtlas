# CodeAtlas

**논문의 한 단락을 고르면, 그 내용을 실제로 구현한 코드 위치를 찾아줍니다.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Java 21](https://img.shields.io/badge/Java-21-orange)
![Spring Boot 4.1](https://img.shields.io/badge/Spring%20Boot-4.1-6DB33F)
![React 19](https://img.shields.io/badge/React-19-61DAFB)
![PostgreSQL 17 + pgvector](https://img.shields.io/badge/PostgreSQL-17%20%2B%20pgvector-336791)
![Ollama local](https://img.shields.io/badge/AI-Ollama%20local%20(open--weight)-000000)

> 2026 오픈소스 개발자대회 자유과제(인공지능 분야) 출품작 · 2인 팀
> 상용 AI API 를 호출하는 경로가 없습니다. 생성·임베딩 모델 모두 **오픈웨이트 로컬 구동**입니다.

---

## 1. 무엇을 해결하나

논문을 읽다 "이 수식이 코드로는 어디에 있지?"에서 막힙니다. 저장소를 클론해서 파일을 뒤지는
수밖에 없고, 논문 용어(`scaled dot-product attention`)와 코드 심볼(`ScaledDotProductAttention.forward`)이
같은 단어를 쓰지 않기 때문에 grep 도 잘 듣지 않습니다.

이 문제를 자동으로 풀어주던 **Papers with Code 는 2025년 7월 서비스가 종료**됐습니다.
남은 서비스들(arXiv Trending 등)은 "어떤 논문에 코드가 있는가"까지만 알려주고,
**논문 안의 어느 단락이 코드의 어느 함수에 해당하는가**는 다루지 않습니다.

CodeAtlas 는 그 마지막 한 칸을 채웁니다.

```
  Attention Is All You Need — §3.2.2 Multi-Head Attention

    "In this work we employ h=8 parallel attention layers, or heads.
     For each of these we use d_k = d_v = d_model/h = 64."

              │   pgvector 코사인 거리  →  TACC 선별  →  Qwen3 설명 생성
              ▼

  attention-is-all-you-need-pytorch — transformer/SubLayers.py:12-27

    class MultiHeadAttention(nn.Module):
        def __init__(self, n_head, d_model, d_k, d_v, dropout=0.1):
            self.w_qs = nn.Linear(d_model, n_head * d_k, bias=False)
            self.attention = ScaledDotProductAttention(temperature=d_k ** 0.5)
            ...
```

*(꾸며낸 예시가 아니라 실제 적재된 데이터입니다 — `paper_chunks.id=19` ↔ `code_blocks.id=13`)*

---

## 2. 어떻게 동작하나

```
① 적재
     논문 PDF + GitHub 저장소
       └─▶ scripts/ingest.py  (섹션 분할 · AST 파싱)
             └─▶ PostgreSQL 17 + pgvector
                   papers · paper_chunks · repositories · code_blocks
                   embedding vector(768) — nomic-embed-text

② 사전계산   POST /api/admin/curate-pending
     1. CodeSearchService  — pgvector 코사인 거리로 코드 후보 Top-K
     2. CurateContext      — TACC: 중복 제거 후 근거가 되는 후보만 선별
     3. Qwen3              — "왜 이 코드인가" 설명 생성
       └─▶ paper_code_mappings 에 저장

③ 조회       POST /api/agent/query
     1. paper_code_mappings 조회 → 있으면 즉시 반환    source="precomputed"   0.049초
     2. 없으면 ②를 그 자리에서 실행 (라이브 폴백)      source="live"          27.3초

④ 표면
     React 19 대시보드  — Monaco 코드 뷰어 · React Flow 연결 그래프
     MCP 서버 (SSE)     — SearchPaperChunk · FindCodeImplementation
                          QueryMetadataSQL · CurateContext
```

**왜 사전계산인가.** 매 요청마다 로컬 LLM 을 부르면 27초가 걸리고, 시연 중 Ollama 가 한 번
멈추면 그대로 장애가 됩니다. 큐레이션된 논문은 미리 계산해 두고 신규·ad-hoc 질의만 라이브로
처리합니다. 실측 **27.3초 → 0.049초** (M4 macOS).

**순위를 정하는 것은 LLM 이 아닙니다.** 후보 순위는 pgvector 코사인 거리로 결정되고,
LLM 은 선별된 후보에 대한 *설명*만 생성합니다. 근거는
[AI_모델_활용_명세.md](docs/AI_모델_활용_명세.md) 를 참고하세요.

---

## 3. 로컬에서 띄우기

### 사전 준비

| 도구 | 버전 | 확인 |
|---|---|---|
| Docker | Compose v2 | `docker compose version` |
| JDK | 21 | `java -version` (Maven 은 `./mvnw` 동봉) |
| Node.js | 20.19+ | `node -v` |
| Python | 3.9+ | `python3 -V` (적재 스크립트용, 추가 패키지 없음) |
| Ollama | 최신 | `ollama -v` |

### 실행

3~5번은 각각 서버를 붙잡고 있으므로 **터미널을 따로 열어야 합니다.**

```bash
git clone https://github.com/Ae-Ti/CodeAtlas.git && cd CodeAtlas

# 1) DB — pgvector 컨테이너가 localhost:5433 에 뜨고 스키마·데모 데이터가 자동 적재됩니다
docker compose up -d

# 2) AI 모델 (최초 1회, 합계 수 GB 다운로드)
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve                                              # localhost:11434  [터미널 A]

# 3) 백엔드 — 최초 1회는 임베딩 backfill 을 켜고 기동합니다
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run  # localhost:8080   [터미널 B]

# 4) 프론트엔드
cd frontend && npm install && npm run dev                 # localhost:5173   [터미널 C]

# 5) (선택) 큐레이션 사전계산 — chunk 당 Qwen3 1회, 376 chunk 기준 약 100분
curl -X POST localhost:8080/api/admin/curate-pending      #                  [터미널 D]
```

여기까지 하면 `localhost:5173` 에서 화면이 뜹니다. 모델 다운로드를 빼면 몇 분,
5번 큐레이션까지 포함하면 100분쯤 걸립니다. **논문을 하나 더 추가할 때는 그 논문의
단락만 처리하므로 약 11분입니다** — 전체 재구축과 별개입니다.

### 확인

```bash
./scripts/doctor.sh     # 도구·DB·모델·백엔드를 한 번에 점검하고, 빠진 것은 채우는 법을 알려줍니다
./scripts/smoke.sh      # 기동된 서버의 전체 API 를 한 번씩 호출 (8종)
cd backend && ./mvnw test    # DB·Ollama 없이 전부 통과 (32개)
```

> **포트 5433 을 씁니다.** 로컬에 이미 PostgreSQL 이 5432 에 떠 있는 경우가 많아 옮겨
> 두었습니다. 바꾸려면 `docker-compose.yml` 과 `backend/src/main/resources/application.yml` 을
> 함께 수정하세요.

> **5번을 건너뛰어도 화면은 동작합니다.** 사전계산이 없는 단락은 라이브 경로로 폴백하며,
> 대신 응답에 수십 초가 걸리고 `live` 배지가 붙습니다.
> 배치는 동시 실행이 차단되어 있습니다 — 다시 부르기 전에 `GET /api/admin/curate-status`
> 로 진행 중인지 확인하세요. `curl` 을 Ctrl-C 해도 서버 배치는 멈추지 않습니다.

### 새 논문 적재하기

```bash
./scripts/reset_db.sh                                              # 스키마 초기화 (데모 데이터 제거)
python3 scripts/ingest.py database/ingest/<논문>.json --dry-run     # 형식 검증만, DB 는 안 건드림
python3 scripts/ingest.py database/ingest/<논문>.json --insert-mappings
# → 임베딩 backfill(3번) → 큐레이션(5번) 순서로 다시 실행
```

입력 JSON 형식과 전체 절차는 [docs/A_논문DB구축_가이드.md](docs/A_논문DB구축_가이드.md) 에 있습니다.

---

## 4. 화면

| 화면 | 하는 일 | 사용 API |
|---|---|---|
| Dashboard | 적재 현황, 최근 매핑 | `GET /api/stats`, `GET /api/mappings` |
| Papers | 논문 목록 | `GET /api/papers` |
| PaperDetail | 단락 클릭 → 대응 코드 Top-5, Monaco 뷰어로 해당 줄 하이라이트 | `GET /api/papers/{id}/chunks`, `POST /api/mapping/search`, `POST /api/agent/query` |
| Agent | 자연어 질의 → chunk 검색 → 매핑, NL2SQL 메타데이터 조회 | `POST /api/papers/chunks/search`, `POST /api/agent/query`, `POST /api/nl2sql` |
| Graph | 논문–코드 연결을 React Flow 그래프로 | `GET /api/mappings?limit=60` |

응답의 `precomputed` / `live` 배지는 그 결과가 사전계산된 매핑에서 왔는지, 그 자리에서
Qwen3 를 호출한 것인지를 나타냅니다. 자세한 내용은 [frontend/README.md](frontend/README.md).

---

## 5. API

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/papers` | 논문 목록 |
| `GET` | `/api/papers/{paperId}/chunks` | 논문 단락 목록 |
| `POST` | `/api/papers/chunks/search` | 자연어 → 단락 벡터 검색 |
| `POST` | `/api/mapping/search` | 단락 → 코드 Top-K (AI 설명 없음) |
| `POST` | `/api/agent/query` | 사전계산 조회 + 라이브 폴백 |
| `POST` | `/api/nl2sql` | 자연어 → read-only SQL 조회 |
| `GET` | `/api/stats`, `/api/mappings` | 대시보드·그래프용 집계 |
| `POST` | `/api/admin/curate-pending` | 큐레이션 배치 트리거 |
| `GET` | `/api/admin/curate-status` | 배치 진행률 |

**MCP 서버** — SSE 전송. 연결 `GET /sse`, 요청 `POST /mcp/message?sessionId=...`
등록 tool 4종: `SearchPaperChunk`, `FindCodeImplementation`, `QueryMetadataSQL`, `CurateContext`.

요청·응답 스키마 전문은 [docs/api-spec.md](docs/api-spec.md), 구현 구조는
[backend/README.md](backend/README.md) 를 보세요.

**NL2SQL 은 4중으로 막혀 있습니다** — `SELECT` 시작 검사, 단어 경계 기준 DDL/DML 블록리스트,
세미콜론·주석 차단과 100행 상한, read-only 트랜잭션. 노출 테이블도 메타데이터 3종뿐입니다.

---

## 6. 검색 품질

논문 9편에 대해 손으로 만든 정답셋 **315쌍**(논문 단락 ↔ 대응 코드 블록)으로 측정했습니다.
**서비스와 동일한 조건** — 후보를 그 논문에 연결된 저장소로 한정(단락당 평균 22블록),
순수 pgvector 코사인 정렬입니다.

| 지표 | 값 | 무작위 선택 시 | 배수 |
|---|---|---|---|
| Top-1 | 28.6% (90/315) | 5.0% | **5.7×** |
| Top-3 | 52.4% (165/315) | 15.1% | **3.5×** |
| **Top-5** | **65.1% (205/315)** | 25.2% | **2.6×** |
| MRR | 0.4173 | — | — |

**Top-5 가 제품과 맞는 지표입니다** — 화면이 후보 5개를 함께 보여주고 사용자는 그중에서
고릅니다. 근거(파일 경로·줄 번호·원본 GitHub 링크)를 함께 제시하므로 5개 중 고르는 비용이
저장소를 직접 뒤지는 것보다 훨씬 낮습니다.

### 측정 조건에 대하여

지표를 부풀리지 않기 위해 아래를 명시합니다.

- **정답셋은 저자가 수동 검수한 것**입니다. 논문 단락 376개 중 코드가 대응하는 315개가
  대상이며, 나머지 61개(실험 결과·Figure·저장소에 없는 기능)는 **일부러 비워 두었습니다.**
  억지로 코드를 붙이면 정답셋 자체가 오염됩니다.
- **랜덤 하한은 단락별 실제 후보 수로 계산**했습니다. 후보를 논문 범위로 좁히면 무작위
  적중률이 올라가므로, 전체 코퍼스(183블록) 기준으로 계산하면 배수가 부풀려집니다.
- **랭킹 함수 자체는 아직 개선하지 않았습니다.** 어휘 신호를 결합한 하이브리드 검색은
  측정만 해두고 적용하지 않았습니다 ([#18](https://github.com/Ae-Ti/CodeAtlas/issues/18)).

> 이전 문서의 43쌍 수치(Top-5 69.8%)와는 조건이 다릅니다. 그때는 논문 1편·후보 33블록이었고
> 지금은 9편입니다. 측정 이력과 판단 근거는
> [2026-08-12 정리](docs/2026-08-12_논문9편_확장_및_검색범위_교정.md) ·
> [2026-08-11 정리](docs/2026-08-11_정답셋_43쌍_확장_및_평가지표_정비.md) 에 있습니다.

### 재현

정답셋은 DB id 가 아니라 안정 키(`arxiv_id`, `chunk_index`, `github_url`, `file_path`,
`symbol_name`, `start_line`)로 저장돼 있어, 적재 순서가 달라도 같은 결과가 나옵니다.

```bash
python3 scripts/note2ingest/eval_set_tool.py resolve database/eval_set_bert.csv /tmp/bert.csv
python3 scripts/eval_retrieval.py /tmp/bert.csv --k 5
```

---

## 7. AI 모델 — 오픈웨이트 로컬 구동

| 용도 | 모델 | 라이선스 | 실행 |
|---|---|---|---|
| 생성 (연결 근거 설명, NL2SQL) | `qwen3:8b` | Apache 2.0 | Ollama 로컬 |
| 임베딩 (768차원) | `nomic-embed-text` | Apache 2.0 | Ollama 로컬 |

런타임에 상용 AI API 를 호출하는 경로가 없습니다. 라이선스는 `ollama /api/show` 로 실측
확인했습니다. 활용 지점·안전장치·재현 방법은 [docs/AI_모델_활용_명세.md](docs/AI_모델_활용_명세.md).

> 임베딩 모델을 바꾸면 벡터 공간이 달라져 기존 데이터와의 유사도 계산이 무의미해집니다.
> 파이프라인과 백엔드가 **같은 모델**을 쓰는지 반드시 확인하세요.

---

## 8. 저장소 구조

```
CodeAtlas/
├── backend/          Spring Boot 4.1 / Java 21 — REST API + MCP 서버
│   └── src/main/java/com/codeatlas/backend/
│       ├── agent/      사전계산 조회 · 라이브 폴백 · 큐레이션 배치   (B)
│       ├── nl2sql/     자연어 → read-only SQL + 4중 안전장치        (B)
│       ├── mcp/        MCP tool 4종 + A↔B 포트 인터페이스 계약      (B)
│       ├── paper/      논문·단락 조회, 단락 벡터 검색                (A)
│       ├── mapping/    코드 매핑 검색 (pgvector 코사인)             (A)
│       └── embedding/  pgvector 바인딩, 임베딩 backfill
├── frontend/         React 19 / TypeScript / Vite — 화면 5종        (B)
├── database/         스키마(Script-2), pgvector(Script-3), 데모 seed, 적재 JSON, 정답셋 CSV
├── scripts/          doctor.sh · smoke.sh · reset_db.sh · ingest.py · eval_retrieval.py
├── docs/             기획서 · API 명세 · 역할분담 · 데이터 검수 · 평가 기록
└── docker-compose.yml
```

A/B 경계는 `mcp/port/CodeAtlasPorts` 의 인터페이스입니다. 검색 구현이 바뀌어도
MCP tool 코드는 손대지 않습니다.

---

## 9. 문서

| 문서 | 내용 |
|---|---|
| [docs/CodeAtlas_기획서.md](docs/CodeAtlas_기획서.md) | 프로젝트 목적, 로드맵, 컴플라이언스 체크리스트 |
| [docs/api-spec.md](docs/api-spec.md) | REST·MCP tool 전체 스펙 (A↔B 인터페이스 계약) |
| [docs/AI_모델_활용_명세.md](docs/AI_모델_활용_명세.md) | 사용 모델, 라이선스, 활용 지점, 재현 방법 |
| [docs/A_논문DB구축_가이드.md](docs/A_논문DB구축_가이드.md) | 논문 적재 JSON 형식과 전체 절차 |
| [docs/CodeAtlas_팀_역할분담.md](docs/CodeAtlas_팀_역할분담.md) | RACI, 코드 소유권 경계, 브랜치 전략 |
| [docs/데이터_검수_리포트.md](docs/데이터_검수_리포트.md) · [회신](docs/데이터_검수_리포트_회신.md) | 적재 데이터 상호 검수 기록 |
| [docs/2026-08-11 정리](docs/2026-08-11_정답셋_43쌍_확장_및_평가지표_정비.md) | 평가 지표 확장, 하이브리드 검색 실험 |
| [backend/README.md](backend/README.md) · [frontend/README.md](frontend/README.md) | 각 모듈 실행·구조 |

---

## 10. 데이터 출처와 라이선스

본 저장소의 코드는 [MIT License](LICENSE) 입니다. 인덱싱 대상 자료의 출처는 아래와 같습니다.

**적재 현황** (2026-08-12 기준)

| | |
|---|---|
| 논문 | **9편** (Attention, BERT, ResNet, YOLO, ViT, CLIP, Latent Diffusion, SAM, Llama 3) |
| 단락 | 376개 — 쪽 번호 100%, 논문 원문 대조 99.2% |
| 코드 블록 | **183개** / 저장소 **12곳** |
| 매핑 | 수동 검증 344건 + AI 생성 1,667건 |

전량이 실데이터입니다. 데모용 임시 데이터는 포함돼 있지 않습니다.

### 인덱싱 대상 저장소

| 저장소 | 라이선스 | 코드 블록 |
|---|---|---|
| [jadore801120/attention-is-all-you-need-pytorch](https://github.com/jadore801120/attention-is-all-you-need-pytorch) | MIT | 33 |
| [CompVis/latent-diffusion](https://github.com/CompVis/latent-diffusion) | MIT | 21 |
| [google-research/bert](https://github.com/google-research/bert) | Apache-2.0 | 18 |
| [pjreddie/darknet](https://github.com/pjreddie/darknet) | YOLO LICENSE v2 (public-domain style) | 18 |
| [pytorch/vision](https://github.com/pytorch/vision) | BSD-3-Clause | 18 |
| [facebookresearch/segment-anything](https://github.com/facebookresearch/segment-anything) | Apache-2.0 | 16 |
| [KaimingHe/deep-residual-networks](https://github.com/KaimingHe/deep-residual-networks) | MIT | 14 |
| [openai/CLIP](https://github.com/openai/CLIP) | MIT | 13 |
| [google-research/vision_transformer](https://github.com/google-research/vision_transformer) | Apache-2.0 | 12 |
| [meta-llama/llama3](https://github.com/meta-llama/llama3) | Meta Llama 3 Community License | 10 |
| [lucidrains/vit-pytorch](https://github.com/lucidrains/vit-pytorch) | MIT | 6 |
| [mlfoundations/open_clip](https://github.com/mlfoundations/open_clip) | MIT | 4 |

| 그 밖의 자료 | 출처 | 라이선스 |
|---|---|---|
| 논문 본문·메타데이터 | [arXiv](https://arxiv.org) | 논문별 원저작자 표기 유지 |
| 논문↔저장소 후보 소싱 | Papers with Code 아카이브 데이터셋 | CC-BY-SA-4.0 |

라이선스는 GitHub API(`GET /repos/{owner}/{repo}`)로 실측 확인했으며, **라이선스가 명시되지
않은 저장소는 인용 대상에서 제외**했습니다. 코드 블록은 원 저장소의 파일 경로·줄 번호,
참조한 커밋 해시와 함께 저장되며 화면에서 항상 원본 GitHub 링크를 제시합니다.

전문 고지는 [`NOTICE`](NOTICE) 와 [`database/THIRD_PARTY_LICENSES.md`](database/THIRD_PARTY_LICENSES.md)
에 있습니다. Meta Llama 3 Community License §1.b.i(B)가 요구하는 "Built with Meta Llama 3"
표시는 화면 하단에 상시 노출합니다.

> **이 절은 "우리가 코드를 인용해 보여주는 저장소"입니다.** CodeAtlas 가 동작하기 위해
> *의존하는* 라이브러리 271개는 성격이 다르며 [docs/오픈소스SW_목록.md](docs/오픈소스SW_목록.md)
> 와 [`sbom/`](sbom/) 에 별도로 정리했습니다.

---

## 11. 팀

2인 팀입니다. AI 기능이 한 명에게 몰리지 않도록 **"찾는 AI"와 "판단하고 보여주는 AI"** 로
나눴습니다.

| | 역할 | 담당 |
|---|---|---|
| [UngsikJo](https://github.com/UngsikJo) | Knowledge Retrieval Engineer | 논문·코드 수집과 파싱, 임베딩, pgvector 검색, 평가 정답셋 |
| [Taeil Bae](https://github.com/Ae-Ti) | Agent & AI Product Engineer | MCP 도구, TACC 선별, NL2SQL, React 대시보드, 시연 |

상세한 RACI 와 코드 소유권 경계는 [docs/CodeAtlas_팀_역할분담.md](docs/CodeAtlas_팀_역할분담.md).
기여 방법을 정리한 `CONTRIBUTING.md` 는 작성 중입니다.

---

## 12. 대회 제출물

| 제출물 | 위치 | 상태 |
|---|---|---|
| 소스코드 (Public repo) | 본 저장소 | ✅ |
| LICENSE (MIT) | [LICENSE](LICENSE) | ✅ |
| AI 모델 활용 명세 | [docs/AI_모델_활용_명세.md](docs/AI_모델_활용_명세.md) | ✅ |
| README (실행 가능 수준) | 본 문서 | ✅ |
| 결과보고서 | — | 작성 예정 |
| 시연영상 (3분 이내) | — | 촬영 예정 |
| SBOM / 오픈소스SW 목록 | [docs/오픈소스SW_목록.md](docs/오픈소스SW_목록.md) · [sbom/](sbom/) | ✅ |
| CONTRIBUTING.md | — | 작성 예정 |
| `seed_dump.sql` / `seed_manifest.csv` | [database/](database/) | ✅ |
| 확장 기능·발전 방향 | [docs/CodeAtlas_확장기능.md](docs/CodeAtlas_확장기능.md) | ✅ |
| 데모 시나리오 | `docs/demo-scenario.md` | 작성 예정 |
| 정부 지원사업 중복수혜 여부 확인서 | — | 해당 여부 확인 중 |

진행 상황은 [Issues](https://github.com/Ae-Ti/CodeAtlas/issues) 에서 추적합니다.
