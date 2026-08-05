# 팀원 A — 논문·코드 DB 구축 가이드

> 대상: 팀원 A (Knowledge Retrieval Engineer)
> 전제: **노트 앱에서 논문을 단락으로 나누고, 각 단락에 맞는 코드를 분류하는 중**
> 목표: 그 정리 결과를 DB에 넣고, 검색이 제대로 되는지 확인하는 것까지
> 기준일: 2026.8.6

백엔드·적재 도구·검증 도구는 B가 이미 다 만들어 뒀습니다.
**A는 데이터만 채우면 됩니다.** SQL을 직접 쓸 일도, 임베딩을 직접 만들 일도 없습니다.

---

## 0. 전체 그림

```
[지금 하고 계신 것]                    [이 가이드]
노트 앱                                 
 ├ 논문을 단락으로 분리        ──▶  JSON 한 파일  ──▶  ingest.py  ──▶  DB
 └ 단락별로 코드 분류                    │                              │
                                        │                              ├─ 임베딩 backfill
                                        │                              ├─ AI 큐레이션
   ※ 이 "단락↔코드 분류"가                │                              └─ 검증 (SQL/API/지표)
     그대로 정답셋이 됩니다  ────────────┘
```

**중요:** 지금 하고 계신 단락↔코드 분류는 단순 데이터 입력이 아닙니다.

1. `paper_chunks` / `code_blocks` 데이터
2. **정답 매핑셋** — AI 검색이 맞았는지 채점하는 기준 (로드맵 4주차 산출물)
3. `is_verified = TRUE` 인 **사람 검증 매핑** — 발표 데모에서 "사람이 확인한 연결"로 쓸 수 있음

세 가지가 한 번에 나옵니다. 그래서 노트에 정리할 때 아래 §2 규칙만 지켜주시면 됩니다.

---

## 1. 5분 셋업

```bash
git clone https://github.com/Ae-Ti/CodeAtlas.git
cd CodeAtlas
git checkout develop

# 1) DB (PostgreSQL 17 + pgvector)
docker compose up -d

# 2) 모델 — https://ollama.com 설치 후
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve

# 3) 환경 점검
./scripts/doctor.sh
```

`doctor.sh`가 docker / Java 21 / python3 / DB / pgvector / 임베딩 차원 / Ollama 모델 /
데이터 적재 상태 / 백엔드를 확인하고, **빠진 항목마다 실행할 명령을 같이 출력**합니다.
막히면 항상 이걸 먼저 돌리세요.

```
[2/5] 데이터베이스
  ✅ 컨테이너 'codeatlas-postgres' 실행 중
  ✅ 노출 포트 5433 (접속 URL: jdbc:postgresql://localhost:5433/codeatlas)
  ✅ pgvector 0.8.6
[4/5] 데이터 적재 상태
  papers 0 / chunks 0 / code_blocks 0 / mappings 0
  ⚠️  적재된 논문 없음
     → python3 scripts/ingest.py <파일>.json
```

> ⚠️ **DB 포트는 5432가 아니라 5433입니다.** 로컬에 이미 PostgreSQL이 5432를 쓰고 있으면
> 그쪽으로 붙어버려 `role "codeatlas" does not exist` 에러가 납니다.

---

## 2. 노트 정리 시 지켜야 할 규칙

지금 정리 중인 내용이 그대로 DB 스키마에 들어갑니다. 아래만 맞춰 주세요.

### 논문 단위

| 항목 | 규칙 |
|---|---|
| **arXiv ID** | **필수.** `1706.03762` 형식. 재적재 시 이 값으로 덮어쓰기(upsert)하므로, 같은 논문을 두 번 넣어도 중복이 안 생깁니다 |
| 제목 | 필수 |
| 저자 | 이름 문자열 목록. `["Ashish Vaswani", "Noam Shazeer"]` |
| 초록·PDF URL·발행일 | 선택이지만 화면에 표시되므로 채우는 걸 권장 |

### 단락(chunk) 단위

