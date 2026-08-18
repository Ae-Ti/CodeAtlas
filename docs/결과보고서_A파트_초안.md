# 결과보고서 — A 파트 초안 (데이터 구축·검증 / 평가지표 / 라이선스)

> [#11](https://github.com/Ae-Ti/CodeAtlas/issues/11) 분담: **표·수치 = A / 해석 문단 = B**
> B 가 잡는 골격에 그대로 끼울 수 있게 절 단위로 씁니다. 해석·서사는 비워 두었습니다.
> 작성: A (UngsikJo) · 실측 기준일 2026-08-18

**이 문서의 모든 수치는 제출본 경로에서 다시 측정한 값입니다.** 재현 명령을 절마다 적었습니다.

```bash
./scripts/reset_db.sh
docker exec -i codeatlas-postgres psql -U codeatlas -d codeatlas < database/seed_dump.sql
cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run    # 약 1분
```

---

## §2. 데이터 구축과 검증

### 2.1 카탈로그 규모

| 항목 | 수 |
|---|---:|
| 논문 | **9** |
| 저장소 | **12** |
| 논문↔저장소 연결 | 12 |
| 논문 단락 (`paper_chunks`) | **376** |
| 코드 블록 (`code_blocks`) | **183** |
| 단락↔코드 매핑 (`paper_code_mappings`) | **2,011** (수동 검수 344 + AI 생성 1,667) |

논문별 내역입니다.

| arXiv | 논문 | 단락 | 코드 블록 | 저장소 |
|---|---|---:|---:|---:|
| 1706.03762 | Attention Is All You Need | 63 | 33 | 1 |
| 1810.04805 | BERT | 37 | 18 | 1 |
| 2103.00020 | CLIP | 31 | 17 | 2 |
| 2112.10752 | Latent Diffusion | 30 | 21 | 1 |
| 2407.21783 | Llama 3 | 20 | 10 | 1 |
| 1512.03385 | ResNet | 64 | 32 | 2 |
| 2304.02643 | Segment Anything | 29 | 16 | 1 |
| 2010.11929 | Vision Transformer | 33 | 18 | 2 |
| 1506.02640 | YOLO | 69 | 18 | 1 |

```bash
docker exec codeatlas-postgres psql -U codeatlas -d codeatlas -tAc \
  "SELECT count(*) FROM paper_chunks"      # 376
```

### 2.2 구축 방식 — 수동 큐레이션

논문 1편당 사람이 읽고 단락을 나눈 뒤, 각 단락에 대응하는 코드 위치를 지정했습니다.
자동 수집을 쓰지 않은 이유는 **오탐 한 건의 비용이 특히 크기** 때문입니다 — "이 단락은
이 함수입니다"라고 단정해 놓고 틀리면 사용자는 검증하려 저장소를 직접 뒤지게 되고,
그 순간 제품이 존재할 이유가 없어집니다.

파이프라인은 다음과 같습니다. 각 단계 산출물이 저장소에 남아 있어 재현할 수 있습니다.

```
큐레이터 노트(마크다운)
  └─▶ scripts/note2ingest/    노트 파싱 · 코드 위치 역매칭 · 쪽 번호 대조
        └─▶ database/ingest/*_ingest.json      ← 커밋됨
              └─▶ scripts/ingest.py            스키마 검증 후 적재
                    └─▶ PostgreSQL 17 + pgvector
```

**코드 본문은 노트가 아니라 저장소 원문에서 가져옵니다.** 초기에는 노트에 적힌 코드를
그대로 넣었는데, 검수 과정에서 14개 블록 중 13개가 저장소와 바이트 단위로 일치하지
않는다는 것을 발견했습니다(노트를 쓰며 줄여 적은 것). 지정된 커밋의 해당 줄 범위를
직접 잘라 오도록 바꿨습니다.

### 2.3 데이터 품질 실측

| 항목 | 값 | 비고 |
|---|---:|---|
| 쪽 번호가 채워진 단락 | **376/376 (100%)** | 논문 PDF 대조 |
| 논문 원문이 실린 단락 | **374/376 (99.5%)** | 나머지 2건은 큐레이터가 쓴 요약 단락이라 대응 원문이 원래 없음 |
| 코드가 매핑된 단락 | **315/376 (83.8%)** | 나머지 61건은 §2.4 |
| 줄 번호가 있는 코드 블록 | **183/183 (100%)** | NULL 이면 중복 적재가 생김 |
| 커밋 해시가 고정된 저장소 | **12/12 (100%)** | 인용 위치 재현용 |
| 임베딩이 채워진 단락 / 블록 | **376/376 · 183/183** | `nomic-embed-text` 768차원 |

### 2.4 매핑하지 않은 61건 — 억지로 채우지 않았습니다

코드를 붙이지 않은 단락 61건을 **하나씩 판정**했습니다. 판정과 근거는
`scripts/note2ingest/tally_unmapped.py` 에 단락 단위로 적혀 있어 재현·검증할 수 있습니다.

| 사유 | 건수 | 뜻 |
|---|---:|---|
| **A. 저장소가 그 구현을 배포하지 않음** | **24 (39.3%)** | 논문은 구현 요소로 서술했으나 인용 저장소에 그 코드가 없음 |
| **B. 코드로 표현되는 대상이 아님** | **32 (52.5%)** | 실험 결과·수치, Figure/Table, Reference, 타 시스템 설명, 하드웨어·일정, 결론 |
| C. 저장소엔 있으나 인덱싱 범위 밖 | 2 (3.3%) | 코드는 존재하지만 이번 큐레이션에서 블록으로 뽑지 않음 |
| D. 대응이 느슨해 정답셋에 넣지 않음 | 3 (4.9%) | 후보 심볼은 있으나 "이 단락의 구현"이라 단정하기 어려워 비워 둠 |

**A 가 39.3% 로 예상보다 큽니다.** 원인은 공개된 구현이 논문의 일부만 담기 때문입니다.

| 저장소 | 배포 범위 | 그래서 못 붙은 것 |
|---|---|---|
| `meta-llama/llama3` | 추론 코드 3파일 (`generation`·`model`·`tokenizer`) | RLHF·DPO·Reward Modeling·SFT |
| `facebookresearch/segment-anything` | 인코더·디코더·predictor | Loss Function·SA-1B Dataset·Data Engine |
| `KaimingHe/deep-residual-networks` | **ResNet-101 `deploy` prototxt 한 개** | CIFAR 구조·학습 설정·detection 확장 전부 (15건) |

**이 판단은 논문만 읽어서는 나오지 않습니다.** 논문은 학습 절차와 detection 확장에 절을
배정해 상세히 서술하지만, 저자가 공개한 것은 추론 정의뿐입니다. 저장소 인벤토리를 봐야
알 수 있는 구분이고, 자동 분류 실험(확장기능 §5.1)이 이 지점에서 실패한 이유이기도 합니다.

C·D 5건은 데이터의 한계가 아니라 **우리 쪽에서 더 할 수 있었던 부분**입니다.
darknet 의 `examples/demo.c`(webcam)처럼 저장소에 있는데 뽑지 않은 것이 2건,
하이퍼파라미터 표처럼 대응이 느슨해 비워 둔 것이 3건입니다.

```bash
python3 scripts/note2ingest/tally_unmapped.py --list    # 61건 전체를 판정과 함께
```

### 2.5 검증 방법

수치를 만든 뒤가 아니라 **만드는 과정에서** 검증이 걸리도록 했습니다.

| 검증 | 방법 | 잡은 것 |
|---|---|---|
| 스키마 | `ingest.py --dry-run` | 승인 스텁의 빈 초록·저자가 기존 값을 NULL 로 덮어쓸 뻔한 것 |
| 코드 원문 일치 | 저장소 커밋에서 직접 슬라이스 후 대조 | 노트 코드 13/14 불일치 |
| 재현성 | `seed_dump.sql` 복원 → `smoke.sh` | `smoke.sh` 가 demo seed 의 chunk id 를 하드코딩해 클론 경로에서 2건 실패 |
| 왕복 무결성 | 덤프 생성 후 md5 대조 | psql 출력을 줄 단위로 파싱해 값이 깨지던 문제 |
| 화면 노출 문자열 | DB 실측으로 표본 확인 | 매핑 근거 344건 중 112건에 마크다운 잔재 (화면 노출분 42건) |

마지막 항목은 `seed_dump.sql` 을 **실제로 복원해 보는 리뷰**에서 나왔습니다. diff 만
읽었으면 통과했을 건입니다.

---

## §3.x 검색 품질 평가

> 이 절의 해석("개선이 아니라 교정")은 B 파트입니다. 여기서는 측정 조건과 수치만 둡니다.

### 3.x.1 정답셋

논문 9편에 대해 큐레이터가 손으로 만든 **단락↔코드 315쌍**(대안 정답 포함 344건)입니다.
`database/eval_set_*.csv` 에 커밋돼 있으며, DB 자동증가 ID 가 아니라
**안정 키**(`arxiv_id, chunk_index, github_url, file_path, symbol_name, start_line`)로
보관합니다 — 깨끗한 DB 에 클론하면 ID 가 달라지기 때문입니다.

### 3.x.2 측정 조건

- 후보는 **그 논문에 연결된 저장소로 한정** — 서비스(`CodeSearchService.SEARCH_SQL_SCOPED`)와 동일한 SQL
- 단락당 후보 평균 **22개**
- 순위는 **pgvector 코사인 거리**로만 결정. LLM 은 순위에 관여하지 않음
- 한 단락에 대안 정답이 여러 개면 그중 가장 높은 순위를 인정(`--multi-gold`)

### 3.x.3 결과

| 지표 | 값 | 무작위 선택 시 | 배수 |
|---|---|---|---|
| Top-1 | 29.8% (94/315) | 5.3% | **5.6×** |
| Top-3 | 53.3% (168/315) | 16.0% | **3.3×** |
| **Top-5** | **65.4% (206/315)** | 26.7% | **2.5×** |
| MRR@10 | 0.454 | — | — |

**Top-5 가 제품과 맞는 지표입니다** — 화면이 후보 5개를 함께 보여주고 사용자가 그중에서
고릅니다. 파일 경로·줄 번호·원본 GitHub 링크를 함께 제시하므로 5개 중 고르는 비용이
저장소를 직접 뒤지는 것보다 훨씬 낮습니다.

**MRR 은 컷을 함께 적어야 합니다.** 순위를 어디서 자르느냐로 값이 달라집니다 —
같은 정답셋에서 `--k 5` 는 0.428, `--k 10` 은 0.454, 자르지 않으면 0.464 입니다.
Top-1/3/5 는 컷과 무관합니다.

**무작위 하한은 단락별 실제 후보 수로 계산**했습니다. 전체 코퍼스 크기(183)로 계산하면
배수가 열 배 가까이 부풀려집니다.

```bash
python3 scripts/note2ingest/eval_set_tool.py resolve database/eval_set_attention.csv /tmp/ids.csv
python3 scripts/eval_retrieval.py /tmp/ids.csv --k 10 --multi-gold
```

### 3.x.4 논문별 내역

| 논문 | 정답 단락 | Top-1 | Top-5 |
|---|---:|---:|---:|
| Llama 3 | 15 | **80.0%** | **100.0%** |
| Segment Anything | 25 | 44.0% | 92.0% |
| BERT | 37 | 32.4% | 75.7% |
| Attention | 52 | 34.6% | 71.2% |
| Vision Transformer | 33 | 24.2% | 66.7% |
| YOLO | 51 | 29.4% | 60.8% |
| Latent Diffusion | 29 | 13.8% | 55.2% |
| CLIP | 31 | 19.4% | 48.4% |
| **ResNet** | 42 | **19.0%** | **45.2%** |

ResNet 이 가장 낮습니다. 저장소가 Caffe `prototxt` 라 심볼 이름과 숫자뿐이어서 논문
문장과 임베딩이 잘 붙지 않습니다. 측정으로 확인하고
[#18](https://github.com/Ae-Ti/CodeAtlas/issues/18) 에 기록했습니다.

### 3.x.5 정답셋을 읽을 때의 한계

**정답셋은 큐레이터 판단이지 구현 가능성의 정답이 아닙니다.** "매핑하지 않음"에는
"구현이 존재하지 않음"과 "노트에 대응 코드가 없었음"이 섞여 있습니다. 이 구분은
자동 분류 실험(확장기능 §5.1)에서 실제로 문제가 됐고, 그 절에 사유를 적었습니다.

---

## §x. 라이선스 대응

### x.1 왜 대응이 필요한가

`database/ingest/*_ingest.json` 에 **저장소 코드 원문이 들어간 채 공개 저장소에 커밋**되고
화면에도 표시됩니다. 이는 각 저장소 라이선스가 말하는 **재배포**에 해당합니다.

- 인용 코드는 **수정하지 않았습니다.** 각 블록은 지정 커밋의 해당 줄 범위와 바이트 단위로 일치합니다
- 출처(저장소·커밋·파일·줄 번호)는 `code_blocks` 와 `database/seed_manifest.csv` 에 있습니다
- 라이선스 전문은 `database/licenses/` 에 원본 그대로 두었습니다
- 고지는 `database/THIRD_PARTY_LICENSES.md` 와 루트 `NOTICE` 입니다

### x.2 인용 저장소 12곳 — 전부 확인 완료

| 저장소 | 라이선스 | 커밋 | 블록 |
|---|---|---|---:|
| `jadore801120/attention-is-all-you-need-pytorch` | MIT | `132907d` | 33 |
| `CompVis/latent-diffusion` | MIT | `a506df5` | 21 |
| `pytorch/vision` | BSD-3-Clause | `0fba2e8` | 18 |
| `google-research/bert` | Apache-2.0 | `eedf571` | 18 |
| `pjreddie/darknet` | YOLO LICENSE v2 (public-domain style) | `f6afaab` | 18 |
| `facebookresearch/segment-anything` | Apache-2.0 | `dca509f` | 16 |
| `KaimingHe/deep-residual-networks` | MIT | `a7026cb` | 14 |
| `openai/CLIP` | MIT | `d05afc4` | 13 |
| `google-research/vision_transformer` | Apache-2.0 | `64801f1` | 12 |
| `meta-llama/llama3` | Meta Llama 3 Community License | `a0940f9` | 10 |
| `lucidrains/vit-pytorch` | MIT | `bb13e27` | 6 |
| `mlfoundations/open_clip` | MIT | `602d4af` | 4 |

`license_name` 은 **12/12 채워져 있습니다**(DB 실측).

### x.3 제외한 저장소 — 라이선스가 없으면 쓰지 않습니다

LICENSE 파일이 없는 저장소는 **모든 권리 유보** 상태라 재배포할 수 없습니다.
점수를 깎는 것이 아니라 후보에서 제외합니다.

- **U-Net 논문을 카탈로그에서 통째로 제외**했습니다. 인용하려던 저장소에 LICENSE 가
  없었고, 코드 블록을 빼면 남는 단락이 매핑 없이 뜨는 상태가 되기 때문입니다
  (`database/ingest/excluded/` 에 원본 노트 보존)
- GPL-3.0 저장소도 제외했습니다

**GitHub API 의 `spdx_id` 를 그대로 믿으면 안 됩니다.** `open_clip` 은 `NOASSERTION`
으로 뜨지만 본문이 MIT 이고, 반대로 `pjreddie/darknet` 은 LICENSE 가 있는데도
`NOASSERTION` 입니다. **LICENSE 원문을 읽고 판단**했습니다.

### x.4 별도 조건이 붙는 라이선스

**Meta Llama 3 Community License** 는 "Llama 3" 정의에 inference-enabling code 를
포함하므로 인용분이 그 대상입니다. §1.b 가 요구하는 세 가지를 이행했습니다.

| 조항 | 요구 | 이행 |
|---|---|---|
| §1.b.i(A) | 라이선스 사본 배포 | `database/licenses/meta-llama_llama3.txt` |
| §1.b.i(B) | **관련 화면에 "Built with Meta Llama 3" 표시** | 프론트 Footer 상시 표시 |
| §1.b.ii | 저작권 고지 | `NOTICE` |

### x.5 코드가 아닌 데이터 — PWC 아카이브

저장소 후보 추천(`scripts/suggest_repos.py`)이 쓰는
`database/pwc/links.tsv.gz` 는 Papers with Code 아카이브의 부분집합입니다
(논문↔저장소 링크 283,772건 / 논문 204,750편).

**CC-BY-SA-4.0** 이며 동일조건변경허락이 붙으므로, 파생물인 이 색인도 **같은 조건으로
배포**합니다. 저장소 전체의 MIT 와 별개이고 이 데이터 파일에만 적용됩니다
(운영규정 제8조⑤ 대응).

### x.6 프로젝트 자체 라이선스와 AI 모델

- CodeAtlas 소스: **MIT** (루트 `LICENSE`)
- 사용 모델: `qwen3:8b`(생성) · `nomic-embed-text`(임베딩) — 둘 다 **Apache-2.0**,
  **오픈웨이트 로컬 구동**이며 런타임에 상용 AI API 를 호출하는 경로가 없습니다
- 의존성 목록은 `docs/오픈소스SW_목록.md` 와 CycloneDX SBOM

---

## 남겨둔 것 (B 파트 또는 확인 대기)

- 아키텍처·기술스택 근거, "개선이 아니라 교정" 해석 문단, Limitations & Future Work — **B**
- 정부 지원사업 중복수혜([#15](https://github.com/Ae-Ti/CodeAtlas/issues/15)) — **팀 전원 해당 없음 확인·종결(2026-08-18)**. 보고서에 "해당 없음" 명시
- 개인별 기여도: `.mailmap` 적용 `git shortlog` 를 첨부하되 **"로컬 shortlog"임을 명시**해야
  합니다. GitHub 기여 그래프는 `.mailmap` 을 읽지 않아 손상된 이메일로 올라간 커밋
  8건이 여전히 미귀속입니다
