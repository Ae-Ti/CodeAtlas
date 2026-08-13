#!/usr/bin/env bash
# CodeAtlas 백엔드 스모크 테스트 — 기동된 서버의 전체 API를 한 번씩 호출합니다.
#
#   ./scripts/smoke.sh              # 기본 http://localhost:8080
#   BASE=http://1.2.3.4:8080 ./scripts/smoke.sh
#
# AI 엔드포인트(/api/agent/query, /api/nl2sql)는 Ollama 응답을 기다리므로 수십 초 걸릴 수 있습니다.

set -u
BASE="${BASE:-http://localhost:8080}"
fail=0

check() {  # check <이름> <기대 status> <curl 인자...>
  local name="$1" expected="$2"; shift 2
  local code
  code=$(curl -s -o /tmp/codeatlas-smoke.out -w '%{http_code}' "$@")
  if [ "$code" = "$expected" ]; then
    echo "  ✅ $name ($code)"
  else
    echo "  ❌ $name — 기대 $expected, 실제 $code"
    head -c 300 /tmp/codeatlas-smoke.out; echo
    fail=1
  fi
}

echo "▶ CodeAtlas 백엔드 스모크 테스트: $BASE"

echo "[1/8] 논문 조회"
check "GET  /api/papers"            200 "$BASE/api/papers"
check "GET  /api/papers/1/chunks"   200 "$BASE/api/papers/1/chunks"
check "GET  /api/papers/999/chunks" 404 "$BASE/api/papers/999/chunks"

echo "[2/8] chunk 벡터 검색"
check "POST /api/papers/chunks/search" 200 -X POST "$BASE/api/papers/chunks/search" \
  -H 'Content-Type: application/json' -d '{"queryText":"multi head attention","topK":3}'

# chunk id는 적재 이력에 따라 달라지므로 하드코딩하지 않고 논문 1의 첫 chunk를 씁니다.
# (demo seed는 id 101을 명시적으로 넣지만, ingest.py 적재본이나 seed_dump.sql 복원본은 다릅니다)
CHUNK_ID=$(curl -s "$BASE/api/papers/1/chunks" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)[0]['chunkId'])" 2>/dev/null)
if [ -z "${CHUNK_ID:-}" ]; then
  echo "  ❌ 논문 1의 chunk id를 읽지 못했습니다 — [3/8]·[5/8]은 의미 없는 결과가 됩니다"
  fail=1; CHUNK_ID=1
fi

echo "[3/8] 코드 매핑 검색 (chunkId=$CHUNK_ID)"
check "POST /api/mapping/search" 200 -X POST "$BASE/api/mapping/search" \
  -H 'Content-Type: application/json' -d "{\"paperId\":1,\"chunkId\":$CHUNK_ID,\"topK\":5}"

echo "[4/8] 없는 chunk 요청"
check "POST /api/mapping/search (404)" 404 -X POST "$BASE/api/mapping/search" \
  -H 'Content-Type: application/json' -d '{"paperId":1,"chunkId":99999}'

echo "[5/8] MCP Agent 질의 (사전계산 결과가 없으면 Ollama 호출 — 느립니다)"
check "POST /api/agent/query" 200 -X POST "$BASE/api/agent/query" \
  -H 'Content-Type: application/json' \
  -d "{\"query\":\"이 논문의 attention 부분은 코드로 어떻게 구현됐어?\",\"paperId\":1,\"chunkId\":$CHUNK_ID}"
if command -v python3 >/dev/null; then
  src=$(python3 -c "import json;print(json.load(open('/tmp/codeatlas-smoke.out')).get('source',''))" 2>/dev/null)
  echo "     └ source=$src  (precomputed면 큐레이션 배치가 이미 돌아간 상태)"
fi

echo "[6/8] 큐레이션 배치 (미큐레이션 chunk가 있으면 chunk당 Qwen3 1회 — 매우 느립니다)"
check "POST /api/admin/curate-pending" 200 -X POST "$BASE/api/admin/curate-pending"

echo "[7/8] NL2SQL (Ollama 호출 — 느립니다)"
check "POST /api/nl2sql" 200 -X POST "$BASE/api/nl2sql" \
  -H 'Content-Type: application/json' -d '{"query":"star 수 상위 5개 repository 알려줘"}'

echo "[8/8] MCP SSE 엔드포인트"
code=$(curl -s -m 2 -o /dev/null -w '%{http_code}' "$BASE/sse")
if [ "$code" = "200" ] || [ "$code" = "000" ]; then   # 000 = 스트림 유지 중 타임아웃(정상)
  echo "  ✅ GET  /sse"
else
  echo "  ❌ GET  /sse — 실제 $code"; fail=1
fi

echo
[ "$fail" = 0 ] && echo "🎉 전체 통과" || echo "⚠️  실패한 항목이 있습니다"
exit $fail
