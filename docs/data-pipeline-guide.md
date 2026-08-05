# 팀원 A용 — 논문·코드 DB 구축 및 테스트 가이드

> 대상: 팀원 A (Knowledge Retrieval Engineer)
> 목적: `data-pipeline/`이 만든 데이터를 DB에 넣고, 검색이 제대로 되는지 확인하는 방법
> 관련: [api-spec.md](api-spec.md) · [backend/README.md](../backend/README.md) · `database/Script-2.sql`

---

## 0. 핵심 원칙 하나 — **임베딩은 직접 만들지 말고 백엔드에 맡기세요**

가장 깨지기 쉬운 부분이 임베딩입니다. 벡터가 같은 공간에 있으려면 **세 가지가 전부 일치**해야 합니다.

1. 모델 (`nomic-embed-text`)
2. 차원 (768)
3. **이어붙이는 텍스트 구성** ← 이게 제일 자주 어긋납니다

세 개 중 하나라도 다르면 `<=>` 유사도 계산이 통째로 무의미해지는데, **에러가 안 나고 그냥 결과만 이상해집니다.** 디버깅이 매우 어렵습니다.

그래서 권장 방식은:

> **A는 `embedding` 컬럼을 비운 채로(NULL) 데이터만 넣고, 백엔드를 backfill 모드로 한 번 띄운다.**

```bash
cd backend
CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
```

`EmbeddingBackfillRunner`가 `embedding IS NULL`인 행을 전부 찾아, B의 검색 코드와 **정확히 같은 방식**으로 채웁니다. 이러면 위 3가지 불일치가 원천적으로 발생하지 않습니다.

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

조합이 바뀌면 검색 품질이 달라집니다 (demo 6쌍 기준 Top-1이 3/6 ↔ 5/6까지 벌어졌습니다).
바꾸려면 `EmbeddingBackfillRunner`도 같이 고치고 이 문서에 기록하세요.
</details>

---

## 1. 채워야 할 테이블과 순서

FK 때문에 **반드시 이 순서**로 넣어야 합니다.

```
papers  →  paper_chunks
        ↘
repositories  →  paper_repositories
              ↘
                code_blocks
```

`paper_code_mappings`는 A가 채우지 않습니다. 백엔드 큐레이션 배치가 만듭니다 (아래 3단계).

### DB 접속

```
host localhost   port 5433   db codeatlas   user codeatlas   password codeatlas
```

> **5432가 아니라 5433입니다.** 로컬에 이미 PostgreSQL이 5432를 쓰고 있으면 그쪽으로 붙어버려
> `role "codeatlas" does not exist` 에러가 납니다.

```bash
# psql 바로 붙기
docker exec -it codeatlas-postgres psql -U codeatlas -d codeatlas
```

### 컬럼별 주의사항 (`Script-2.sql`의 제약조건)

| 테이블 | 주의할 점 |
|---|---|
| `papers` | `authors`는 **JSONB 배열** — `'[{"name": "Ashish Vaswani"}]'::jsonb` 형식. TEXT 아님 |
| | `arxiv_id`, `doi`는 UNIQUE — 중복 적재 시 실패 |
| | `processing_status` ∈ `PENDING/PROCESSING/COMPLETED/FAILED` |
| `paper_chunks` | `(paper_id, chunk_index)`가 UNIQUE — chunk_index는 논문 안에서 0부터 순서대로 |
| | 본문 컬럼명은 `content` (chunk_text 아님) |
| `repositories` | `github_url` UNIQUE. 이름 컬럼은 `repository_name` (repo_name 아님) |
| `code_blocks` | `symbol_type` ∈ `FILE/CLASS/FUNCTION/METHOD/MODULE` — 그 외 값은 INSERT 거부 |
| | `(repository_id, file_path, symbol_name, start_line)`가 UNIQUE |
| | 코드 본문은 `code_content`, 함수/클래스명은 `symbol_name`, 상위 클래스는 `parent_symbol_name` |
| | `end_line >= start_line` 이어야 함 |

형식 예시는 `database/seed_demo.sql`을 그대로 참고하세요.

---

## 2. 테스트 1단계 — 백엔드 없이 SQL만으로 확인