| 항목 | 규칙 |
|---|---|
| **단락 번호** | **필수.** 논문 안에서 **0부터 순서대로**. 건너뛰거나 중복되면 적재가 거부됩니다 |
| **본문** | **필수.** 500~800 토큰 권장 (너무 짧으면 검색 신호가 약하고, 너무 길면 여러 주제가 섞입니다) |
| 섹션 제목 | `Multi-Head Attention` 처럼. 화면 목록에 그대로 표시되고 임베딩에도 들어갑니다 |
| 하위 섹션 제목 | 있으면 |
| 페이지 | `pageStart` ≤ `pageEnd` |

> **단락을 나누는 기준:** "이 단락 하나에 대응하는 코드를 짚을 수 있는가"입니다.
> 한 단락이 여러 알고리즘을 설명하고 있으면 더 쪼개세요.

### 코드 블록 단위

| 항목 | 규칙 |
|---|---|
| **파일 경로** | **필수.** repo 루트 기준 상대 경로 (`model/attention.py`) |
| **심볼 타입** | **필수.** `FILE` / `CLASS` / `FUNCTION` / `METHOD` / `MODULE` 중 하나. 오타 나면 적재 거부 |
| **코드 본문** | **필수.** 함수/클래스 하나 통째로 |
| 심볼 이름 | 함수·클래스 이름 (`forward`) |
| 상위 심볼 이름 | 메서드면 소속 클래스 (`MultiHeadedAttention`) |
| 시작/끝 줄 | `endLine` ≥ `startLine`. 코드 뷰어 줄 번호에 쓰입니다 |

> 같은 repo 안에서 `(파일경로, 심볼이름, 시작줄)` 조합이 **중복되면 안 됩니다.**

### 단락 ↔ 코드 분류 (지금 하고 계신 것)

각 단락에 대응하는 코드를 **정확한 순서로** 적어 주세요.

> **맨 앞에 적은 코드가 Top-1 정답입니다.** 채점 기준이 되므로 가장 확실한 것을 1번에 두세요.

각 분류마다 "왜 이 코드인가"를 한 줄 적어 두면 그대로 DB의 `mapping_reason`에 저장되고,
**AI가 나중에 덮어쓰지 않습니다.** (그 보호 장치를 확인해 뒀습니다)

### repository 단위

| 항목 | 규칙 |
|---|---|
| **GitHub URL** | **필수.** 이 값으로 upsert |
| **repository 이름** | **필수** (`annotated-transformer`) |
| 소유자·라이선스·언어·star 수 | 선택. 라이선스는 제출물 검증에 쓰이니 채워두면 좋습니다 |
| 관계 유형 | `OFFICIAL` / `AUTHOR` / `COMMUNITY` / `REFERENCE` |

---

## 3. 노트 → JSON

정리한 내용을 JSON 한 파일로 만듭니다. 전체 예시는
[`database/ingest_example.json`](../database/ingest_example.json) — **복사해서 값만 바꾸세요.**

```jsonc
{
  "papers": [{
    "arxivId": "1706.03762",
    "title": "Attention Is All You Need",
    "abstract": "...",
    "pdfUrl": "https://arxiv.org/pdf/1706.03762",
    "publishedDate": "2017-06-12",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],

    "chunks": [{
      "chunkIndex": 0,
      "sectionTitle": "Multi-Head Attention",
      "content": "Multi-head attention allows the model to jointly attend ...",
      "pageStart": 4, "pageEnd": 5,

      // ★ 노트에서 이 단락에 분류해둔 코드 — 맨 앞이 Top-1 정답
      "mappedCode": [
        { "githubUrl": "https://github.com/harvardnlp/annotated-transformer",
          "filePath": "model/attention.py", "symbolName": "forward", "startLine": 42,
          "reason": "h개 헤드로 선형 프로젝션 → 병렬 attention → concat 순서가 논문과 1:1 대응" },
        { "githubUrl": "https://github.com/harvardnlp/annotated-transformer",
          "filePath": "model/attention.py", "symbolName": "attention", "startLine": 12,
          "reason": "multi-head가 내부적으로 호출하는 단일 attention 함수" }
      ]
    }],

    "repositories": [{
      "githubUrl": "https://github.com/harvardnlp/annotated-transformer",
      "repositoryName": "annotated-transformer",
      "ownerName": "harvardnlp", "licenseName": "MIT",
      "primaryLanguage": "Python", "starCount": 6200,
      "relationType": "COMMUNITY", "isPrimary": true,

      "codeBlocks": [{
        "filePath": "model/attention.py",
        "symbolName": "forward",
        "symbolType": "METHOD",
        "parentSymbolName": "MultiHeadedAttention",
        "startLine": 42, "endLine": 89,
        "codeContent": "def forward(self, query, key, value, mask=None):\n    ..."
      }]
    }]
  }]
}
```

