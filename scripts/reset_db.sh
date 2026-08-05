#!/usr/bin/env bash
# DB 스키마 초기화 — Script-2 → Script-3 순으로 다시 적용합니다.
#
#   ./scripts/reset_db.sh              # 빈 DB (실데이터 적재용)
#   ./scripts/reset_db.sh --with-demo  # demo seed까지 적재 (백엔드 혼자 돌려볼 때)
#
# Script-2.sql 맨 위에 DROP TABLE이 있어 몇 번을 돌려도 같은 결과가 됩니다.
# docker compose down -v 와 달리 볼륨을 지우지 않으므로 훨씬 빠릅니다.
#
# ⚠️ 기존 데이터가 전부 삭제됩니다.

set -euo pipefail

CONTAINER="${CODEATLAS_PG_CONTAINER:-codeatlas-postgres}"
DB="${CODEATLAS_DB:-codeatlas}"
USER_NAME="${CODEATLAS_DB_USER:-codeatlas}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

WITH_DEMO=0
[ "${1:-}" = "--with-demo" ] && WITH_DEMO=1

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "❌ '$CONTAINER' 컨테이너가 실행 중이 아닙니다. 먼저 docker compose up -d 를 실행하세요." >&2
  exit 1
fi

apply() {
  echo "  → $(basename "$1")"
  docker exec -i "$CONTAINER" psql -U "$USER_NAME" -d "$DB" -v ON_ERROR_STOP=1 -q < "$1"
}

echo "▶ DB 초기화: $CONTAINER/$DB"
apply "$ROOT/database/Script-2.sql"
apply "$ROOT/database/Script-3_pgvector.sql"

if [ "$WITH_DEMO" = 1 ]; then
  apply "$ROOT/database/seed_demo.sql"
fi

docker exec "$CONTAINER" psql -U "$USER_NAME" -d "$DB" -tAc "
SELECT '  papers ' || (SELECT count(*) FROM papers)
    || ' / chunks ' || (SELECT count(*) FROM paper_chunks)
    || ' / repos ' || (SELECT count(*) FROM repositories)
    || ' / code_blocks ' || (SELECT count(*) FROM code_blocks)
    || ' / mappings ' || (SELECT count(*) FROM paper_code_mappings)"

echo "✅ 완료"
[ "$WITH_DEMO" = 0 ] && echo "   이제 scripts/ingest.py 로 실데이터를 넣으세요."
exit 0
