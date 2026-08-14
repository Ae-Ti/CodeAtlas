# 기여 가이드

2인 팀(A·B)이 두 주 동안 부딪히면서 정한 규칙을 모아둔 문서입니다.
"이렇게 하는 게 좋다"가 아니라 **실제로 사고가 나서 정한 것들**이라 근거를 같이 적었습니다.

- 프로젝트 개요는 [README](README.md)
- 역할·산출물 일정은 [기획서](docs/CodeAtlas_기획서.md) · [역할분담](docs/CodeAtlas_팀_역할분담.md)

## 1. 브랜치

| 브랜치 | 용도 |
|---|---|
| `main` | 최종 안정본. 시연·제출 직전에만 머지 |
| `develop` | 기본 브랜치. 모든 PR 의 base |
| `feature/*` | 기능 개발 (B) |
| `data/*` | 카탈로그 데이터 (A) |
| `docs/*` | 문서 |
| `fix/*` | 버그 수정 |

**PR base 는 항상 `develop`** 입니다. 초기에 PR 두 건이 `main` 으로 바로 들어가
`develop` 이 `main` 보다 5커밋 뒤처지는 상태가 됐던 적이 있습니다. 그 뒤로 `main` 은
잠가두고 있습니다.

## 2. 리뷰 — 자기 PR 은 자기가 머지하지 않습니다

2인 팀이라 형식적으로 보일 수 있지만 실제로 효과가 있었습니다. 서로 리뷰하면서
잡은 것들입니다.

- 평가 스크립트가 서비스 SQL 과 어긋나 **24pp** 낮은 수치를 보고할 뻔한 것
- 랜덤 하한을 전체 코퍼스로 계산해 배수가 **10배 부풀려져** 있던 것
- 큐레이션 배치가 폴백 후보를 `mapping_method='AI'` 로 영구 저장하던 것
- 공개 저장소에 커밋될 파일에 로컬 절대경로가 들어간 것

**메신저 승인은 리뷰 기록이 아닙니다.** GitHub 의 Approve 를 눌러야 심사 증빙이 됩니다.
승인 본문에는 "무엇을 확인했는지"를 적습니다 — "LGTM" 한 줄은 나중에 근거가 안 됩니다.

리뷰어가 자리에 없어 막힐 때는, 상대 영역이 아닌 문서·스크립트 PR 에 한해
"훑고 넘겨도 되는 것"으로 분류해 요청할 수 있습니다. 코드 PR 은 예외 없이 실질 리뷰를 받습니다.

## 3. 파일 소유권

같은 파일을 양쪽이 고치면 머지 충돌보다 **서로의 수정을 덮어쓰는 사고**가 더 문제였습니다.
소유자가 아닌 쪽은 PR 로 제안하고, 소유자가 판단합니다.

| 경로 | 소유 |
|---|---|
| `database/ingest/**`, `database/eval_set_*.csv` | **A** |
| `database/seed_dump.sql`, `database/seed_manifest.csv`, `database/THIRD_PARTY_LICENSES.md`, `database/licenses/**` | **A** |
| `scripts/note2ingest/**` (노트 → ingest JSON 변환) | **A** |
| `scripts/suggest_repos.py`, `scripts/build_pwc_index.py`, `database/pwc/**` (저장소 후보 추천) | **A** |
| `backend/src/main/java/**/mapping/**` (검색·매핑) | **A** |
| `scripts/ingest.py`, `scripts/eval_retrieval.py`, `scripts/doctor.sh`, `scripts/reset_db.sh`, `scripts/smoke.sh` | **B** |
| `backend/src/main/java/**/agent/**`, `**/mcp/**`, `**/nl2sql/**`, `**/embedding/**` | **B** |
| `frontend/**` | **B** |
| `database/Script-*.sql`, `database/seed_demo.sql` | **B** |
| `docs/api-spec.md`, `docs/backend-setup.md`, `docs/demo-scenario.md`, `docs/AI_모델_활용_명세.md` | **B** |
| `docs/A_논문DB구축_가이드.md`, `docs/data-pipeline-guide.md` | **B** — A 가 실제 사용자라 바꿀 일이 생기면 PR |
| `docs/CodeAtlas_기획서.md`, `docs/CodeAtlas_팀_역할분담.md`, `README.md` | **공동** — 상대에게 알리고 수정 |
| 위에 없는 `docs/**`, 날짜별 정리 문서 | **작성자** — `git log --diff-filter=A -- <파일>` 로 확인 |

**eval CSV 는 A 만 커밋합니다.** DB 를 실제로 돌려야 나오는 산출물이라 양쪽이 각자
생성하면 매번 충돌합니다.

**`docs/api-spec.md` 는 응답 스키마가 바뀌는 PR 과 같이 갑니다.** 소유자가 B 라서
A 가 백엔드 응답 변화를 발견해도 직접 못 고칩니다 — 필드를 추가·삭제하는 쪽이
같은 PR 안에서 문서를 맞춰 주세요.

포트 인터페이스(`mcp/port/CodeAtlasPorts.java`)는 A↔B 계약이라 어느 쪽이든 바꾸면
상대에게 알립니다.

## 4. 커밋

```
<type>(<scope>): <한 줄 요약>

무엇을 왜 바꿨는지. 수치가 있으면 before → after 로.
검증한 방법도 같이.
```

`type` 은 `feat` `fix` `docs` `chore` `refactor` `test` 를 씁니다.
`scope` 는 `ingest` `mapping` `eval` `agent` `db` `data` `license` 같은 영역 이름입니다.

