#!/usr/bin/env bash
# 개발 환경 점검 — 무엇이 준비됐고 무엇이 빠졌는지, 빠진 건 어떻게 채우는지 알려줍니다.
#
#   ./scripts/doctor.sh
#
# 실패해도 끝까지 진행합니다 (한 번에 전체 상태를 보기 위함).

CONTAINER="${CODEATLAS_PG_CONTAINER:-codeatlas-postgres}"
DB="${CODEATLAS_DB:-codeatlas}"
USER_NAME="${CODEATLAS_DB_USER:-codeatlas}"
OLLAMA="${OLLAMA_BASE_URL:-http://localhost:11434}"
BACKEND="${CODEATLAS_BACKEND:-http://localhost:8080}"

fail=0
ok()   { echo "  ✅ $1"; }
warn() { echo "  ⚠️  $1"; [ -n "${2:-}" ] && echo "     → $2"; }
bad()  { echo "  ❌ $1"; [ -n "${2:-}" ] && echo "     → $2"; fail=1; }

psqlq() { docker exec "$CONTAINER" psql -U "$USER_NAME" -d "$DB" -tAc "$1" 2>/dev/null; }

echo "▶ CodeAtlas 환경 점검"
echo
echo "[1/5] 필수 도구"

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then ok "docker ($(docker --version | cut -d, -f1))"
  else bad "docker는 있으나 데몬이 꺼져 있음" "Docker Desktop을 실행하세요"; fi
else
  bad "docker 없음" "https://docs.docker.com/get-docker/"
fi

if command -v java >/dev/null 2>&1; then
  jver=$(java -version 2>&1 | head -1 | grep -oE '"[0-9]+' | tr -d '"')
  if [ "${jver:-0}" -ge 21 ]; then ok "java $jver"
  else bad "java $jver — 21 이상 필요" "https://adoptium.net 에서 JDK 21 설치"; fi
else
  bad "java 없음" "JDK 21 이상 설치 필요"
fi

command -v python3 >/dev/null 2>&1 && ok "python3 ($(python3 --version | cut -d' ' -f2))" \
  || bad "python3 없음" "ingest.py / eval_retrieval.py 실행에 필요합니다"

echo
echo "[2/5] 데이터베이스"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  ok "컨테이너 '$CONTAINER' 실행 중"

  port=$(docker port "$CONTAINER" 5432/tcp 2>/dev/null | head -1 | sed 's/.*://')
  [ -n "$port" ] && ok "노출 포트 $port (접속 URL: jdbc:postgresql://localhost:$port/$DB)"

  if [ "$(psqlq 'SELECT 1')" = "1" ]; then
    ok "DB 접속 성공"

    tables=$(psqlq "SELECT count(*) FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name IN ('papers','paper_chunks','repositories',
                                         'paper_repositories','code_blocks','paper_code_mappings')")
    if [ "$tables" = "6" ]; then ok "테이블 6종 존재"
    else bad "테이블이 $tables/6개만 있음" "./scripts/reset_db.sh"; fi

    ext=$(psqlq "SELECT extversion FROM pg_extension WHERE extname='vector'")
    if [ -n "$ext" ]; then ok "pgvector $ext"
    else bad "pgvector 확장 없음" "./scripts/reset_db.sh"; fi

    dims=$(psqlq "SELECT DISTINCT vector_dims(embedding) FROM paper_chunks WHERE embedding IS NOT NULL")
    if [ -n "$dims" ]; then
      if [ "$dims" = "768" ]; then ok "임베딩 차원 768 (nomic-embed-text와 일치)"
      else bad "임베딩 차원이 $dims — 768이어야 함" "다른 모델로 만든 벡터입니다. UPDATE ... SET embedding=NULL 후 재생성"; fi
    fi
  else
    bad "DB 접속 실패" "로컬 PostgreSQL이 포트를 잡고 있을 수 있습니다. docker compose up -d 확인"
  fi
else
  bad "컨테이너 '$CONTAINER' 미실행" "docker compose up -d"
fi

echo
echo "[3/5] AI 모델 (Ollama)"

