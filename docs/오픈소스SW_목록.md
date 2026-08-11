# 오픈소스SW 활용 목록 및 SBOM

> 2차 평가 **오픈소스SW 적절성(10점)** · **작품발표 PT(10점, 라이브러리 표기 필수)** ·
> **라이선스 검증(5점)** 대응 문서
> 기준일: 2026-08-12 / 생성: `./scripts/gen_sbom.sh`

---

## 0. 이 문서의 범위 — 혼동 주의

CodeAtlas 에는 **성격이 다른 두 종류의 제3자 코드**가 있습니다. 서로 다른 문서로 관리합니다.

| | 무엇 | 문서 | 규모 |
|---|---|---|---|
| **① 의존 라이브러리** | 우리 소프트웨어가 **동작하기 위해 링크·번들하는** 것 (Spring, React …) | **이 문서** + `sbom/*.json` | **271개** |
| ② 인용 대상 저장소 | 우리가 화면에 **코드를 인용해 보여주는** 논문 구현체 (annotated-transformer, darknet …) | [`database/THIRD_PARTY_LICENSES.md`](../database/THIRD_PARTY_LICENSES.md), [README §10](../README.md) | 12개 저장소 |

②는 제품의 *데이터*이지 의존성이 아닙니다. SBOM 에는 ①만 들어갑니다.

---

## 1. 요약

| 구분 | 컴포넌트 | 라이선스 미기재 |
|---|---|---|
| 백엔드 (Maven, 전이 포함) | 129 | **0** |
| 프론트엔드 (npm, 전이 포함) | 142 | **0** |
| 인프라·AI 모델 (수동 기입) | 5 | 0 |
| **합계** | **276** | **0** |

### 라이선스 분포

| 백엔드 | 개수 | | 프론트엔드 | 개수 |
|---|---|---|---|---|
| Apache-2.0 | 114 | | MIT | 124 |
| MIT | 6 | | ISC | 11 |
| EPL-2.0 | 3 | | BSD-3-Clause | 2 |
| BSD 계열 | 3 | | Apache-2.0 | 2 |
| CC0-1.0 | 1 | | MPL-2.0 | 2 |
| MIT-0 | 1 | | MPL-2.0 OR Apache-2.0 | 1 |

**GPL·AGPL·LGPL 계열은 한 건도 없습니다.** 전량 permissive 또는 파일 단위 약한 카피레프트입니다.

---

## 2. SBOM 파일

기계 판독용 **CycloneDX** 형식입니다.

| 파일 | 대상 | 생성 도구 |
|---|---|---|
| [`sbom/backend-cyclonedx.json`](../sbom/backend-cyclonedx.json) | Maven 의존 트리 | `cyclonedx-maven-plugin` 2.9.1 |
| [`sbom/frontend-cyclonedx.json`](../sbom/frontend-cyclonedx.json) | npm 의존 트리 | `npm sbom` (npm 10.9.8) |

```bash
./scripts/gen_sbom.sh          # 두 파일을 다시 생성하고 라이선스 분포를 출력합니다
```

`pom.xml` 을 수정하지 않습니다 — 플러그인을 CLI 로 직접 호출합니다.

---

## 3. 직접 의존 — 발표자료용

전이 의존까지 271개지만, 발표에서 표기할 핵심은 아래입니다.

### 백엔드 — Java 21 / Spring Boot 4.1.0

| 라이브러리 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| `spring-boot-starter-webmvc` | 4.1.0 | Apache-2.0 | REST API |
| `spring-boot-starter-jdbc` | 4.1.0 | Apache-2.0 | DB 접근 (JdbcTemplate) |
| `spring-boot-starter-validation` | 4.1.0 | Apache-2.0 | 요청 검증 |
| **`spring-ai-starter-mcp-server-webmvc`** | 2.0.0 | Apache-2.0 | **MCP 서버 (SSE) — tool 4종 노출** |
| **`spring-ai-starter-model-ollama`** | 2.0.0 | Apache-2.0 | **Ollama 연동 (생성·임베딩)** |
| `postgresql` (JDBC) | 42.7.11 | BSD-2-Clause | PostgreSQL 드라이버 |

### 프론트엔드 — React 19 / TypeScript / Vite 8

| 라이브러리 | 버전 | 라이선스 | 용도 |
|---|---|---|---|
| `react` / `react-dom` | 19.2.8 | MIT | UI |
| `react-router-dom` | 7.18.2 | MIT | 라우팅 |
| **`@monaco-editor/react`** | 4.7.0 | MIT | **코드 뷰어 — 해당 줄 하이라이트** |
| **`@xyflow/react`** (React Flow) | 12.11.2 | MIT | **논문–코드 연결 그래프** |
| `react-markdown` | 10.1.0 | MIT | AI 설명 렌더링 |
| `lucide-react` | 1.28.0 | ISC | 아이콘 |
| `vite` | 8.2.0 | MIT | 빌드 (dev) |
| `typescript` | 6.0.3 | Apache-2.0 | 타입 검사 (dev) |
| `oxlint` | 1.77.0 | MIT | 린트 (dev) |