**백엔드를 띄우지 않고도 검색 품질을 확인할 수 있습니다.** 가장 빠른 피드백 루프입니다.

```sql
-- (1) 적재량 확인
SELECT
  (SELECT count(*) FROM papers)              AS papers,
  (SELECT count(*) FROM paper_chunks)        AS chunks,
  (SELECT count(*) FROM repositories)        AS repos,
  (SELECT count(*) FROM code_blocks)         AS blocks;

-- (2) 임베딩이 다 찼는지 (여기서 NULL이 남아 있으면 검색 대상에서 빠집니다)
SELECT count(*) FILTER (WHERE embedding IS NULL) AS 미완료,
       count(*)                                   AS 전체
FROM code_blocks;

-- (3) 차원이 768인지 (모델을 잘못 쓰면 여기서 걸립니다)
SELECT DISTINCT vector_dims(embedding) FROM paper_chunks WHERE embedding IS NOT NULL;

-- (4) 실제 검색 — CodeSearchService와 동일한 SQL
SELECT cb.id, r.repository_name, cb.file_path, cb.parent_symbol_name, cb.symbol_name,
       round((1 - (cb.embedding <=> pc.embedding))::numeric, 3) AS similarity
FROM code_blocks cb
JOIN repositories r ON r.id = cb.repository_id
CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = 101) pc
WHERE cb.embedding IS NOT NULL AND pc.embedding IS NOT NULL
ORDER BY cb.embedding <=> pc.embedding
LIMIT 5;
```

(4)의 결과 1위가 사람이 보기에 맞는 코드면 성공입니다.

---

## 3. 테스트 2단계 — 백엔드 API로 확인

```bash
# 백엔드 기동 (임베딩이 이미 다 찼으면 backfill 플래그 없이)
cd backend && ./mvnw spring-boot:run

# 논문/chunk가 잘 나오는지
curl -s localhost:8080/api/papers | python3 -m json.tool
curl -s localhost:8080/api/papers/1/chunks | python3 -m json.tool

# chunk → 코드 검색 (A 담당 API)
curl -s -X POST localhost:8080/api/mapping/search \
  -H 'Content-Type: application/json' \
  -d '{"paperId":1,"chunkId":101,"topK":5}' | python3 -m json.tool

# 자연어로 chunk 검색
curl -s -X POST localhost:8080/api/papers/chunks/search \
  -H 'Content-Type: application/json' \
  -d '{"queryText":"residual connection","topK":3}' | python3 -m json.tool
```

여기까지 확인됐으면 **큐레이션 배치**를 돌립니다. chunk 1건당 Qwen3를 한 번 호출하므로
chunk가 많으면 오래 걸립니다 (demo 6건 = 약 2분). 진행 상황은 서버 로그에 찍힙니다.

```bash
curl -X POST localhost:8080/api/admin/curate-pending
# → {"chunksPending":6,"chunksCurated":6,"chunksSkipped":0,"mappingsCreated":30}
```

`chunksSkipped`가 크면 **code_blocks 임베딩이 안 채워진 것**입니다 (후보가 0건이라 건너뜀).

배치 후 `/api/agent/query`는 Ollama를 호출하지 않고 즉시 응답합니다.

```bash
curl -s -X POST localhost:8080/api/agent/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"attention 구현?","paperId":1,"chunkId":101}' | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d['source'], d['mappingReason'])"
# → precomputed  TACC: 후보 7개 중 중복·저점수 2개 제외 후 5개 선택
```

전체 API를 한 번에 훑으려면:

```bash
./scripts/smoke.sh
```

---

## 4. 테스트 3단계 — 품질 지표 (로드맵 2주차 산출물)

정답셋 CSV를 만들고 `scripts/eval_retrieval.py`를 돌리면 Top-1/3 Accuracy와 MRR이 나옵니다.
백엔드가 안 떠 있어도 되고 추가 패키지도 필요 없습니다.

```bash
# 정답셋: chunk_id, code_block_id (사람이 검수한 정답 1개)
# 형식 예시는 database/eval_set_demo.csv 참고 — 로드맵 기준 30쌍까지 확장
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

실패 목록이 그대로 "검색 실패 케이스 보정"(로드맵 3주차) 작업 목록이 됩니다.

### 임베딩 조합을 바꿔 실험하려면

```bash
# 1. 코드 block 임베딩만 초기화
docker exec codeatlas-postgres psql -U codeatlas -d codeatlas \
  -c "UPDATE code_blocks SET embedding = NULL;"

