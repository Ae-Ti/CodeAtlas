#!/usr/bin/env python3
"""논문 arXiv ID → 구현 저장소 후보 추천 (확장기능 §1.2 ①②단계).

수동 큐레이션의 병목은 승인이 아니라 **소싱**입니다(확장기능 §1.3).
이 스크립트가 후보를 모아 점수순으로 세우면, 사람은 목록만 보고 고르면 됩니다.

    소싱                          추천                         승인(사람)
    ────────────────────          ──────────────────           ──────────
    PWC 아카이브 (CC-BY-SA-4.0)   신뢰도 점수로 정렬            --approve 로
      논문↔저장소 링크       ──▶    · PWC official/mentioned  ──▶  repositories
    GitHub Search API              · star 수                       스텁 생성
      아카이브 이후 논문           · 라이선스 유무(하드 필터)        │
                                   · 언어 Python                    ▼
                                   · 제목·초록 ↔ 저장소 유사도   ingest.py

사용법:

    python3 scripts/suggest_repos.py 1706.03762
    python3 scripts/suggest_repos.py 2010.11929 --top 10 --enrich 40
    python3 scripts/suggest_repos.py 1706.03762 --approve 1 --out /tmp/repo.json
    python3 scripts/suggest_repos.py --missing            # 카탈로그에서 저장소 없는 논문 찾기

표준 라이브러리만 씁니다. GitHub 토큰은 `git credential fill` 에서 읽거나
`GITHUB_TOKEN` 으로 줍니다 — 없으면 core API 가 시간당 60회로 제한돼
`--enrich` 를 10 이하로 낮춰야 합니다.

## 왜 하드 필터가 라이선스인가

LICENSE 없는 저장소는 모든 권리 유보 상태라 코드 원문을 ingest JSON 에 넣는 순간
재배포 위반입니다(CONTRIBUTING §7). 점수를 깎는 게 아니라 후보에서 뺍니다 —
승인 화면에 올라오면 사람이 실수로 고를 수 있기 때문입니다.
"""
import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HF_FILTER = 'https://datasets-server.huggingface.co/filter'
PWC_DATASET = 'pwc-archive/links-between-paper-and-code'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PWC_INDEX = os.path.join(ROOT, 'database', 'pwc', 'links.tsv.gz')
GH_API = 'https://api.github.com'
UA = 'CodeAtlas-suggest-repos'

#: 논문 제목·초록과 겹쳐도 변별력이 없는 낱말
STOP = set('the a an of and or to in for with on is are be we our this that as by at from '
           'it its can will using use used which not have has more than then also such each '
           'other paper code official implementation pytorch tensorflow model models'.split())

#: 저장소 이름에 이게 들어가면 구현이 아니라 모음집·강의자료일 확률이 높습니다.
JUNK_HINT = re.compile(r'awesome|tutorial|course|study|lecture|homework|assignment|'
                       r'paper-?list|reading|note[s]?$|blog|test|demo|playground|template',
                       re.I)


# ── 공통 ────────────────────────────────────────────────────────
def tokens(text):
    out = []
    for t in re.split(r'[^A-Za-z0-9]+', text or ''):
        t = t.lower()
        if len(t) >= 3 and t not in STOP:
            out.append(t)
    return set(out)


