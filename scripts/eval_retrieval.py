#!/usr/bin/env python3
"""
검색 품질 평가 — Top-1 / Top-3 Accuracy, MRR (로드맵 2주차 A 산출물)

정답셋 CSV(chunk_id,code_block_id)를 읽어, CodeSearchService와 **동일한 SQL**로
각 chunk의 코드 후보 순위를 뽑고 지표를 계산합니다.
백엔드를 띄우지 않아도 되고, psycopg2 같은 추가 패키지도 필요 없습니다
(docker exec psql만 사용).

⚠️ 랭킹 기준에 대하여

  기본(--scorer 미지정)은 CodeSearchService.SEARCH_SQL 과 **동일한 순수 pgvector
  코사인 정렬**입니다. 이 도구의 수치가 실제 서비스 순위와 같다는 보장은 여기서 나옵니다.

  --scorer lexical|hybrid 는 **진단 전용**입니다. 어휘 점수 공식은 자리표시자이며
  CodeSearchService 에 구현된 것이 아닙니다. 즉 이 모드의 수치는 서비스 동작이
  아니라 "임베딩이 어휘가 하는 일 이상을 하고 있는가"를 보기 위한 참고값입니다.
  보고서에 올릴 하이브리드 수치는 CodeSearchService 에 공식이 확정된 뒤,
  그 공식을 이 파일에 미러링하고 나서 내야 합니다.

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
import re
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


# ── 어휘 점수 (진단 전용 자리표시자) ────────────────────────────
# CodeSearchService 에는 없는 공식입니다. 최종 공식은 A가 확정합니다.
#   식별자 토큰화: camelCase / snake_case 분해 → 소문자 → 길이 2 이하 버림
#   score = |chunk 토큰 ∩ 코드 토큰| / |chunk 토큰|   (Jaccard 아님 — 질의 기준 recall)
TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+")
CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize(text):
    tokens = set()
    for raw in TOKEN_SPLIT.split(text or ""):
        for part in CAMEL_SPLIT.split(raw):
            part = part.lower()
            if len(part) > 2:
                tokens.add(part)
    return tokens


def lexical_score(chunk_tokens, code_tokens, form="recall"):
    """
    form 은 A가 CodeSearchService 공식을 정할 때 고를 수 있게 세 가지를 둡니다.

      recall  |∩|/|q|        질의 기준 recall (A가 지정한 자리표시자)
      jaccard |∩|/|q∪d|      문서 크기로 정규화
      dice    2|∩|/(|q|+|d|) 문서 크기로 정규화

    recall 은 **길이 보정이 없어 큰 블록이 구조적으로 유리합니다.** 토큰이 많을수록
    질의 토큰을 더 많이 덮기 때문입니다. 실측에서 9개 질의 중 7개가 최대 블록(97토큰)을
    1위로 뽑았습니다. BM25 의 길이 정규화가 해결하려는 것이 정확히 이 문제입니다.
    """
    inter = len(chunk_tokens & code_tokens)
    if form == "jaccard":
        union = len(chunk_tokens | code_tokens)
        return inter / union if union else 0.0
    if form == "dice":
        total = len(chunk_tokens) + len(code_tokens)
        return 2 * inter / total if total else 0.0
    return inter / len(chunk_tokens) if chunk_tokens else 0.0


# 후보 전체와 코사인 거리를 함께 받습니다 (파이썬에서 재정렬하려면 LIMIT 을 걸면 안 됩니다).
CANDIDATE_SQL = """
SELECT cb.id || '|' || (cb.embedding <=> pc.embedding)
FROM code_blocks cb
CROSS JOIN (SELECT embedding FROM paper_chunks WHERE id = {chunk_id}) pc
WHERE cb.embedding IS NOT NULL AND pc.embedding IS NOT NULL
  {repo_filter}
ORDER BY cb.embedding <=> pc.embedding
"""

# 토큰화 대상은 EmbeddingBackfillRunner 가 임베딩에 넣는 필드와 같게 맞춥니다.
# 코드·단락 본문에 줄바꿈이 있어 행 단위 파싱이 깨지므로 SQL 에서 공백으로 바꿉니다
# (토큰화가 어차피 비영숫자로 자르므로 손실이 없습니다).
CODE_TEXT_SQL = """
SELECT cb.id || E'\\t' || regexp_replace(
         coalesce(cb.file_path,'') || ' ' || coalesce(cb.parent_symbol_name,'') || ' '
         || coalesce(cb.symbol_name,'') || ' ' || coalesce(cb.code_content,''),
         E'[\\n\\r]+', ' ', 'g')
FROM code_blocks cb
WHERE cb.embedding IS NOT NULL
  {repo_filter}
