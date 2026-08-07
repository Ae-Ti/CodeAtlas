# Claude Code 핸드오프 — pgvector 스키마 반영 + 사전계산 아키텍처 도입

> 이 문서를 Claude Code에게 그대로 붙여넣거나 참고 자료로 던져주면 됩니다.
> 목표: `codeatlas-backend-scaffold/`의 파일들을 실제 `backend/` 프로젝트에 통합하고, 컴파일 가능한 상태로 만드는 것.

---

## 0. 작업 전 Claude Code가 먼저 확인해야 할 것

1. `backend/` 프로젝트의 **실제 base package명**을 기존 `pom.xml`/기존 Java 파일에서 확인할 것. 아래 파일들은 전부 `com.codeatlas.backend`를 가정하고 작성되어 있음 — 실제 패키지명이 다르면 **모든 파일의 `package` 선언과 import 문을 일괄 치환**해야 함.
2. `@McpTool` / `@McpToolParam`의 정확한 import 경로를 프로젝트에 이미 추가된 `spring-ai-starter-mcp-server-webmvc` 버전 기준으로 확인할 것 (문서마다 `org.springframework.ai.mcp.annotation` / `org.springframework.ai.mcp.server.annotation`으로 갈려 있어 버전에 따라 다를 수 있음).
3. `EmbeddingModel.embed(String)` 메서드 시그니처를 실제 추가된 Spring AI 버전 기준으로 확인할 것.

---

## 1. 파일 매핑 (소스 → 목적지)

| 소스 (scaffold) | 목적지 (실제 repo) | 담당/브랜치 | 상태 |
|---|---|---|---|
| `database/Script-3_pgvector.sql` | `database/Script-3_pgvector.sql` | A / `feature/retrieval-pipeline` | 신규 |
| `pom.xml` | `backend/pom.xml` (기존 파일에 의존성만 병합) | 공동 | 병합 필요 |
| `resources/application-ai.yml` | `backend/src/main/resources/application-ai.yml` | B / 공동 | 신규 |
| `mcp/dto/McpDtos.java` | `backend/src/main/java/{basepkg}/mcp/dto/McpDtos.java` | B / `feature/agent-mcp` | 신규 |
| `mcp/port/CodeAtlasPorts.java` | `backend/src/main/java/{basepkg}/mcp/port/CodeAtlasPorts.java` | B / `feature/agent-mcp` | 신규 |
| `mcp/tools/SearchPaperChunkTool.java` | `backend/src/main/java/{basepkg}/mcp/tools/SearchPaperChunkTool.java` | B / `feature/agent-mcp` | 신규 |
| `mcp/tools/FindCodeImplementationTool.java` | `backend/src/main/java/{basepkg}/mcp/tools/FindCodeImplementationTool.java` | B / `feature/agent-mcp` | 신규 |
| `mcp/tools/QueryMetadataSqlTool.java` | `backend/src/main/java/{basepkg}/mcp/tools/QueryMetadataSqlTool.java` | B / `feature/agent-mcp` | 신규 |
| `mcp/tools/CurateContextTool.java` | `backend/src/main/java/{basepkg}/mcp/tools/CurateContextTool.java` | B / `feature/agent-mcp` | 신규 |
| `agent/AgentQueryController.java` | `backend/src/main/java/{basepkg}/agent/AgentQueryController.java` | B / `feature/agent-mcp` | 신규 |
| `agent/MappingReadService.java` | `backend/src/main/java/{basepkg}/agent/MappingReadService.java` | B / `feature/agent-mcp` | 신규 |
| `agent/CurationBatchService.java` | `backend/src/main/java/{basepkg}/agent/CurationBatchService.java` | B / `feature/agent-mcp` | 신규 |
| `agent/AdminCurationController.java` | `backend/src/main/java/{basepkg}/agent/AdminCurationController.java` | B / `feature/agent-mcp` | 신규 |
| `nl2sql/Nl2SqlController.java` | `backend/src/main/java/{basepkg}/nl2sql/Nl2SqlController.java` | B / `feature/nl2sql-tacc` | 신규 |
| `nl2sql/MetadataSqlService.java` | `backend/src/main/java/{basepkg}/nl2sql/MetadataSqlService.java` | B / `feature/nl2sql-tacc` | 신규 |
| `paper/PaperChunkSearchService.java` | `backend/src/main/java/{basepkg}/paper/PaperChunkSearchService.java` | **A 검토 필요** / `feature/retrieval-pipeline` | B 초안 → A PR 리뷰 |
| `mapping/CodeSearchService.java` | `backend/src/main/java/{basepkg}/mapping/CodeSearchService.java` | **A 검토 필요** / `feature/vector-search-api` | B 초안 → A PR 리뷰 |
| `docs/api-spec.md` | `docs/api-spec.md` (기존 파일 있으면 교체) | 공동 | 갱신 |
| `docs/backend-setup.md` | `docs/backend-setup.md` | 공동 | 신규 |