def get_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def github_token():
    tok = os.environ.get('GITHUB_TOKEN')
    if tok:
        return tok
    try:
        out = subprocess.run(['git', 'credential', 'fill'],
                             input='protocol=https\nhost=github.com\n\n',
                             capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines():
            if line.startswith('password='):
                return line.split('=', 1)[1]
    except Exception:
        pass
    return None


def gh(path, token, params=None):
    url = f'{GH_API}{path}'
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        return get_json(url, headers)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            sys.exit(f'GitHub API 쿼터 소진({e.code}). --enrich 를 줄이거나 GITHUB_TOKEN 을 주세요.')
        return None
    except Exception:
        return None


# ── ① 소싱 ──────────────────────────────────────────────────────
def normalize_repo(url):
    """tree/blob 하위 경로를 저장소 루트로 접습니다 (PWC 에 파일 링크가 섞여 있음)."""
    m = re.match(r'https?://github\.com/([^/]+)/([^/#?]+)', url or '')
    if not m:
        return None
    owner, name = m.group(1), m.group(2).removesuffix('.git')
    return f'https://github.com/{owner}/{name}'


def from_pwc_index(arxiv_id, path=PWC_INDEX):
    """저장소에 커밋된 색인에서 읽습니다 (기본 경로).

    datasets-server 는 작업 중 실제로 500 을 냈습니다. 심사 시점에 외부 서비스가
    살아 있어야만 도는 기능이면 제10조① 재현성을 만족하지 못하므로, 색인을 넣어 두고
    이쪽을 기본으로 씁니다. 색인 갱신은 scripts/build_pwc_index.py.
    """
    if not os.path.exists(path):
        return None
    key = arxiv_id + '\t'
    rows = []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            if line.startswith(key):
                _, slug, flags = line.rstrip('\n').split('\t')
                rows.append({'repo_url': f'https://github.com/{slug}',
                             'is_official': 'O' in flags,
                             'mentioned_in_paper': 'P' in flags,
                             'mentioned_in_github': 'G' in flags})
    return rows


def from_pwc_api(arxiv_id, page_size=100, max_rows=1000):
    """색인이 없을 때만 쓰는 보조 경로 — HuggingFace datasets-server 질의."""
    rows, offset, total = [], 0, 0
    while offset < max_rows:
        q = urllib.parse.urlencode({
            'dataset': PWC_DATASET, 'config': 'default', 'split': 'train',
            'where': f'"paper_arxiv_id"=\'{arxiv_id}\'',
            'offset': offset, 'limit': page_size})
        try:
            data = get_json(f'{HF_FILTER}?{q}', timeout=60)
        except Exception as e:
            print(f'  ⚠️  PWC datasets-server 질의 실패 ({e})', file=sys.stderr)
            break
        got = data.get('rows') or []
        rows += [r['row'] for r in got]
        total = data.get('num_rows_total', 0)
        offset += page_size
        if offset >= total or not got:
            break
    return rows


def from_github_search(paper_title, token, limit=20):
    """아카이브에 없는 논문용 보완 경로. search API 는 분당 30회라 1회만 씁니다."""
    q = ' '.join(list(tokens(paper_title))[:6]) + ' in:name,description,readme'
    data = gh('/search/repositories', token,
              {'q': q, 'sort': 'stars', 'order': 'desc', 'per_page': limit})
    return (data or {}).get('items', []) or []


# ── ② 추천 ──────────────────────────────────────────────────────
def prefilter(cands, paper_tokens, keep):
    """GitHub 을 부르기 전에 싼 신호로만 추려냅니다.

    논문 1편에 PWC 링크가 수백 개 달립니다(Attention 은 595개). 전부 enrich 하면
    core API 5000/시간을 몇 편만에 씁니다. 그래서 여기서 먼저 자릅니다.
    """
    scored = []
    for c in cands:
        owner, name = c['repo'].split('/')[-2:]
        t = tokens(name) | tokens(owner)
        s = 3.0 * len(t & paper_tokens) / max(1, len(t))
        s += 2.0 if c.get('is_official') else 0.0
        s += 1.0 if c.get('mentioned_in_paper') else 0.0
        s += 0.5 if c.get('mentioned_in_github') else 0.0
        s -= 2.0 if JUNK_HINT.search(name) else 0.0
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:keep]]


def enrich(cand, token):
    """star·라이선스·언어·설명을 채웁니다. 저장소당 core API 1회."""
    owner, name = cand['repo'].split('/')[-2:]
    d = gh(f'/repos/{owner}/{name}', token)
    if not d:
        cand['gone'] = True
        return cand
    # 라이선스는 3상태입니다 — 이 구분이 없으면 pjreddie/darknet(star 26k, 우리 카탈로그에
    # 실제로 들어 있는 저장소)이 조용히 후보에서 사라집니다. GitHub 은 비표준 라이선스를
    # spdx_id=NOASSERTION 으로 돌려주는데, 그건 '없음'이 아니라 '자동 판별 실패'입니다
    # (CONTRIBUTING §7 — spdx_id 를 믿지 말고 원문을 볼 것).
    lic_obj = d.get('license') or {}
    spdx = lic_obj.get('spdx_id')
    if not lic_obj:
        lic, lic_state = None, 'none'            # LICENSE 파일 자체가 없음 → 모든 권리 유보
    elif spdx in (None, 'NOASSERTION'):
        lic, lic_state = lic_obj.get('name') or 'Other', 'unknown'   # 파일은 있으나 비표준
    else:
        lic, lic_state = spdx, 'ok'
    cand.update({
        'stars': d.get('stargazers_count', 0),
        'language': d.get('language'),
        'license': lic,
        'license_state': lic_state,
        'description': d.get('description') or '',
        'archived': d.get('archived', False),
        'default_branch': d.get('default_branch'),
        'owner': owner, 'name': name,
    })
    return cand


