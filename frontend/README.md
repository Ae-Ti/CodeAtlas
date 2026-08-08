# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.

---

## 백엔드 연결

화면은 전부 실제 백엔드 API를 호출합니다 (mock 데이터 없음).

```bash
# 1. 백엔드가 먼저 떠 있어야 합니다 (repo 루트에서)
docker compose up -d
cd backend && ./mvnw spring-boot:run       # localhost:8080

# 2. 프론트
cd frontend && npm run dev                 # localhost:5173
```

dev 서버는 `/api` 요청을 `localhost:8080`으로 프록시합니다 (`vite.config.ts`).
백엔드 주소가 다르면 `VITE_API_TARGET=http://host:port npm run dev`.
배포 시 절대 URL이 필요하면 `VITE_API_BASE`를 설정하세요.

백엔드가 꺼져 있으면 각 화면이 실행 방법을 안내하는 에러 카드를 보여줍니다.

### 화면별 사용 API

| 화면 | API |
|---|---|
| Dashboard | `GET /api/stats`, `GET /api/mappings?limit=6` |
| Papers | `GET /api/papers` |
| PaperDetail | `GET /api/papers`, `GET /api/papers/{id}/chunks`, `POST /api/mapping/search`, `POST /api/agent/query` |
| Agent | `POST /api/papers/chunks/search` → `POST /api/agent/query`, `POST /api/nl2sql` |
| Graph | `GET /api/mappings?limit=60` |

`precomputed` / `live` 배지는 그 응답이 사전계산된 매핑에서 온 것인지,
그 자리에서 Qwen3를 호출한 것인지를 나타냅니다. 데모 전에

```bash
curl -X POST localhost:8080/api/admin/curate-pending
```

를 한 번 돌려두면 전부 `precomputed`로 즉시 응답합니다.
