# 팀원 A용 — 논문·코드 DB 구축 및 테스트 가이드

> 대상: 팀원 A (Knowledge Retrieval Engineer)
> 목적: `data-pipeline/`이 만든 데이터를 DB에 넣고, 검색이 제대로 되는지 확인하는 방법
> 관련: [api-spec.md](api-spec.md) · [backend/README.md](../backend/README.md) · `database/Script-2.sql`

---

## 0. 5분 셋업

```bash
git clone https://github.com/Ae-Ti/CodeAtlas.git
cd CodeAtlas
git checkout develop

# 1) DB
docker compose up -d

# 2) 모델 (https://ollama.com 설치 후)
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve

# 3) 환경 점검 — 뭐가 빠졌는지 알려줍니다
./scripts/doctor.sh
```

`doctor.sh`가 docker / java 21 / python3 / DB / pgvector / 임베딩 차원 / Ollama 모델 /
데이터 적재 상태 / 백엔드까지 확인하고, **빠진 항목마다 실행할 명령을 같이 출력**합니다.
막히면 먼저 이걸 돌리세요.

```
[2/5] 데이터베이스
  ✅ 컨테이너 'codeatlas-postgres' 실행 중
  ✅ 노출 포트 5433 (접속 URL: jdbc:postgresql://localhost:5433/codeatlas)
  ✅ pgvector 0.8.6
[4/5] 데이터 적재 상태
  papers 0 / chunks 0 / code_blocks 0 / mappings 0
  ⚠️  적재된 논문 없음
     → python3 scripts/ingest.py <파일>.json  또는  ./scripts/reset_db.sh --with-demo
```

> **포트는 5432가 아니라 5433입니다.** 로컬에 이미 PostgreSQL이 5432를 쓰고 있으면
> 그쪽으로 붙어버려 `role "codeatlas" does not exist` 에러가 납니다.

---

## 1. 핵심 원칙 — **임베딩은 직접 만들지 말고 백엔드에 맡기세요**

가장 깨지기 쉬운 부분이 임베딩입니다. 벡터가 같은 공간에 있으려면 **세 가지가 전부 일치**해야 합니다.

1. 모델 (`nomic-embed-text`)
2. 차원 (768)
3. **이어붙이는 텍스트 구성** ← 이게 제일 자주 어긋납니다

세 개 중 하나라도 다르면 `<=>` 유사도 계산이 통째로 무의미해지는데,
**에러가 안 나고 그냥 결과만 이상해집니다.** 디버깅이 매우 어렵습니다.

그래서 권장 방식은:

> **A는 `embedding` 컬럼을 비운 채로(NULL) 데이터만 넣고, 백엔드를 backfill 모드로 한 번 띄운다.**

```bash
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
```

`EmbeddingBackfillRunner`가 `embedding IS NULL`인 행을 전부 찾아, B의 검색 코드와
**정확히 같은 방식**으로 채웁니다. 위 3가지 불일치가 원천적으로 발생하지 않습니다.

<details>
<summary>그래도 Python 파이프라인에서 직접 만들고 싶다면 (조합을 반드시 맞출 것)</summary>

```python
import requests

def embed(text: str) -> list[float]:
    r = requests.post("http://localhost:11434/api/embed",
                      json={"model": "nomic-embed-text", "input": text})
    return r.json()["embeddings"][0]      # len == 768

def join(*parts):
    """None/빈 문자열은 건너뛰고 개행으로 연결 — 백엔드와 동일 규칙"""
    return "\n".join(p for p in parts if p)

# 논문 chunk
chunk_vec = embed(join(section_title, subsection_title, content))

# 코드 block  ← file_path가 앞에 온다는 점 주의
code_vec = embed(join(file_path, parent_symbol_name, symbol_name, code_content))

# pgvector에는 '[0.1,-0.2,...]' 문자열로 넣고 ::vector 캐스팅
cur.execute("UPDATE paper_chunks SET embedding = %s::vector WHERE id = %s",
            (str(chunk_vec), chunk_id))
```
</details>

---

## 2. 데이터 적재 — `scripts/ingest.py`