def score(cand, paper_tokens):
    """신뢰도 점수 — 확장기능 §1.2 의 네 축을 그대로 씁니다."""
    s, why = 0.0, []
    if cand.get('is_official'):
        s += 4.0; why.append('PWC official')
    if cand.get('mentioned_in_paper'):
        s += 2.0; why.append('논문이 언급')
    if cand.get('mentioned_in_github'):
        s += 0.5; why.append('README 가 논문 언급')

    stars = cand.get('stars', 0)
    # star 는 로그로 — 4만개와 2만개의 차이보다 100개와 0개의 차이가 큽니다.
    import math
    s += min(3.0, math.log10(stars + 1))
    why.append(f'star {stars:,}')

    if cand.get('language') == 'Python':
        s += 1.0; why.append('Python')
    elif cand.get('language'):
        s -= 0.5; why.append(cand['language'])

    text = f"{cand.get('name','')} {cand.get('owner','')} {cand.get('description','')}"
    overlap = len(tokens(text) & paper_tokens)
    s += min(2.0, 0.5 * overlap)
    if overlap:
        why.append(f'제목·초록 겹침 {overlap}낱말')

    if cand.get('license_state') == 'unknown':
        s -= 0.5; why.append('라이선스 비표준 — 원문 확인 필요')
    if cand.get('archived'):
        s -= 1.0; why.append('archived')
    if JUNK_HINT.search(cand.get('name', '')):
        s -= 2.0; why.append('모음집/학습용으로 보임')

    cand['score'] = round(s, 2)
    cand['why'] = why
    return cand