`mappedCode`는 **같은 파일 안 `codeBlocks`에 정의된 코드만** 가리킬 수 있습니다.
`githubUrl` / `filePath` / `symbolName` / `startLine` 네 개가 정확히 일치해야 하고,
오타가 있으면 적재 전에 잡아서 알려줍니다.

> `_` 로 시작하는 키는 무시되므로 `"_comment": "..."` 처럼 메모를 남겨도 됩니다.

---

## 4. 적재

```bash
# (선택) 데모 데이터를 지우고 빈 DB로 시작
./scripts/reset_db.sh

# 1) 형식만 검증 — DB는 건드리지 않음
python3 scripts/ingest.py my_papers.json --dry-run

# 2) 적재 + 수동 매핑 저장 + 정답셋 CSV 생성
python3 scripts/ingest.py my_papers.json \
    --insert-mappings \
    --eval-csv database/eval_set.csv
```

```
✅ 검증 통과 — 논문 1 / chunk 2 / repo 1 / code_block 2 / 수동매핑 3
✅ 적재 완료
✅ 수동 매핑 3건 저장 (mapping_method=MANUAL, is_verified=TRUE)
✅ 정답셋 2쌍 → database/eval_set.csv
  DB 총계: papers 1 / chunks 2 / repos 1 / code_blocks 2
  embedding 미완료: chunk 2 / code_block 2
```

| 옵션 | 하는 일 |
|---|---|
| (없음) | papers / chunks / repositories / code_blocks 적재 |
| `--insert-mappings` | `mappedCode`를 `paper_code_mappings`에 `MANUAL` / `is_verified=TRUE`로 저장 |
| `--eval-csv PATH` | 각 단락의 **첫 번째** `mappedCode`로 정답셋 CSV 생성 |
| `--dry-run` | 검증만 |
| `--print-sql` | 생성될 SQL 확인 |

### ingest.py가 대신 처리해 주는 것

| 항목 | 처리 |
|---|---|
| FK 순서 | papers → chunks → repositories → paper_repositories → code_blocks |
| `authors` | `["이름"]` → `[{"name": "이름"}]::jsonb` 변환 |
| 재적재 | arxivId / githubUrl / (논문,단락번호) / (repo,파일,심볼,줄) 기준 **upsert** — 여러 번 돌려도 중복 없음 |
| 본문 변경 감지 | 본문이 바뀌면 기존 embedding을 **자동 NULL 처리** (낡은 벡터가 남지 않음) |
| 이스케이프 | 코드 본문의 따옴표·백슬래시·`$`·유니코드 안전 처리 |
| 트랜잭션 | 전체가 한 트랜잭션 — 중간에 실패하면 아무것도 안 들어감 |

### 검증 실패 메시지 읽는 법

DB에 넣기 전에 위반을 **전부 모아서** 알려줍니다. 하나씩 고칠 필요가 없습니다.

