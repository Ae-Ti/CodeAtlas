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

    # 한 chunk 에 대안 정답이 여러 개인 경우 (ingest.py --eval-csv --eval-all 로 생성)
    python3 scripts/eval_retrieval.py database/eval_set_attention.csv --multi-gold

    # 임시 demo seed 를 코퍼스에서 빼고 대상 저장소만으로 측정
    python3 scripts/eval_retrieval.py database/eval_set_attention.csv \
        --only-repo https://github.com/jadore801120/attention-is-all-you-need-pytorch

정답셋 CSV 형식 (헤더 필수, # 로 시작하는 줄은 주석):
    chunk_id,code_block_id
    101,501
    102,502

같은 chunk_id 가 여러 행이면 **첫 행이 Top-1 정답**, 나머지는 대안 정답입니다.
기본 채점은 첫 행만 보고, --multi-gold 를 줘야 나머지를 인정합니다.
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
  {repo_filter}
ORDER BY cb.embedding <=> pc.embedding
LIMIT {k}
"""


def repo_filter_sql(only, exclude):
    """
    후보 코드 블록을 저장소 단위로 걸러냅니다.

    seed_demo.sql 의 데모 저장소가 대상 논문과 **같은 논문**(1706.03762)을 구현하고
    있어서, 정답으로 표기하지 않은 동등 구현이 1위를 가져가 정답이 오답으로 처리됩니다.
    임시 데이터를 코퍼스에서 빼고 재려면 이 옵션을 쓰세요.
    """
    clauses = []
    if only:
        urls = ", ".join(sql_str(u) for u in only)
        clauses.append(f"AND cb.repository_id IN "
                       f"(SELECT id FROM repositories WHERE github_url IN ({urls}))")
    if exclude:
        urls = ", ".join(sql_str(u) for u in exclude)
        clauses.append(f"AND cb.repository_id NOT IN "
                       f"(SELECT id FROM repositories WHERE github_url IN ({urls}))")
    return "\n  ".join(clauses)


def sql_str(value):
    return "'" + str(value).replace("'", "''") + "'"


def psql(container, db, user, sql):
    result = subprocess.run(
        ["docker", "exec", container, "psql", "-U", user, "-d", db, "-tAc", sql],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"psql 실행 실패:\n{result.stderr}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def load_eval_set(path):
    """
    정답셋을 {chunk_id: [code_block_id, ...]} 로 읽습니다 (파일 순서 유지).

    한 chunk 에 여러 행이 있으면 **첫 행이 Top-1 정답**이고 나머지는 대안 정답입니다
    (ingest.py 의 mappedCode 순서 그대로). 기본 채점은 첫 행만 정답으로 보고,
    --multi-gold 를 주면 나머지도 정답으로 인정합니다.
    """
    golds = {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in f if not r.lstrip().startswith("#")]
        for row in csv.DictReader(rows):
            chunk_id, block_id = int(row["chunk_id"]), int(row["code_block_id"])
            golds.setdefault(chunk_id, [])
            if block_id not in golds[chunk_id]:
                golds[chunk_id].append(block_id)
    if not golds:
        sys.exit(f"정답셋이 비어 있습니다: {path}")
    return golds


def main():
    parser = argparse.ArgumentParser(description="CodeAtlas 검색 품질 평가")
    parser.add_argument("eval_set", help="정답셋 CSV 경로 (chunk_id,code_block_id)")
    parser.add_argument("--k", type=int, default=10, help="순위를 확인할 최대 개수 (기본 10)")
    parser.add_argument("--multi-gold", action="store_true",
                        help="한 chunk 에 여러 정답이 있으면 그중 가장 높은 순위를 인정 "
                             "(기본: 첫 행만 정답)")
    parser.add_argument("--only-repo", action="append", metavar="URL", default=[],
                        help="이 저장소의 코드 블록만 후보로 삼음 (반복 지정 가능)")
    parser.add_argument("--exclude-repo", action="append", metavar="URL", default=[],
                        help="이 저장소의 코드 블록을 후보에서 제외 (반복 지정 가능)")
    parser.add_argument("--container", default="codeatlas-postgres")
    parser.add_argument("--db", default="codeatlas")
    parser.add_argument("--user", default="codeatlas")
    args = parser.parse_args()

    golds = load_eval_set(args.eval_set)
    repo_filter = repo_filter_sql(args.only_repo, args.exclude_repo)

    top1 = top3 = 0
    reciprocal_ranks = []
    misses = []

    for chunk_id, block_ids in golds.items():
        # 기본은 첫 행(=mappedCode[0])만 정답. --multi-gold 면 전부 인정하고 최고 순위를 씀.
        accepted = block_ids if args.multi_gold else block_ids[:1]

        ranked = [int(x) for x in psql(args.container, args.db, args.user,
                                       RANK_SQL.format(chunk_id=chunk_id, k=args.k,
                                                       repo_filter=repo_filter))]
        found = [ranked.index(b) + 1 for b in accepted if b in ranked]
        rank = min(found) if found else None

        if rank == 1:
            top1 += 1
        if rank is not None and rank <= 3:
            top3 += 1
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        if rank != 1:
            misses.append((chunk_id, accepted, ranked[0] if ranked else None, rank))

    n = len(golds)
    mode = "다중 정답(최고 순위)" if args.multi_gold else "단일 정답(첫 행)"
    scope = []
    if args.only_repo:
        scope.append(f"only={len(args.only_repo)}개 저장소")
    if args.exclude_repo:
        scope.append(f"exclude={len(args.exclude_repo)}개 저장소")
    total_golds = sum(len(v) for v in golds.values())

    print(f"정답셋 chunk {n}개 / 매핑 {total_golds}건 (top-{args.k}까지 확인)")
    print(f"  채점 기준 : {mode}" + (f" | 후보 범위: {', '.join(scope)}" if scope else ""))
    print(f"  Top-1 Accuracy : {top1}/{n}  ({top1 / n:.1%})")
    print(f"  Top-3 Accuracy : {top3}/{n}  ({top3 / n:.1%})")
    print(f"  MRR            : {sum(reciprocal_ranks) / n:.4f}")

    if misses:
        print(f"\nTop-1 실패 {len(misses)}건 (chunk_id: 정답 → 실제 1위, 정답 순위):")
        for chunk_id, accepted, actual, rank in misses:
            gold = "/".join(str(b) for b in accepted)
            top = actual if actual else "결과 없음"
            where = f"{rank}위" if rank else f"top-{args.k} 밖"
            print(f"  {chunk_id}: {gold} → {top}  (정답 {where})")


if __name__ == "__main__":
    main()