---

## 4. 인프라·AI 모델 — SBOM 이 잡지 못하는 것

컨테이너 이미지와 모델 가중치는 Maven·npm 어디에도 나타나지 않아 **수동으로 기입**합니다.
특히 AI 모델 2종은 **운영규정 제9조①(오픈웨이트 이상) 대응의 핵심**이라 누락되면 안 됩니다.

| 구분 | 항목 | 버전 | 라이선스 | 확인 방법 |
|---|---|---|---|---|
| DB | PostgreSQL | 17 | PostgreSQL License (permissive) | `pgvector/pgvector:pg17` 이미지 |
| DB 확장 | pgvector | 0.8.x | PostgreSQL License | 동일 이미지에 포함 |
| 런타임 | Ollama | 로컬 구동 | MIT | `ollama -v` |
| **AI 생성** | **`qwen3:8b`** | — | **Apache-2.0** | `ollama /api/show` 실측 |
| **AI 임베딩** | **`nomic-embed-text`** | 768차원 | **Apache-2.0** | `ollama /api/show` 실측 |

런타임에 **상용 AI API 를 호출하는 경로가 없습니다.** 자세한 내용은
[AI_모델_활용_명세.md](AI_모델_활용_명세.md).

---

## 5. 라이선스 검토 — 주의가 필요한 항목

permissive 가 아닌 6건을 개별 확인했습니다. **의무가 발생하거나 배포를 제약하는 건은 없습니다.**

| 컴포넌트 | SBOM 표기 | 실제 | 판단 |
|---|---|---|---|
| `ch.qos.logback:logback-classic` `logback-core` | EPL-2.0 | EPL-2.0 / LGPL-2.1 듀얼 | 수정 없이 의존만 함. 파일 단위 카피레프트라 우리 코드에 전이되지 않음 |
| `jakarta.annotation-api` | EPL-2.0 | EPL-2.0 (+ GPL-2.0 classpath 예외) | 표준 API, 수정 없음. classpath 예외로 링크 제약 없음 |
| `org.hdrhistogram:HdrHistogram` | CC0-1.0 | CC0-1.0 | 퍼블릭 도메인 헌정 — 의무 없음 |
| **`org.antlr:ST4`** | **BSD-4-Clause** ⚠️ | **BSD-3-Clause** | **SBOM 오분류.** §5.1 참고 |
| `org.antlr:antlr-runtime` | "BSD licence" | BSD-3-Clause | 동일 (ANTLR 프로젝트 라이선스) |
| `dompurify` | MPL-2.0 OR Apache-2.0 | 듀얼 | **Apache-2.0 을 선택**하여 사용 — MPL 의무 미발생 |
| `lightningcss` (+ darwin-arm64) | MPL-2.0 | MPL-2.0, **optional 의존** | 수정 없이 사용. 파일 단위 카피레프트라 우리 소스에 전이되지 않음 |

### 5.1 `org.antlr:ST4` 는 BSD-4-Clause 가 아닙니다

`cyclonedx-maven-plugin` 이 ST4 의 pom 에 적힌 `<name>The BSD License</name>` 를
**BSD-4-Clause 로 잘못 분류**했습니다. BSD-4-Clause 에는 "광고 문구에 사사(acknowledgement)를
표시하라"는 조항이 있어 실제로 의무가 생기므로 원문을 확인했습니다.

ANTLR 프로젝트의 실제 라이선스 원문은 **조항이 3개이고 광고 조항이 없습니다.**

```
1. Redistributions of source code must retain the above copyright notice ...
2. Redistributions in binary form must reproduce the above copyright notice ...
3. Neither name of copyright holders nor the names of its contributors may be used
   to endorse or promote products derived from this software ...
```

즉 **BSD-3-Clause** 이며, 발표자료에 별도 사사 문구를 넣을 의무는 없습니다.
ST4 는 Spring AI 가 끌어오는 전이 의존입니다.

> SBOM 은 자동 생성물이라 이런 오분류가 남습니다. 검증 단계에서 지적될 수 있어
> 여기에 정정 근거를 남겨 둡니다.

### 5.2 결론

- **GPL/AGPL/LGPL 단독 라이선스 컴포넌트 0건** — 소스 공개 의무가 전이되는 항목 없음
- 카피레프트 계열은 전부 **파일 단위(EPL-2.0, MPL-2.0)** 이며 **수정 없이 의존만** 함
- 본 저장소의 [MIT 라이선스](../LICENSE)와 충돌하는 항목 없음
- 이행해야 할 의무는 **저작권 고지 유지**이며, 이 문서와 `sbom/*.json` 으로 충족

---

## 6. 갱신 규칙

의존성을 추가·제거하면

1. `./scripts/gen_sbom.sh` 재실행
2. §1 요약 수치 갱신
3. 새 라이선스가 permissive 가 아니면 §5 에 검토 결과 추가

전이 의존이 늘어도 §3(직접 의존) 표는 그대로 둡니다 — 발표용 요약이기 때문입니다.