```
❌ 검증 실패 — 6건

  · papers[0].chunks[1]: chunkIndex 중복 — 0 (uq_paper_chunks_order 위반)
  · papers[0].chunks[2]: chunkIndex 가 필요합니다.
  · papers[0].repositories[0]: starCount 는 0 이상이어야 합니다 (ck_repositories_star_count).
  · papers[0].repositories[0]: relationType 은 [...] 중 하나 — 받은 값 'WRONG'
  · papers[0].repositories[0].codeBlocks[0]: symbolType 은 [...] 중 하나 — 받은 값 'CLASSS'
  · papers[0].repositories[0].codeBlocks[0]: endLine(2) < startLine(10) — ck_code_blocks_lines 위반
```

`papers[0].chunks[1]` 는 JSON에서의 위치입니다. 그 자리를 고치면 됩니다.

---

## 5. 임베딩 — **직접 만들지 마세요**

가장 깨지기 쉬운 부분입니다. 벡터가 같은 공간에 있으려면 **셋이 전부 일치**해야 합니다.

1. 모델 (`nomic-embed-text`)
2. 차원 (768)
3. **이어붙이는 텍스트 구성** ← 제일 자주 어긋납니다

하나라도 다르면 **에러가 안 나고 검색 결과만 조용히 이상해집니다.** 디버깅이 매우 어렵습니다.

그래서 `embedding` 컬럼은 비워 둔 채 적재하고(ingest.py가 알아서 비웁니다),
백엔드를 한 번 backfill 모드로 띄우면 됩니다.

```bash
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
```

`EmbeddingBackfillRunner`가 `embedding IS NULL`인 행을 찾아 **B의 검색 코드와 정확히 같은 방식**으로
채웁니다. 위 3가지 불일치가 원천적으로 발생하지 않습니다.

로그에 아래가 뜨면 완료입니다.

```
paper_chunks embedding backfill 완료
code_blocks embedding backfill 완료
```

<details>
<summary>나중에 파이프라인에서 직접 만들게 되면 (조합을 반드시 맞출 것)</summary>

```python
import requests

def embed(text: str) -> list[float]:
    r = requests.post("http://localhost:11434/api/embed",
                      json={"model": "nomic-embed-text", "input": text})
    return r.json()["embeddings"][0]      # len == 768

def join(*parts):
    """None/빈 문자열은 건너뛰고 개행으로 연결 — 백엔드와 동일 규칙"""
    return "\n".join(p for p in parts if p)

chunk_vec = embed(join(section_title, subsection_title, content))
code_vec  = embed(join(file_path, parent_symbol_name, symbol_name, code_content))
#                      ↑ file_path가 맨 앞이라는 점 주의

cur.execute("UPDATE paper_chunks SET embedding = %s::vector WHERE id = %s",
            (str(chunk_vec), chunk_id))
```
</details>

---

## 6. AI 큐레이션 실행

임베딩이 채워지면 AI가 단락마다 코드를 찾아 근거를 만들어 저장합니다.
단락 1건당 Qwen3를 한 번 호출하므로 **단락이 많으면 오래 걸립니다** (6건 ≈ 2분).

```bash
curl -X POST localhost:8080/api/admin/curate-pending
# → {"chunksPending":6,"chunksCurated":6,"chunksSkipped":0,"mappingsCreated":30}
```

`chunksSkipped`가 크면 **code_blocks 임베딩이 안 채워진 것**입니다 (후보가 0건이라 건너뜀).

### 수동 매핑과 AI 매핑의 관계

| | mapping_method | is_verified | mapping_reason |
|---|---|---|---|
| A가 분류한 것 | `MANUAL` | `TRUE` | **A가 쓴 근거 — AI가 덮어쓰지 않음** |
| AI가 찾은 것 | `AI` | `FALSE` | TACC 요약 |

같은 (단락, 코드) 쌍이 양쪽에 다 있으면 `MANUAL` 행이 유지되고, AI가 만든 설명만 추가로 붙습니다.
**A가 적어둔 근거는 보존됩니다.**

---

## 7. 검증 3단계

### 1단계 — 백엔드 없이 SQL만

가장 빠른 피드백 루프입니다. 백엔드를 띄우지 않아도 됩니다.