`{basepkg}`는 0번에서 확인한 실제 base package 경로로 치환.

---

## 2. Claude Code 작업 지침 (순서대로)

1. `backend/` 프로젝트 존재 여부 확인. 없으면 `docs/backend-setup.md`의 1~2단계(Spring Initializr 생성, 의존성 추가)부터 수행.
2. 위 표대로 파일을 목적지에 복사하고, base package가 다르면 전체 파일의 `package`/`import` 문을 일괄 치환.
3. `pom.xml`에 `spring-ai-bom`(dependencyManagement), `spring-ai-starter-mcp-server-webmvc`, `spring-ai-starter-model-ollama`, `postgresql`, `spring-boot-starter-jdbc`가 이미 있는지 확인 후 없는 것만 추가 (기존 의존성 중복 추가 금지).
4. `application.yml`에 `spring.config.import: application-ai.yml` 한 줄 추가.
5. `database/Script-2.sql`이 이미 적용된 상태인지 확인 후, **그 다음 순서로** `Script-3_pgvector.sql` 적용.
6. `./mvnw compile`로 컴파일만 우선 확인. **여기서 실행(run)까지는 하지 말 것** — `PaperChunkSearchService`/`CodeSearchService`는 A 검토 전 초안이라 로컬 DB 데이터 없이 돌리면 의미 있는 결과가 나오지 않음.
7. 컴파일 에러가 나면 원인(대부분 import 경로 문제일 가능성 높음)을 리포트하고, 임의로 로직을 바꾸지 말고 사람에게 확인 요청할 것.
8. 변경 사항을 아래 "3. 커밋 규칙" 기준으로 **브랜치별로 나눠서 커밋**. `main`이나 `develop`에 직접 push 금지.

---

## 3. 커밋/PR 규칙 (기존 병합 규칙 그대로 적용)

- `feature/agent-mcp`, `feature/nl2sql-tacc` 브랜치 커밋은 B 명의로 진행 (B가 이미 다 구현한 부분).
- `feature/retrieval-pipeline`, `feature/vector-search-api` 브랜치의 `PaperChunkSearchService.java`, `CodeSearchService.java`는 **B 초안임을 PR 설명에 명시**하고, **A가 리뷰·수정 후 직접 merge**하도록 남겨둘 것 (자동 merge 금지 — "DB schema 변경 → A 승인 필요" 규칙 적용 대상).
- `database/Script-3_pgvector.sql`도 같은 이유로 A 리뷰 대상.
- `pom.xml`, `application.yml` 등 공동 관리 파일은 PR에 "API/설정 변경 여부" 명시.

---

## 4. 완료 후 사람이 확인할 것 (Claude Code 작업 범위 밖)

- [ ] Ollama 설치 + `qwen3:8b`, `nomic-embed-text` pull
- [ ] PostgreSQL + pgvector 컨테이너 기동, Script-2/Script-3 적용 확인
- [ ] A가 `PaperChunkSearchService`/`CodeSearchService` 실제 로직 검토·merge
- [ ] 샘플 데이터 1~2건으로 `POST /api/admin/curate-pending` → `POST /api/agent/query` 수동 테스트
- [ ] A의 Python 파이프라인 임베딩 로직을 Ollama API 호출로 전환 (sentence-transformers 대신)
