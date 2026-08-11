#!/usr/bin/env bash
# SBOM 생성 — 백엔드(Maven) / 프론트엔드(npm) 의존성을 CycloneDX 형식으로 뽑습니다.
#
#   ./scripts/gen_sbom.sh
#
# 결과물:
#   sbom/backend-cyclonedx.json    Maven 의존 트리 (전이 포함)
#   sbom/frontend-cyclonedx.json   npm 의존 트리 (전이 포함)
#
# pom.xml 을 수정하지 않습니다 — CycloneDX 플러그인을 CLI 로 직접 호출합니다.
# 의존성을 추가·제거했다면 다시 돌리고 docs/오픈소스SW_목록.md 의 수치도 갱신하세요.
#
# ⚠️ 이 SBOM 은 "우리가 의존하는 라이브러리"입니다.
#    "우리가 코드를 인용한 저장소"는 database/THIRD_PARTY_LICENSES.md 쪽입니다. 서로 다릅니다.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/sbom"
CDX_VERSION="${CDX_VERSION:-2.9.1}"

mkdir -p "$OUT"

echo "▶ 백엔드 (Maven + CycloneDX $CDX_VERSION)"
(
  cd "$ROOT/backend"
  ./mvnw -q -DskipTests \
    "org.cyclonedx:cyclonedx-maven-plugin:${CDX_VERSION}:makeAggregateBom" \
    -DoutputFormat=json -DoutputName=bom
)
cp "$ROOT/backend/target/bom.json" "$OUT/backend-cyclonedx.json"
echo "  → sbom/backend-cyclonedx.json"

echo "▶ 프론트엔드 (npm sbom — npm 9+ 필요)"
(
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm ci
  npm sbom --sbom-format cyclonedx > "$OUT/frontend-cyclonedx.json"
)
echo "  → sbom/frontend-cyclonedx.json"

echo
python3 - "$OUT" <<'PY'
import json, sys, collections, pathlib
out = pathlib.Path(sys.argv[1])
total = 0
for label, f in (("백엔드", "backend-cyclonedx.json"), ("프론트엔드", "frontend-cyclonedx.json")):
    comps = json.loads((out / f).read_text()).get("components", [])
    total += len(comps)
    lic = collections.Counter()
    missing = 0
    for c in comps:
        names = [(l.get("license") or {}).get("id") or (l.get("license") or {}).get("name") or l.get("expression")
                 for l in (c.get("licenses") or [])]
        names = [n for n in names if n]
        lic[names[0]] += 1 if names else 0
        if not names:
            missing += 1
    print(f"  {label}: 컴포넌트 {len(comps)}개 / 라이선스 미기재 {missing}개")
    for k, v in lic.most_common(5):
        print(f"      {v:4}  {k}")
print(f"\n  합계 {total}개")
PY
echo
echo "✅ 완료. docs/오픈소스SW_목록.md 의 수치가 위와 맞는지 확인하세요."