# 2. EmbeddingBackfillRunner의 join(...) 구성을 수정

# 3. 다시 채우고 평가
cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run
python3 ../scripts/eval_retrieval.py ../database/eval_set_demo.csv
```

지금 채택된 조합(`file_path + parent_symbol_name + symbol_name + code_content`)은
demo 6쌍으로만 고른 잠정값입니다. **30쌍으로 재검증해서 확정해 주세요.**

| 조합 | Top-1 (6쌍 기준) |
|---|---|
| `parent + symbol + symbol_type + code` | 3/6 |
| `parent + symbol + code` | 4/6 |
| `file_path + parent + symbol + code` (현재) | 5/6 |

---

## 5. `seed_dump.sql` 만들기 (기획서 §2 / 운영규정 제10조①)

심사위원이 clone 후 파이프라인을 재실행하지 않고도 같은 DB 상태를 재현할 수 있어야 합니다.
데이터가 확정되면 덤프를 떠서 커밋하세요.

```bash
docker exec codeatlas-postgres pg_dump -U codeatlas -d codeatlas \
  --data-only --disable-triggers > database/seed_dump.sql
```

- `--data-only`: 스키마는 Script-2/Script-3가 담당하므로 데이터만
- `--disable-triggers`: FK 순서 문제 없이 복원
- 기본 COPY 형식이라 `--column-inserts`보다 훨씬 작습니다 (embedding이 768차원 × 행수라 큽니다)

복원 확인 (클론 시뮬레이션):

```bash
docker compose down -v && docker compose up -d   # Script-2 → Script-3 → seed_demo
docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas < database/seed_dump.sql
```

> `seed_dump.sql`이 완성되면 `docker-compose.yml`의 `seed_demo.sql` 마운트를 그쪽으로 교체하고
> `database/seed_demo.sql`은 삭제하세요. (B가 만든 임시 데이터입니다)

`seed_manifest.csv`는 "논문 10건을 어디서 어떻게 골랐는지"의 출처 기록이므로 별도로 작성해야 합니다.

---

## 6. 자주 걸리는 함정

| 증상 | 원인 |
|---|---|
| `role "codeatlas" does not exist` | 로컬 PostgreSQL 5432에 붙은 것. 포트 **5433** 확인 |
| 검색 결과가 항상 비어 있음 | `embedding IS NULL`. backfill을 돌렸는지 확인 |
| 검색 결과가 나오는데 순위가 엉망 | 임베딩 모델/조합 불일치. `vector_dims`와 join 구성 확인 |
| `curate-pending`의 `chunksSkipped`가 큼 | code_blocks 임베딩 미완료 |
| `new row violates check constraint "ck_code_blocks_..."` | `symbol_type`이 5종 밖의 값 |
| `duplicate key value violates unique constraint` | 같은 파일·심볼·시작줄을 두 번 넣음. 재적재 전 `DELETE` 필요 |
| Script를 고쳤는데 반영이 안 됨 | 초기화 스크립트는 **볼륨이 빈 최초 1회만** 실행. `docker compose down -v` 필요 |
| `503 MODEL_UNAVAILABLE` | `ollama serve` 미기동 |

---

## 7. A 담당 산출물 체크리스트

- [ ] `papers` / `paper_chunks` / `repositories` / `paper_repositories` / `code_blocks` 적재 (논문 10건)
- [ ] 임베딩 전량 채움 (`embedding IS NULL` = 0)
- [ ] 정답셋 30쌍 CSV 작성
- [ ] Top-1/3 Accuracy, MRR 측정 → 결과보고서용 수치 확보
- [ ] 임베딩 조합 최종 확정 (필요 시 `EmbeddingBackfillRunner` 수정)
- [ ] keyword overlap 점수 결합 (로드맵 2주차)
- [ ] `database/seed_dump.sql` + `seed_manifest.csv` 생성·커밋
- [ ] `feature/retrieval-pipeline`, `feature/vector-search-api` 브랜치 리뷰 후 merge
