# CodeAtlas Frontend

논문 단락 ↔ 코드 구현 매핑을 보여주는 React 대시보드. 화면 5종과 Monaco 코드 뷰어,
React Flow 연결 그래프로 구성됩니다.

- React 19 / TypeScript / Vite 8
- Monaco Editor (코드 하이라이트) · React Flow (연결 그래프) · react-markdown (AI 설명)
- 상태 관리 라이브러리 없음 — `useApi` 훅 하나로 로딩/에러/데이터를 다룹니다

프로젝트 전체 개요는 [루트 README](../README.md) 를 보세요.

---

## 실행

```bash
# 1. 백엔드가 먼저 떠 있어야 합니다 (repo 루트에서)
docker compose up -d
cd backend && ./mvnw spring-boot:run       # localhost:8080

# 2. 프론트
cd frontend && npm install && npm run dev  # localhost:5173
```

| 스크립트 | 하는 일 |
|---|---|
| `npm run dev` | dev 서버 (HMR) |
| `npm run build` | `tsc -b` 타입 검사 후 프로덕션 번들 |
| `npm run preview` | 빌드 결과 미리보기 (localhost:4173) |
| `npm run lint` | Oxlint |

dev 서버는 `/api` 요청을 `localhost:8080` 으로 프록시합니다 (`vite.config.ts`).
같은 오리진으로 나가므로 dev 중에는 CORS 설정에 의존하지 않습니다.

| 환경변수 | 용도 |
|---|---|
| `VITE_API_TARGET` | dev 프록시 대상 (기본 `http://localhost:8080`) |
| `VITE_API_BASE` | 배포 시 API 절대 URL (기본값은 빈 문자열 = 같은 오리진) |

백엔드가 꺼져 있으면 각 화면이 실행 방법을 안내하는 에러 카드를 보여줍니다.
mock 데이터는 없습니다 — 전부 실제 API 를 호출합니다.

---

## 화면별 사용 API

| 화면 | 파일 | API |
|---|---|---|
| Dashboard | [src/pages/Dashboard.tsx](src/pages/Dashboard.tsx) | `GET /api/stats`, `GET /api/mappings?limit=6` |
| Papers | [src/pages/Papers.tsx](src/pages/Papers.tsx) | `GET /api/papers` |
| PaperDetail | [src/pages/PaperDetail.tsx](src/pages/PaperDetail.tsx) | `GET /api/papers`, `GET /api/papers/{id}/chunks`, `POST /api/mapping/search`, `POST /api/agent/query` |
| Agent | [src/pages/Agent.tsx](src/pages/Agent.tsx) | `POST /api/papers/chunks/search` → `POST /api/agent/query`, `POST /api/nl2sql` |
| Graph | [src/pages/Graph.tsx](src/pages/Graph.tsx) | `GET /api/mappings?limit=60` |

`precomputed` / `live` 배지는 그 응답이 사전계산된 매핑에서 온 것인지, 그 자리에서
Qwen3 를 호출한 것인지를 나타냅니다. 데모 전에

```bash
curl -X POST localhost:8080/api/admin/curate-pending
```

를 한 번 돌려두면 전부 `precomputed` 로 즉시 응답합니다. 배치는 chunk 당 Qwen3 를 1회
호출하므로 오래 걸립니다 — 진행률은 `GET /api/admin/curate-status` 로 확인하세요.

---

## 구조

```
src/
├── api/client.ts        백엔드 API 클라이언트 + ApiError
│                        타입이 백엔드 응답 record 와 1:1 — DTO 를 바꾸면 여기도 바꿉니다
├── hooks/
│   ├── useApi.ts        로딩·에러·데이터 상태
│   └── useAnimateNumber.ts
├── components/
│   ├── AsyncStates.tsx  로딩 스켈레톤 / 에러 카드 / 빈 상태 (전 화면 공용)
│   └── layout/Header.tsx
└── pages/               화면 5종
```

응답 스키마는 [docs/api-spec.md](../docs/api-spec.md) 가 기준입니다.

> `tsconfig` 에 `erasableSyntaxOnly` 가 켜져 있어 생성자 파라미터 프로퍼티,
> `enum` 등 런타임 코드를 만드는 TypeScript 문법은 쓸 수 없습니다.

---

## Oxlint 타입 인식 규칙 (선택)

타입 기반 린트 규칙을 쓰려면 `oxlint-tsgolint` 를 설치하고 `.oxlintrc.json` 에
`options.typeAware` 를 켜면 됩니다. 규칙 목록은
[Oxlint 문서](https://oxc.rs/docs/guide/usage/linter/rules) 참고.