```bash
docker exec -it codeatlas-postgres psql -U codeatlas -d codeatlas
```

```sql
-- 임베딩이 다 찼는지 (NULL이 남으면 검색 대상에서 빠집니다)
SELECT count(*) FILTER (WHERE embedding IS NULL) AS 미완료, count(*) AS 전체 FROM code_blocks;

-- 차원이 768인지 (모델을 잘못 썼으면 여기서 걸립니다)
SELECT DISTINCT vector_dims(embedding) FROM paper_chunks WHERE embedding IS NOT NULL;

-- 실제 검색 — 백엔드 CodeSearchService와 동일한 SQL
SELECT cb.id, r.repository_name, cb.file_path, cb.parent_symbol_name, cb.symbol_name,
       round((1 - (cb.embedding <=> pc.embedding))::numeric, 3) AS similarity
FROM code_blocks cb
JOIN repositories r ON r.id = cb.repository_id
CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = 1) pc
WHERE cb.embedding IS NOT NULL AND pc.embedding IS NOT NULL
ORDER BY cb.embedding <=> pc.embedding
LIMIT 5;
```

1위가 노트에 적어둔 코드와 같으면 성공입니다.

### 2단계 — 백엔드 API

```bash
cd backend && ./mvnw spring-boot:run

curl -s localhost:8080/api/papers | python3 -m json.tool
curl -s localhost:8080/api/papers/1/chunks | python3 -m json.tool

curl -s -X POST localhost:8080/api/mapping/search \
  -H 'Content-Type: application/json' \
  -d '{"paperId":1,"chunkId":1,"topK":5}' | python3 -m json.tool

./scripts/smoke.sh    # 전체 API 한 번에
```

### 3단계 — 정답셋으로 채점 (로드맵 2주차 산출물)

`--eval-csv`로 만든 정답셋을 그대로 씁니다.

```bash
python3 scripts/eval_retrieval.py database/eval_set.csv
```

```
정답셋 30쌍 (top-10까지 확인)
  Top-1 Accuracy : 25/30  (83.3%)
  Top-3 Accuracy : 28/30  (93.3%)
  MRR            : 0.8750

Top-1 실패 5건 (chunk_id: 정답 block → 실제 1위):
  201: 506 → 505
  ...
```

이 수치가 **결과보고서에 들어갈 정량 지표**이고,
실패 목록이 그대로 "검색 실패 케이스 보정"(로드맵 3주차) 작업 목록이 됩니다.

---

## 8. 검색이 잘 안 나올 때

### 임베딩 조합 바꿔보기

```bash
docker exec codeatlas-postgres psql -U codeatlas -d codeatlas \
  -c "UPDATE code_blocks SET embedding = NULL;"
# backend/.../embedding/EmbeddingBackfillRunner.java 의 join(...) 구성을 수정한 뒤
cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
python3 ../scripts/eval_retrieval.py ../database/eval_set.csv
```

현재 조합은 demo 6쌍으로만 고른 **잠정값**입니다. 30쌍으로 재검증해 확정해 주세요.

| 조합 | Top-1 (6쌍 기준) |
|---|---|
| `parent + symbol + symbol_type + code` | 3/6 |
| `parent + symbol + code` | 4/6 |
| `file_path + parent + symbol + code` (현재) | **5/6** |

### 그 밖의 개선 방향 (로드맵 2주차)

- 단락을 더 잘게 쪼개기 — 한 단락에 여러 주제가 섞이면 벡터가 흐려집니다
- 코드 블록 단위 조정 — 파일 통째보다 함수 단위가 유리합니다
- keyword overlap 점수 결합 (아직 미적용, 순수 코사인 유사도만 사용 중)

---

## 9. `seed_dump.sql` 만들기 (기획서 §2 / 운영규정 제10조①)

심사위원이 clone 후 파이프라인 재실행 없이 같은 DB 상태를 재현할 수 있어야 합니다.
데이터가 확정되면 덤프를 떠서 커밋하세요.