FK 순서·JSONB·CHECK 제약·UNIQUE 키를 직접 신경 쓸 필요 없습니다.
**파이프라인은 JSON 하나만 만들면 됩니다.**

```bash
# 빈 DB로 시작 (demo 데이터 제거)
./scripts/reset_db.sh

# 형식 확인
python3 scripts/ingest.py database/ingest_example.json --dry-run

# 실제 적재
python3 scripts/ingest.py my_papers.json
```

```
✅ 검증 통과 — 논문 1 / chunk 2 / repo 1 / code_block 2
✅ 적재 완료
  DB 총계: papers 1 / chunks 2 / repos 1 / code_blocks 2
  embedding 미완료: chunk 2 / code_block 2

다음 단계: 임베딩 채우기
  cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
```

### JSON 형식

전체 예시는 [`database/ingest_example.json`](../database/ingest_example.json) — 그대로 복사해서 쓰세요.

```jsonc
{
  "papers": [{
    "arxivId": "1706.03762",        // 필수 — 재적재 시 upsert 키
    "title": "...",                  // 필수
    "abstract": "...", "pdfUrl": "...", "publishedDate": "2017-06-12",
    "authors": ["Ashish Vaswani", "..."],     // 문자열 배열 → JSONB로 변환해줌

    "chunks": [{
      "chunkIndex": 0,               // 필수, 논문 안에서 0부터
      "content": "...",              // 필수
      "sectionTitle": "...", "subsectionTitle": null,
      "pageStart": 4, "pageEnd": 5, "tokenCount": 96
    }],

    "repositories": [{
      "githubUrl": "https://github.com/...",   // 필수 — upsert 키
      "repositoryName": "...",                 // 필수
      "ownerName": "...", "licenseName": "MIT", "primaryLanguage": "Python",
      "starCount": 6200, "relationType": "COMMUNITY", "isPrimary": true,

      "codeBlocks": [{
        "filePath": "model/attention.py",      // 필수
        "symbolType": "METHOD",                // 필수 — FILE/CLASS/FUNCTION/METHOD/MODULE
        "codeContent": "...",                  // 필수
        "symbolName": "forward", "parentSymbolName": "MultiHeadedAttention",
        "startLine": 42, "endLine": 89
      }]
    }]
  }]
}
```

### ingest.py가 대신 처리해 주는 것

| 항목 | 처리 |
|---|---|
| FK 순서 | papers → chunks → repositories → paper_repositories → code_blocks 순으로 생성 |
| `authors` | `["이름"]` → `[{"name": "이름"}]::jsonb` 변환 |
| 재적재 | `arxivId` / `githubUrl` / `(paper_id, chunk_index)` / `(repo, file, symbol, line)` 기준 **upsert** — 여러 번 돌려도 중복이 안 생깁니다 |
| 본문 변경 감지 | `content`/`code_content`가 바뀌면 기존 embedding을 **자동으로 NULL 처리** (낡은 벡터가 남지 않음) |
| 이스케이프 | 코드 본문의 따옴표·백슬래시·`$`·유니코드를 dollar-quoting으로 안전 처리 |
| 트랜잭션 | 전체가 한 트랜잭션 — 중간에 실패하면 아무것도 안 들어갑니다 |

### 사전 검증

DB에 넣기 전에 제약 위반을 **전부 모아서** 알려줍니다. psql 에러 하나씩 고칠 필요가 없습니다.

```
❌ 검증 실패 — 6건

  · papers[0].chunks[1]: chunkIndex 중복 — 0 (uq_paper_chunks_order 위반)
  · papers[0].chunks[2]: chunkIndex 가 필요합니다.
  · papers[0].repositories[0]: starCount 는 0 이상이어야 합니다 (ck_repositories_star_count).
  · papers[0].repositories[0]: relationType 은 [...] 중 하나 — 받은 값 'WRONG'
  · papers[0].repositories[0].codeBlocks[0]: symbolType 은 [...] 중 하나 — 받은 값 'CLASSS'
  · papers[0].repositories[0].codeBlocks[0]: endLine(2) < startLine(10) — ck_code_blocks_lines 위반
```