if curl -sf -m 3 "$OLLAMA/api/tags" >/dev/null 2>&1; then
  ok "Ollama 응답 ($OLLAMA)"
  models=$(curl -s -m 5 "$OLLAMA/api/tags")
  for m in qwen3:8b nomic-embed-text; do
    if echo "$models" | grep -q "\"$m"; then ok "모델 $m"
    else bad "모델 $m 없음" "ollama pull $m"; fi
  done

  # /api/tags 는 메타데이터만 돌려줍니다. 추론 엔진이 멈춰도 200이 나오므로
  # (실제로 겪었습니다 — 큐레이션 배치가 조용히 멈춰 있었습니다)
  # 임베딩과 생성을 한 번씩 실제로 호출해서 확인합니다.
  emb=$(curl -s -m 20 "$OLLAMA/api/embed" \
        -d '{"model":"nomic-embed-text","input":"healthcheck"}' 2>/dev/null)
  dims=$(echo "$emb" | python3 -c \
         "import json,sys; print(len(json.load(sys.stdin)['embeddings'][0]))" 2>/dev/null)
  if [ "$dims" = "768" ]; then
    ok "임베딩 생성 확인 (768차원)"
  elif [ -n "$dims" ]; then
    bad "임베딩 차원이 $dims — 768이어야 함" \
        "Script-3_pgvector.sql 의 vector(768) 과 맞지 않습니다"
  else
    bad "임베딩 생성 실패" "ollama serve 를 재시작하세요"
  fi

  # 생성 모델은 큐레이션 배치가 점유하고 있으면 응답이 한참 밀립니다.
  # "멈춤"과 "바쁨"은 밖에서 구분할 수 없으므로, 임베딩이 살아 있는지를 함께 봅니다.
  # 임베딩은 다른 러너라서 qwen3 가 바쁜 동안에도 응답합니다.
  #   임베딩 ❌            → 추론 엔진 전체가 멈춤 (재시작 필요)
  #   임베딩 ✅ + 생성 ❌   → 점유 중일 가능성이 큼 (경고만)
  gen_timeout="${CODEATLAS_OLLAMA_GEN_TIMEOUT:-90}"
  gen_start=$(date +%s)
  if curl -sf -m "$gen_timeout" "$OLLAMA/api/generate" \
       -d '{"model":"qwen3:8b","prompt":"ping","stream":false,"options":{"num_predict":1}}' \
       >/dev/null 2>&1; then
    gen_sec=$(( $(date +%s) - gen_start ))
    if [ "$gen_sec" -le 30 ]; then
      ok "텍스트 생성 확인 (${gen_sec}초)"
    else
      warn "텍스트 생성이 ${gen_sec}초 걸림" \
           "모델 최초 로딩이면 정상입니다. 반복되면 ollama serve 재시작"
    fi
  elif [ "$dims" = "768" ]; then
    warn "텍스트 생성이 ${gen_timeout}초 안에 응답 없음 (임베딩은 정상)" \
         "큐레이션 배치가 qwen3 를 점유 중일 수 있습니다. 배치가 없는데도 이러면 ollama serve 재시작"
  else
    bad "텍스트 생성·임베딩 모두 응답 없음" \
        "/api/tags 가 200 이어도 추론이 멈춰 있습니다. ollama serve 를 재시작하세요"
  fi
else
  bad "Ollama 응답 없음 ($OLLAMA)" "ollama serve  (미설치면 https://ollama.com)"
fi

echo
echo "[4/5] 데이터 적재 상태"

if [ "$(psqlq 'SELECT 1')" = "1" ]; then
  papers=$(psqlq "SELECT count(*) FROM papers")
  chunks=$(psqlq "SELECT count(*) FROM paper_chunks")
  blocks=$(psqlq "SELECT count(*) FROM code_blocks")
  maps=$(psqlq "SELECT count(*) FROM paper_code_mappings")
  echo "  papers $papers / chunks $chunks / code_blocks $blocks / mappings $maps"

  if [ "${papers:-0}" -eq 0 ]; then
    warn "적재된 논문 없음" "python3 scripts/ingest.py <파일>.json  또는  ./scripts/reset_db.sh --with-demo"
  else
    nullc=$(psqlq "SELECT count(*) FROM paper_chunks WHERE embedding IS NULL")
    nullb=$(psqlq "SELECT count(*) FROM code_blocks WHERE embedding IS NULL")
    if [ "${nullc:-0}" -eq 0 ] && [ "${nullb:-0}" -eq 0 ]; then
      ok "임베딩 전량 완료"
    else
      warn "임베딩 미완료 — chunk $nullc / code_block $nullb" \
           "cd backend && CODEATLAS_EMBEDDING_BACKFILL=true ./mvnw spring-boot:run"
    fi

    if [ "${maps:-0}" -eq 0 ]; then
      warn "사전계산된 매핑 없음 (agent/query가 매번 Qwen3를 호출합니다)" \
           "curl -X POST $BACKEND/api/admin/curate-pending"
    else
      ok "사전계산 매핑 ${maps}건"
    fi
  fi
fi

echo
echo "[5/5] 백엔드"

# 생존 확인은 /api/papers 로 합니다. /api/stats 는 프론트 연동 브랜치에서 추가된
# 엔드포인트라, 그걸로 확인하면 develop에서 멀쩡한 백엔드를 "미기동"으로 오판합니다.
if curl -sf -m 3 "$BACKEND/api/papers" >/dev/null 2>&1; then
  ok "백엔드 응답 ($BACKEND)"
  stats=$(curl -sf -m 3 "$BACKEND/api/stats" 2>/dev/null)
  if [ -n "$stats" ] && ! echo "$stats" | grep -q '"status":404'; then
    echo "     $stats"
  fi
else
  warn "백엔드 미기동 ($BACKEND)" "cd backend && ./mvnw spring-boot:run"
fi

echo
if [ "$fail" = 0 ]; then
  echo "🎉 필수 항목 모두 통과"
else
  echo "⚠️  ❌ 항목을 먼저 해결하세요"
fi
exit $fail