"""

CHUNK_TEXT_SQL = """
SELECT pc.id || E'\\t' || regexp_replace(
         coalesce(pc.section_title,'') || ' ' || coalesce(pc.content,''),
         E'[\\n\\r]+', ' ', 'g')
FROM paper_chunks pc WHERE pc.id IN ({ids})
"""


def load_tokens(container, db, user, sql):
    """'id<TAB>텍스트' 행을 {id: 토큰집합} 으로."""
    out = {}
    for line in psql(container, db, user, sql):
        if "\t" not in line:
            continue
        key, text = line.split("\t", 1)
        out[int(key)] = tokenize(text)
    return out


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
    parser.add_argument("--scorer", choices=["vector", "lexical", "hybrid"], default="vector",
                        help="랭킹 기준. vector(기본)만 CodeSearchService 와 동일합니다. "
                             "lexical/hybrid 는 진단 전용 자리표시자입니다")
    parser.add_argument("--alpha", type=float, default=0.5, metavar="W",
                        help="--scorer hybrid 에서 벡터 가중치 (기본 0.5, 나머지가 어휘)")
    parser.add_argument("--lexical-form", choices=["recall", "jaccard", "dice"], default="recall",
                        help="어휘 점수 형태. recall(기본)은 길이 보정이 없어 큰 블록에 유리합니다")
    parser.add_argument("--container", default="codeatlas-postgres")
    parser.add_argument("--db", default="codeatlas")
    parser.add_argument("--user", default="codeatlas")
    args = parser.parse_args()

    golds = load_eval_set(args.eval_set)
    repo_filter = repo_filter_sql(args.only_repo, args.exclude_repo)

    code_tokens = chunk_tokens = {}
    if args.scorer != "vector":
        code_tokens = load_tokens(args.container, args.db, args.user,
                                  CODE_TEXT_SQL.format(repo_filter=repo_filter))
        chunk_tokens = load_tokens(args.container, args.db, args.user,
                                   CHUNK_TEXT_SQL.format(
                                       ids=", ".join(str(c) for c in golds)))

    def rank_for(chunk_id):
        if args.scorer == "vector":
            # CodeSearchService.SEARCH_SQL 과 동일 경로 — 정렬을 DB에 맡깁니다.
            return [int(x) for x in psql(args.container, args.db, args.user,
                                         RANK_SQL.format(chunk_id=chunk_id, k=args.k,
                                                         repo_filter=repo_filter))]
        # 재정렬이 필요하므로 후보 전체와 거리를 받아 파이썬에서 점수를 매깁니다.
        scored = []
        q = chunk_tokens.get(chunk_id, set())
        for line in psql(args.container, args.db, args.user,
                         CANDIDATE_SQL.format(chunk_id=chunk_id, repo_filter=repo_filter)):
            bid, dist = line.split("|")
            bid = int(bid)
            lex = lexical_score(q, code_tokens.get(bid, set()), args.lexical_form)
            if args.scorer == "lexical":
                # 순수 어휘 베이스라인이므로 동점을 벡터로 깨지 않습니다.
                # 벡터로 깨면 "임베딩이 어휘보다 나은가"를 재는데 벡터가 섞여 들어갑니다
                # (실측에서 44.4% 대 33.3% 로 갈렸습니다). id 순서로 결정적으로 처리합니다.
                scored.append((-lex, float(bid), bid))
            else:
                score = args.alpha * (1.0 - float(dist)) + (1.0 - args.alpha) * lex
                # 하이브리드는 이미 벡터가 점수에 있으므로 동점도 벡터로 깹니다.
                scored.append((-score, float(dist), bid))
        scored.sort()
        return [bid for _, _, bid in scored[:args.k]]

    top1 = top3 = 0
    reciprocal_ranks = []
    misses = []

    for chunk_id, block_ids in golds.items():
        # 기본은 첫 행(=mappedCode[0])만 정답. --multi-gold 면 전부 인정하고 최고 순위를 씀.
        accepted = block_ids if args.multi_gold else block_ids[:1]

        ranked = rank_for(chunk_id)
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
    if args.scorer == "vector":
        rank_desc = "vector (CodeSearchService 와 동일)"
    elif args.scorer == "lexical":
        rank_desc = "lexical ⚠️ 진단 전용 — 서비스 랭킹 아님"
    else:
        rank_desc = f"hybrid(α={args.alpha}) ⚠️ 진단 전용 — 서비스 랭킹 아님"
    scope = []
    if args.only_repo:
        scope.append(f"only={len(args.only_repo)}개 저장소")
    if args.exclude_repo:
        scope.append(f"exclude={len(args.exclude_repo)}개 저장소")
    total_golds = sum(len(v) for v in golds.values())

    print(f"정답셋 chunk {n}개 / 매핑 {total_golds}건 (top-{args.k}까지 확인)")
    print(f"  랭킹 기준 : {rank_desc}")
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