---

## 3. 테스트 1단계 — 백엔드 없이 SQL만으로 확인

**백엔드를 띄우지 않고도 검색 품질을 확인할 수 있습니다.** 가장 빠른 피드백 루프입니다.

```sql
-- 임베딩이 다 찼는지 (NULL이 남아 있으면 검색 대상에서 빠집니다)
SELECT count(*) FILTER (WHERE embedding IS NULL) AS 미완료, count(*) AS 전체 FROM code_blocks;

-- 차원이 768인지 (모델을 잘못 쓰면 여기서 걸립니다)
SELECT DISTINCT vector_dims(embedding) FROM paper_chunks WHERE embedding IS NOT NULL;

-- 실제 검색 — CodeSearchService와 동일한 SQL
SELECT cb.id, r.repository_name, cb.file_path, cb.parent_symbol_name, cb.symbol_name,
       round((1 - (cb.embedding <=> pc.embedding))::numeric, 3) AS similarity
FROM code_blocks cb
JOIN repositories r ON r.id = cb.repository_id
CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = 1) pc
WHERE cb.embedding IS NOT NULL AND pc.embedding IS NOT NULL
ORDER BY cb.embedding <=> pc.embedding
LIMIT 5;
```

결과 1위가 사람이 보기에 맞는 코드면 성공입니다.

---

## 4. 테스트 2단계 — 백엔드 API

```bash
cd backend && ./mvnw spring-boot:run

curl -s localhost:8080/api/papers | python3 -m json.tool
curl -s localhost:8080/api/papers/1/chunks | python3 -m json.tool

# chunk → 코드 검색 (A 담당 API)
curl -s -X POST localhost:8080/api/mapping/search \
  -H 'Content-Type: application/json' \
  -d '{"paperId":1,"chunkId":1,"topK":5}' | python3 -m json.tool
```

여기까지 되면 **큐레이션 배치**를 돌립니다. chunk 1건당 Qwen3를 한 번 호출하므로
chunk가 많으면 오래 걸립니다 (chunk 6건 ≈ 2분). 진행 상황은 서버 로그에 찍힙니다.

```bash
curl -X POST localhost:8080/api/admin/curate-pending
# → {"chunksPending":6,"chunksCurated":6,"chunksSkipped":0,"mappingsCreated":30}
```

`chunksSkipped`가 크면 **code_blocks 임베딩이 안 채워진 것**입니다 (후보가 0건이라 건너뜀).

전체 API를 한 번에 훑으려면 `./scripts/smoke.sh`.

---

## 5. 테스트 3단계 — 품질 지표 (로드맵 2주차 산출물)

```bash
# 정답셋: chunk_id, code_block_id (사람이 검수한 정답 1개)
python3 scripts/eval_retrieval.py database/eval_set_demo.csv
```

```
정답셋 6쌍 (top-10까지 확인)
  Top-1 Accuracy : 5/6  (83.3%)
  Top-3 Accuracy : 5/6  (83.3%)
  MRR            : 0.8750

Top-1 실패 1건 (chunk_id: 정답 block → 실제 1위):
  201: 506 → 505
```

백엔드가 안 떠 있어도 되고 추가 패키지도 필요 없습니다.
실패 목록이 그대로 "검색 실패 케이스 보정"(로드맵 3주차) 작업 목록이 됩니다.

### 임베딩 조합을 바꿔 실험하려면

```bash
docker exec codeatlas-postgres psql -U codeatlas -d codeatlas \
  -c "UPDATE code_blocks SET embedding = NULL;"
# EmbeddingBackfillRunner의 join(...) 구성을 수정한 뒤
cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
python3 ../scripts/eval_retrieval.py ../database/eval_set_demo.csv
```

현재 조합(`file_path + parent_symbol_name + symbol_name + code_content`)은
demo 6쌍으로만 고른 **잠정값**입니다. 30쌍으로 재검증해서 확정해 주세요.