수치를 바꾸는 커밋은 **검증 방법을 본문에 적습니다.** "원문 일치 182/182",
"재적재 후 수치 동일 — 멱등 확인" 처럼 다음 사람이 재현할 수 있는 형태로요.

### author 설정 확인

작업 시작 전에 한 번 확인하세요.

```bash
git config --get-all user.email    # 값이 하나만 나와야 합니다
```

`--global user.email` 에 같은 주소가 **4개 항목**으로 들어가 있어 git 이 이어붙인 값을
커밋에 넣은 적이 있습니다. 그 커밋 8건은 지금도 GitHub 기여로 안 잡힙니다.
`--get-all` 로 봐야 보입니다 — `git config user.email` 은 마지막 하나만 보여줍니다.

## 5. 히스토리 재작성

- **push 전**이면 `rebase --exec` 로 자유롭게 정리합니다 (author 교정 등, 작성일시는 보존됨)
- **push 후**에는 `--force-with-lease` 만 씁니다. `--force` 는 상대 작업을 지웁니다
- **머지된 커밋은 재작성하지 않습니다.** `develop`·`main` 을 다시 쓰면 상대의 작업
  브랜치가 전부 리베이스 대상이 됩니다. 과거 author 문제는 `.mailmap` 으로 처리합니다

rebase 전에 `git fetch` 를 먼저 하세요. 낡은 `origin/develop` 참조 위로 replay 하면
이미 머지된 커밋의 사본이 생깁니다.

## 6. 이슈

라벨은 세 축으로 씁니다.

| 축 | 라벨 |
|---|---|
| 담당 | `owner: A` · `owner: B` · `owner: 공동` |
| 성격 | `데이터` · `평가` · `제출물` · `컴플라이언스` · `documentation` · `bug` · `enhancement` · `Future Work` |
| 급함 | `우선순위: 높음` |

마일스톤은 `1주차 (~8.12)` · `2주차 (~8.19)` · `3주차 · 제출 (~8.27)` 입니다.

**PR 본문에 `Closes #N` 을 넣습니다.** 머지되면 이슈가 자동으로 닫히고 추적이 끊기지 않습니다.

## 7. 데이터를 고칠 때

카탈로그 데이터는 다른 산출물과 얽혀 있어 순서가 있습니다.

```
ingest JSON 수정
  → scripts/ingest.py 로 재적재        (embedding 이 NULL 로 초기화됨)
  → 임베딩 backfill                     (약 1분)
  → 큐레이션                            (chunk 당 Qwen3 1회, 376 chunk 기준 약 100분)
  → 정답셋 재생성 · 평가 재측정
```

**chunk 본문을 고치면 상대에게 알립니다.** 낡은 AI 설명이 남는 문제가 있었고
(`391658e` 로 `ingest.py` 가 정리하도록 고쳤습니다), 큐레이션이 100분짜리라
모르고 진행하면 그 시간이 버려집니다.

### 인용 코드를 추가할 때

논문 코드를 새로 인용하면 **저장소 라이선스를 반드시 확인합니다.**
`*_ingest.json` 에 코드 원문이 들어간 채 공개 저장소에 커밋되므로 재배포에 해당합니다.

- LICENSE 파일 **원문**을 확인합니다. GitHub API 의 `spdx_id` 는 틀릴 수 있습니다
  (`open_clip` 은 `NOASSERTION` 으로 뜨지만 본문이 MIT, `ST4` 는 BSD-4 로 분류됐지만 실제 BSD-3)
- LICENSE 가 **없는** 저장소는 쓰지 않습니다. 모든 권리 유보 상태입니다
- `database/THIRD_PARTY_LICENSES.md` 와 `database/licenses/` 에 고지를 추가합니다
- UI 표시를 요구하는 라이선스가 있습니다 (Meta Llama 3 Community License §1.b.i(B))

## 8. 스크립트에 절대경로를 넣지 않습니다

공개 저장소라 로컬 경로가 그대로 노출되고, 다른 사람이 실행할 수 없습니다.
저장소 기준 상대경로로 계산하고, 필요하면 환경변수로 덮어쓰게 합니다.

```python
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ING = os.environ.get('CODEATLAS_INGEST_DIR') or os.path.join(ROOT, 'database', 'ingest')
```

## 9. psql 출력을 행 단위로 파싱하지 않습니다

논문 본문과 코드에는 줄바꿈이 있습니다. `psql -tA` 결과를 `splitlines()` 로 자르면
값이 조용히 깨집니다 — 양쪽이 각각 한 번씩 밟았습니다(덤프 생성, 교차 오염 분석).

서버에서 `string_agg` 나 `json_agg` 로 한 덩어리를 만들어 받으세요.

## 10. 검증

PR 을 올리기 전에 해당하는 것만 돌리면 됩니다.

```bash
./scripts/doctor.sh                                   # 환경 점검
python3 scripts/ingest.py <json> --dry-run            # 데이터 스키마 검증
./scripts/smoke.sh                                    # 백엔드 API 전체
cd frontend && npx tsc -b                             # 프론트 타입
cd backend && ./mvnw test                             # 백엔드 단위 테스트
```

데이터 PR 은 `--dry-run` 통과만으로 부족합니다. **실제 적재까지 해보고 수치를 본문에
적습니다.** 스키마는 통과하는데 적재에서 깨지는 경우가 있었습니다
(`start_line` 이 NULL 이면 `uq_code_blocks_location` 이 무력화돼 재적재 시 중복 행 발생).