# ── 카탈로그 조회 ────────────────────────────────────────────────
def psql(sql, container='codeatlas-postgres', db='codeatlas', user='codeatlas'):
    out = subprocess.run(['docker', 'exec', container, 'psql', '-U', user, '-d', db, '-tAc', sql],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return [l for l in out.stdout.splitlines() if l.strip()]


def find_missing():
    rows = psql("""SELECT p.arxiv_id || '|' || p.title FROM papers p
                   WHERE NOT EXISTS (SELECT 1 FROM paper_repositories r WHERE r.paper_id = p.id)
                   ORDER BY p.id""")
    if rows is None:
        sys.exit('DB 조회 실패 — 컨테이너가 떠 있는지 확인하세요 (docker compose up -d)')
    return [r.split('|', 1) for r in rows]


def paper_meta(arxiv_id):
    """제목·초록·저자·발행일 — 카탈로그에 있으면 DB, 없으면 arXiv API.

    초록·저자를 빈 값으로 두면 안 됩니다. ingest.py 는 arxivId 로 upsert 하므로
    이미 적재된 논문이면 기존 초록을 NULL, 저자를 [] 로 덮어씁니다
    (ingest.py --dry-run 이 실제로 이 경고를 냅니다).
    """
    rows = psql("SELECT title || E'\\x01' || coalesce(abstract,'') FROM papers "
                f"WHERE arxiv_id = '{arxiv_id}'")
    if rows:
        title, _, abstract = rows[0].partition('\x01')
        return {'title': title, 'abstract': abstract, 'authors': [], 'published': None,
                'in_catalog': True}
    meta = {'title': '', 'abstract': '', 'authors': [], 'published': None, 'in_catalog': False}
    try:
        req = urllib.request.Request(
            f'http://export.arxiv.org/api/query?id_list={arxiv_id}', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            xml = r.read().decode('utf-8', 'replace')
        entry = re.search(r'<entry>(.*?)</entry>', xml, re.S)
        body = entry.group(1) if entry else ''
        norm = lambda s: re.sub(r'\s+', ' ', s).strip() if s else ''
        t = re.search(r'<title>(.*?)</title>', body, re.S)
        a = re.search(r'<summary>(.*?)</summary>', body, re.S)
        pub = re.search(r'<published>(\d{4}-\d{2}-\d{2})', body)
        meta['title'] = norm(t.group(1) if t else '')
        meta['abstract'] = norm(a.group(1) if a else '')
        meta['authors'] = [norm(x) for x in re.findall(r'<author>\s*<name>(.*?)</name>', body, re.S)]
        meta['published'] = pub.group(1) if pub else None
    except Exception as e:
        print(f'  ⚠️  arXiv 메타데이터 조회 실패 ({e}) — 초록·저자가 빈 채로 나갑니다', file=sys.stderr)
    return meta


# ── 출력 ────────────────────────────────────────────────────────
def print_table(cands, top):
    print(f'\n{"#":>2}  {"점수":>5}  {"star":>7}  {"라이선스":<12} {"언어":<10} 저장소')
    print('─' * 108)
    for i, c in enumerate(cands[:top], 1):
        print(f'{i:>2}  {c["score"]:>5}  {c.get("stars",0):>7,}  '
              f'{(("⚠ " if c.get("license_state")=="unknown" else "") + (c.get("license") or "-"))[:12]:<12} '
              f'{(c.get("language") or "-"):<10} '
              f'{c["owner"]}/{c["name"]}')
        print(f'    └ {" · ".join(c["why"])}')


def approval_stub(cand, arxiv_id, meta):
    """승인된 후보를 ingest.py 가 받는 모양으로 내보냅니다.

    codeBlocks 는 비워 둡니다 — AST 파싱은 별도 단계이고, 여기서 채우면
    '사람이 승인한 것'과 '기계가 뽑은 것'의 경계가 흐려집니다.
    """
    return {
        '_comment': (f'suggest_repos.py 추천 → 사람 승인. 점수 {cand["score"]} '
                     f'({" · ".join(cand["why"])}). codeBlocks 는 AST 파싱 단계에서 채웁니다.'
                     + (' ⚠️ 라이선스가 비표준이라 licenseName 을 비워 두었습니다 — '
                        'LICENSE 원문을 읽고 직접 채우세요(CONTRIBUTING §7).'
                        if cand.get('license_state') == 'unknown' else '')),
        'papers': [{
            'arxivId': arxiv_id, 'title': meta['title'],
            # 초록·저자를 비워 두면 재적재 시 기존 값을 덮어씁니다 — arXiv 에서 받아 채웁니다.
            'abstract': meta['abstract'] or None,
            'authors': meta['authors'],
            'publishedDate': meta['published'],
            'pdfUrl': f'https://arxiv.org/pdf/{arxiv_id}',
            'chunks': [],
            'repositories': [{
                'githubUrl': cand['repo'],
                'repositoryName': cand['name'],
                'ownerName': cand['owner'],
                'defaultBranch': cand.get('default_branch') or 'main',
                'licenseName': (None if cand.get('license_state') == 'unknown'
                                else cand.get('license')),
                'primaryLanguage': cand.get('language'),
                'starCount': cand.get('stars', 0),
                'relationType': 'OFFICIAL' if cand.get('is_official') else 'COMMUNITY',
                'isPrimary': True,
                'codeBlocks': [],
            }],
        }],
    }


def main():
    ap = argparse.ArgumentParser(description='논문 → 구현 저장소 후보 추천')
    ap.add_argument('arxiv_id', nargs='?', help='예: 1706.03762')
    ap.add_argument('--missing', action='store_true', help='카탈로그에서 저장소가 없는 논문 목록')
    ap.add_argument('--top', type=int, default=10, help='출력할 후보 수 (기본 10)')
    ap.add_argument('--enrich', type=int, default=25,
                    help='GitHub API 로 조회할 상위 후보 수 (기본 25). 저장소당 1회 호출')
    ap.add_argument('--approve', type=int, metavar='N', help='N번 후보를 승인해 ingest 스텁 생성')
    ap.add_argument('--out', metavar='PATH', help='--approve 결과를 쓸 경로 (기본 stdout)')
    ap.add_argument('--pwc-index', default=PWC_INDEX, help='PWC 링크 색인 경로')
    ap.add_argument('--allow-unlicensed', action='store_true',
                    help='라이선스 없는 저장소도 후보에 남김 (기본은 제외 — CONTRIBUTING §7)')
    args = ap.parse_args()

    if args.missing:
        rows = find_missing()
        if not rows:
            print('저장소가 연결되지 않은 논문이 없습니다.')
            return
        print(f'저장소 미연결 논문 {len(rows)}편:')
        for aid, title in rows:
            print(f'  {aid}  {title[:70]}')
        return

    if not args.arxiv_id:
        ap.error('arxiv_id 를 주거나 --missing 을 쓰세요')

    token = github_token()
    meta = paper_meta(args.arxiv_id)
    title, abstract = meta['title'], meta['abstract']
    ptok = tokens(title) | tokens(abstract)
    print(f'▶ {args.arxiv_id}  {title[:72]}')
    print(f'  GitHub 토큰: {"있음" if token else "없음 — core API 60회/시간 제한"}')

    # ① 소싱 — 커밋된 색인이 기본, 없으면 datasets-server
    rows = from_pwc_index(args.arxiv_id, args.pwc_index)
    src = '색인'
    if rows is None:
        print(f'  색인 없음({args.pwc_index}) — datasets-server 로 질의합니다')
        rows, src = from_pwc_api(args.arxiv_id), 'datasets-server'
    total = len(rows)
    seen, cands = set(), []
    for r in rows:
        repo = normalize_repo(r.get('repo_url'))
        if not repo or repo in seen:
            continue
        seen.add(repo)
        cands.append({'repo': repo, 'is_official': bool(r.get('is_official')),
                      'mentioned_in_paper': bool(r.get('mentioned_in_paper')),
                      'mentioned_in_github': bool(r.get('mentioned_in_github')),
                      'source': 'PWC'})
    print(f'  PWC 아카이브({src}): 링크 {total}건 → 저장소 {len(cands)}곳'
          f' · official 표시 {sum(1 for c in cands if c["is_official"])}건')

    if len(cands) < 5 and title:
        for it in from_github_search(title, token):
            repo = normalize_repo(it.get('html_url'))
            if repo and repo not in seen:
                seen.add(repo)
                cands.append({'repo': repo, 'is_official': False, 'mentioned_in_paper': False,
                              'mentioned_in_github': False, 'source': 'GitHub Search'})
        print(f'  GitHub Search 보완 → 후보 {len(cands)}곳')

    if not cands:
        sys.exit('후보를 찾지 못했습니다.')

    # ② 추천 — 싼 신호로 먼저 자르고, 살아남은 것만 API 로 채웁니다
    short = prefilter(cands, ptok, args.enrich)
    print(f'  사전 선별 {len(cands)} → {len(short)}곳, GitHub 조회 중…')
    short = [score(enrich(c, token), ptok) for c in short]

    gone = [c for c in short if c.get('gone')]
    alive = [c for c in short if not c.get('gone')]
    nolic = [c for c in alive if c.get('license_state') == 'none']
    unknown = [c for c in alive if c.get('license_state') == 'unknown']
    if not args.allow_unlicensed:
        alive = [c for c in alive if c.get('license_state') != 'none']
    alive.sort(key=lambda c: -c['score'])

    print(f'  삭제·비공개 {len(gone)}곳 제외 / LICENSE 없음 {len(nolic)}곳 '
          f'{"표시함" if args.allow_unlicensed else "제외"} → 후보 {len(alive)}곳')
    if unknown:
        print(f'  ⚠️  비표준 라이선스 {len(unknown)}곳은 남겨 두었습니다 — 승인 전 원문 확인 필요')

    # 신호가 가장 강한 후보가 라이선스 때문에 빠졌다면 반드시 알립니다.
    # 조용히 빼면 사람은 "왜 공식 저장소가 없지?" 를 모른 채 2위를 고르게 됩니다.
    # (실제로 DDPM 2006.11239 의 공식 구현 hojonathanho/diffusion 이 이 경우입니다 —
    #  PWC official + 논문 언급 + star 5,298 인데 LICENSE 파일이 없습니다.)
    if not args.allow_unlicensed:
        notable = [c for c in nolic
                   if c.get('is_official') or c.get('mentioned_in_paper') or c.get('stars', 0) >= 1000]
        for c in sorted(notable, key=lambda x: -x.get('stars', 0)):
            tags = ' · '.join(filter(None, [
                'PWC official' if c.get('is_official') else '',
                '논문이 언급' if c.get('mentioned_in_paper') else '',
                f'star {c.get("stars", 0):,}']))
            print(f'  🔴 {c["owner"]}/{c["name"]} 제외됨 — LICENSE 파일 없음 ({tags})')
            print(f'     모든 권리 유보 상태라 코드 원문을 재배포할 수 없습니다(CONTRIBUTING §7).')
            print(f'     저자에게 라이선스 추가를 요청하거나, 라이선스가 있는 재구현을 쓰세요.')
    print_table(alive, args.top)

    if args.approve:
        if not 1 <= args.approve <= len(alive):
            sys.exit(f'--approve 는 1~{len(alive)} 사이여야 합니다')
        chosen = alive[args.approve - 1]
        if meta['in_catalog'] and not meta['authors']:
            print('  ℹ️  카탈로그에 이미 있는 논문이라 초록·저자는 DB 값을 그대로 둡니다', file=sys.stderr)
        stub = approval_stub(chosen, args.arxiv_id, meta)
        text = json.dumps(stub, ensure_ascii=False, indent=2) + '\n'
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'\n✅ 승인 {chosen["owner"]}/{chosen["name"]} → {args.out}')
            print(f'   python3 scripts/ingest.py {args.out} --dry-run')
        else:
            print(text)


if __name__ == '__main__':
    main()