```bash
docker exec codeatlas-postgres pg_dump -U codeatlas -d codeatlas \
  --data-only --disable-triggers > database/seed_dump.sql
```

- `--data-only`: 스키마는 Script-2/Script-3가 담당하므로 데이터만
- `--disable-triggers`: FK 순서 문제 없이 복원
- `--column-inserts`는 쓰지 마세요 — embedding이 768차원 × 행수라 파일이 폭발합니다

복원 확인:

```bash
./scripts/reset_db.sh
docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas < database/seed_dump.sql
./scripts/doctor.sh
```

> 완성되면 `docker-compose.yml`의 `seed_demo.sql` 마운트를 `seed_dump.sql`로 바꾸고
> `database/seed_demo.sql`은 삭제하세요 (B가 만든 임시 데이터입니다).

`seed_manifest.csv`는 "논문 10건을 어디서 어떻게 골랐는지"의 출처 기록이라 별도로 작성해야 합니다.

---

## 10. 스크립트 요약

| 스크립트 | 용도 |
|---|---|
| `./scripts/doctor.sh` | 환경 점검 — 막히면 제일 먼저 |
| `./scripts/reset_db.sh` | 스키마 초기화 (빈 DB). `--with-demo`로 데모 데이터 포함 |
| `python3 scripts/ingest.py <json>` | 논문·코드·수동매핑 적재, 정답셋 CSV 생성 |
| `python3 scripts/eval_retrieval.py <csv>` | Top-1/3 Accuracy, MRR |
| `./scripts/smoke.sh` | 기동된 백엔드 전체 API 확인 |

---

## 11. 자주 걸리는 함정

| 증상 | 원인 |
|---|---|
| `role "codeatlas" does not exist` | 로컬 PostgreSQL 5432에 붙은 것. 포트 **5433** 확인 |
| 검색 결과가 항상 비어 있음 | `embedding IS NULL`. backfill을 돌렸는지 확인 |
| 검색 결과는 나오는데 순위가 엉망 | 임베딩 모델/조합 불일치. `vector_dims` 확인 |
| `curate-pending`의 `chunksSkipped`가 큼 | code_blocks 임베딩 미완료 |
| `mappedCode`가 "codeBlocks에 없는 코드" 라고 나옴 | githubUrl/filePath/symbolName/startLine 네 개가 정확히 일치해야 함 (줄 번호 오타가 많습니다) |
| SQL 스크립트를 고쳤는데 반영 안 됨 | docker 초기화 스크립트는 **볼륨이 빈 최초 1회만** 실행. `./scripts/reset_db.sh` 사용 |
| `503 MODEL_UNAVAILABLE` | `ollama serve` 미기동 |

---

## 12. 체크리스트

**데이터**
- [ ] 노트 정리를 §2 규칙에 맞춰 정돈 (단락번호 0부터, symbolType 5종, 줄 번호)
- [ ] 논문 10건 JSON 작성 → `ingest.py --dry-run` 통과
- [ ] `--insert-mappings --eval-csv` 로 적재 + 정답셋 생성
- [ ] backfill 실행 → `doctor.sh`에서 "임베딩 전량 완료" 확인
- [ ] `curate-pending` 실행

**검증**
- [ ] 정답셋 30쌍 확보
- [ ] Top-1/3 Accuracy, MRR 측정 → 결과보고서용 수치
- [ ] 임베딩 조합 최종 확정
- [ ] keyword overlap 점수 결합 (로드맵 2주차)

**제출물**
- [ ] `database/seed_dump.sql` + `seed_manifest.csv` 생성·커밋
- [ ] `feature/retrieval-pipeline`, `feature/vector-search-api` 브랜치 리뷰

---

## 참고 문서

- [api-spec.md](api-spec.md) — A↔B API 계약
- [backend/README.md](../backend/README.md) — 백엔드 실행·구조
- [backend-setup.md](backend-setup.md) — 백엔드가 어떻게 만들어졌는지
- `database/Script-2.sql` — 전체 스키마 (변경 시 A 승인 필요)
