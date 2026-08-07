#!/usr/bin/env python3
"""
검색 품질 평가 — Top-1 / Top-3 Accuracy, MRR (로드맵 2주차 A 산출물)

정답셋 CSV(chunk_id,code_block_id)를 읽어, CodeSearchService와 **동일한 SQL**로
각 chunk의 코드 후보 순위를 뽑고 지표를 계산합니다.
백엔드를 띄우지 않아도 되고, psycopg2 같은 추가 패키지도 필요 없습니다
(docker exec psql만 사용).

사용법:
    python3 scripts/eval_retrieval.py database/eval_set_demo.csv
    python3 scripts/eval_retrieval.py my_eval.csv --k 5 --container codeatlas-postgres

정답셋 CSV 형식 (헤더 필수, # 로 시작하는 줄은 주석):
    chunk_id,code_block_id
    101,501
    102,502
"""
import argparse
import csv
import subprocess
import sys

# CodeSearchService.SEARCH_SQL 과 동일한 정렬 기준 (pgvector cosine distance)
RANK_SQL = """
SELECT cb.id
FROM code_blocks cb
CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = {chunk_id}) pc
WHERE cb.embedding IS NOT NULL AND pc.embedding IS NOT NULL
ORDER BY cb.embedding <=> pc.embedding
LIMIT {k}
"""


def psql(container, db, user, sql):
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-U", user, "-d", db, "-tAc", sql],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"psql 실행 실패:\n{result.stderr}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def load_eval_set(path):
    pairs = []
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
        for row in csv.DictReader(rows):
            pairs.append((int(row["chunk_id"]), int(row["code_block_id"])))
    if not pairs:
        sys.exit(f"정답셋이 비어 있습니다: {path}")
    return pairs


def main():
    parser = argparse.ArgumentParser(description="CodeAtlas 검색 품질 평가")
    parser.add_argument("eval_set", help="정답셋 CSV 경로 (chunk_id,code_block_id)")
    parser.add_argument("--k", type=int, default=10, help="순위를 확인할 최대 개수 (기본 10)")
    parser.add_argument("--container", default="codeatlas-postgres")
    parser.add_argument("--db", default="codeatlas")
    parser.add_argument("--user", default="codeatlas")
    args = parser.parse_args()

    pairs = load_eval_set(args.eval_set)

    top1 = top3 = 0
    reciprocal_ranks = []
    misses = []

    for chunk_id, expected_block in pairs:
        ranked = [int(x) for x in psql(args.container, args.db, args.user,
                                       RANK_SQL.format(chunk_id=chunk_id, k=args.k))]
        if not ranked:
            misses.append((chunk_id, expected_block, None))
            reciprocal_ranks.append(0.0)
            continue

        rank = ranked.index(expected_block) + 1 if expected_block in ranked else None
        if rank == 1:
            top1 += 1
        if rank is not None and rank <= 3:
            top3 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        if rank != 1:
            misses.append((chunk_id, expected_block, ranked[0]))

    n = len(pairs)
    print(f"정답셋 {n}쌍 (top-{args.k}까지 확인)")
    print(f"  Top-1 Accuracy : {top1}/{n}  ({top1 / n:.1%})")
    print(f"  Top-3 Accuracy : {top3}/{n}  ({top3 / n:.1%})")
    print(f"  MRR            : {sum(reciprocal_ranks) / n:.4f}")

    if misses:
        print(f"\nTop-1 실패 {len(misses)}건 (chunk_id: 정답 block → 실제 1위):")
        for chunk_id, expected, actual in misses:
            print(f"  {chunk_id}: {expected} → {actual if actual else '결과 없음'}")


if __name__ == "__main__":
    main()