| 조합 | Top-1 (6쌍 기준) |
|---|---|
| `parent + symbol + symbol_type + code` | 3/6 |
| `parent + symbol + code` | 4/6 |
| `file_path + parent + symbol + code` (현재) | 5/6 |

---

## 6. `seed_dump.sql` 만들기 (기획서 §2 / 운영규정 제10조①)

심사위원이 clone 후 파이프라인을 재실행하지 않고도 같은 DB 상태를 재현할 수 있어야 합니다.

```bash
docker exec codeatlas-postgres pg_dump -U codeatlas -d codeatlas \
  --data-only --disable-triggers > database/seed_dump.sql
```

- `--data-only`: 스키마는 Script-2/Script-3가 담당하므로 데이터만
- `--disable-triggers`: FK 순서 문제 없이 복원
- `--column-inserts`는 쓰지 마세요 — embedding이 768차원 × 행수라 파일이 폭발합니다

복원 확인 (클론 시뮬레이션):

```bash
./scripts/reset_db.sh          # 빈 스키마
docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas < database/seed_dump.sql
./scripts/doctor.sh            # 상태 확인
```

> `seed_dump.sql`이 완성되면 `docker-compose.yml`의 `seed_demo.sql` 마운트를 그쪽으로 교체하고
> `database/seed_demo.sql`은 삭제하세요. (B가 만든 임시 데이터입니다)

`seed_manifest.csv`는 "논문 10건을 어디서 어떻게 골랐는지"의 출처 기록이므로 별도로 작성해야 합니다.

---

## 7. 스크립트 요약

| 스크립트 | 용도 |
|---|---|
| `./scripts/doctor.sh` | 환경 점검 — 막히면 제일 먼저 |
| `./scripts/reset_db.sh` | 스키마 초기화 (빈 DB). `--with-demo`로 demo 데이터 포함 |
| `python3 scripts/ingest.py <json>` | 논문·코드 적재. `--dry-run`으로 검증만, `--print-sql`로 SQL 확인 |
| `python3 scripts/eval_retrieval.py <csv>` | Top-1/3 Accuracy, MRR |
| `./scripts/smoke.sh` | 기동된 백엔드 전체 API 확인 |

---

## 8. 자주 걸리는 함정

| 증상 | 원인 |
|---|---|
| `role "codeatlas" does not exist` | 로컬 PostgreSQL 5432에 붙은 것. 포트 **5433** 확인 |
| 검색 결과가 항상 비어 있음 | `embedding IS NULL`. backfill을 돌렸는지 확인 |
| 검색 결과는 나오는데 순위가 엉망 | 임베딩 모델/조합 불일치. `vector_dims`와 join 구성 확인 |
| `curate-pending`의 `chunksSkipped`가 큼 | code_blocks 임베딩 미완료 |
| Script를 고쳤는데 반영이 안 됨 | docker 초기화 스크립트는 **볼륨이 빈 최초 1회만** 실행. `./scripts/reset_db.sh` 사용 |
| `503 MODEL_UNAVAILABLE` | `ollama serve` 미기동 |
| ingest.py가 검증 실패 | 메시지에 위반한 제약조건 이름이 같이 나옵니다. 파이프라인 출력을 고치세요 |

---

## 9. A 담당 산출물 체크리스트

- [ ] 파이프라인이 `ingest.py` JSON 형식으로 출력하도록 구현
- [ ] 논문 10건 적재 (`papers` / `paper_chunks` / `repositories` / `paper_repositories` / `code_blocks`)
- [ ] 임베딩 전량 채움 (`doctor.sh`에서 "임베딩 전량 완료" 확인)
- [ ] 정답셋 30쌍 CSV 작성
- [ ] Top-1/3 Accuracy, MRR 측정 → 결과보고서용 수치 확보
- [ ] 임베딩 조합 최종 확정 (필요 시 `EmbeddingBackfillRunner` 수정)
- [ ] keyword overlap 점수 결합 (로드맵 2주차)
- [ ] `database/seed_dump.sql` + `seed_manifest.csv` 생성·커밋
- [ ] `feature/retrieval-pipeline`, `feature/vector-search-api` 브랜치 리뷰
