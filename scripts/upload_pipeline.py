#!/usr/bin/env python3
"""arXiv ID + GitHub URL → 카탈로그 적재까지 한 번에 — 업로드 페이지의 백엔드 작업.

    python3 scripts/upload_pipeline.py --arxiv 1505.04597 \
        --github https://github.com/milesial/Pytorch-UNet --work /tmp/upload-1

단계 (각 단계 시작을 stdout 에 `##STAGE <이름> <설명>` 으로 찍는다 — 백엔드가 이 줄로
진행 상황을 화면에 올린다):

  ARXIV_META    export.arxiv.org 에서 제목·초록·저자·발표일
  EPRINT        arxiv.org/e-print 에서 LaTeX 소스 다운로드·압축 해제
  REPO_CLONE    git clone --depth 1 + GitHub API 메타(별·라이선스·언어)
  CODE_BLOCKS   .py 파일을 ast 로 파싱해 리프 심볼(함수·메서드) 단위 code block 추출
  LATEX_SPLIT   latex2chunks.py split — qwen3 가 경계·소제목 제안, 본문은 원문 슬라이스
  INGEST        ingest.py 로 papers / paper_chunks / repositories / code_blocks 적재

마지막에 `##RESULT paperId=<id> chunks=<n> blocks=<n>` 을 찍는다. 임베딩·큐레이션은
백엔드(UploadJobService)가 이어서 수행한다 — 이 스크립트는 embedding 을 쓰지 않는다.

추가 패키지 없음 (stdlib + git + docker exec psql). LaTeX 원문·클론한 저장소는 --work
디렉터리에만 두고 저장소에 커밋하지 않는다 (저작권 — latex2chunks.py 와 같은 원칙).
"""
import argparse
import ast
import gzip
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import latex2chunks  # noqa: E402  (latex_to_text 재사용)

UA = {'User-Agent': 'CodeAtlas-upload/1.0 (+https://github.com/Ae-Ti/CodeAtlas)'}
MAX_BLOCKS = 500           # 거대 저장소 방어 — 큐레이션 후보 검색은 저장소 단위라 이 위로는 품질보다 시간만 는다
MAX_FILE_BYTES = 300_000   # 생성 코드·벤더 파일 방어
SKIP_DIRS = {'.git', 'test', 'tests', 'testing', 'venv', '.venv', 'env', 'node_modules',
             'build', 'dist', 'docs', 'doc', '__pycache__', 'site-packages', 'third_party',
             'vendor', 'examples', 'example', 'notebooks', 'scripts'}


def stage(name, msg=''):
    print(f'##STAGE {name} {msg}'.rstrip(), flush=True)


def log(msg):
    print(f'   {msg}', flush=True)


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ── 1. arXiv 메타 ────────────────────────────────────────────────

def arxiv_meta(arxiv_id):
    xml = fetch(f'http://export.arxiv.org/api/query?id_list={arxiv_id}')
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    root = ET.fromstring(xml)
    entry = root.find('a:entry', ns)
    if entry is None or entry.find('a:title', ns) is None:
        raise SystemExit(f'arXiv 에서 {arxiv_id} 를 찾지 못했습니다')
    title = re.sub(r'\s+', ' ', entry.findtext('a:title', '', ns)).strip()
    if title.lower().startswith('error'):
        raise SystemExit(f'arXiv 오류: {title}')
    summary = re.sub(r'\s+', ' ', entry.findtext('a:summary', '', ns)).strip()
    authors = [a.findtext('a:name', '', ns).strip() for a in entry.findall('a:author', ns)]
    published = (entry.findtext('a:published', '', ns) or '')[:10] or None
    pdf = None
    for link in entry.findall('a:link', ns):
        if link.get('title') == 'pdf':
            pdf = link.get('href')
    return {'arxivId': arxiv_id, 'title': title, 'abstract': summary, 'authors': authors,
            'publishedDate': published, 'pdfUrl': pdf or f'https://arxiv.org/pdf/{arxiv_id}'}


# ── 2. e-print (LaTeX 소스) ───────────────────────────────────────

def download_eprint(arxiv_id, dest):
    os.makedirs(dest, exist_ok=True)
    raw = fetch(f'https://arxiv.org/e-print/{arxiv_id}', timeout=120)
    if raw[:4] == b'%PDF':
        raise SystemExit('이 논문은 arXiv 에 LaTeX 소스가 없습니다 (PDF 만 제공). '
                         '단락을 직접 작성한 ingest JSON 업로드를 이용하세요.')
    # gzip 풀기 → tar 이면 전개, 아니면 단일 .tex
    try:
        data = gzip.decompress(raw)
    except OSError:
        data = raw
    if tarfile.is_tarfile(io.BytesIO(data)):
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            members = [m for m in tf.getmembers()
                       if m.isfile() and not os.path.isabs(m.name) and '..' not in m.name.split('/')]
            tf.extractall(dest, members=members)
    else:
        with open(os.path.join(dest, 'main.tex'), 'wb') as f:
            f.write(data)
    # 메인 .tex 가 하위 디렉터리에 있는 경우 그 디렉터리를 돌려준다
    for root, _dirs, files in os.walk(dest):
        for name in files:
            if name.endswith('.tex'):
                with open(os.path.join(root, name), errors='replace') as f:
                    if '\\documentclass' in f.read():
                        return root
    raise SystemExit('소스 안에서 \\documentclass 가 있는 .tex 를 찾지 못했습니다')


# ── 3. 저장소 ─────────────────────────────────────────────────────

def parse_github(url):
    m = re.match(r'https?://github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?$', url.strip())
    if not m:
        raise SystemExit(f'GitHub 저장소 URL 형식이 아닙니다: {url}')
    return m.group(1), m.group(2)


def clone_repo(url, dest):
    owner, name = parse_github(url)
    try:
        r = subprocess.run(['git', 'clone', '--depth', '1', '--quiet', f'https://github.com/{owner}/{name}.git', dest],
                           capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise SystemExit('git clone 이 10분 안에 끝나지 않았습니다 — 저장소가 지나치게 크거나 네트워크 문제')
    if r.returncode:
        raise SystemExit(f'git clone 실패: {r.stderr.strip()[:300]}')
    commit = subprocess.run(['git', '-C', dest, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(['git', '-C', dest, 'rev-parse', '--abbrev-ref', 'HEAD'],
                            capture_output=True, text=True).stdout.strip() or None
    meta = {'githubUrl': f'https://github.com/{owner}/{name}', 'ownerName': owner, 'repositoryName': name,
            'defaultBranch': branch, 'commitHash': commit, 'starCount': 0,
            'licenseName': None, 'primaryLanguage': None}
    try:
        api = json.loads(fetch(f'https://api.github.com/repos/{owner}/{name}', timeout=30))
        meta['starCount'] = int(api.get('stargazers_count') or 0)
        meta['licenseName'] = (api.get('license') or {}).get('spdx_id')
        meta['primaryLanguage'] = api.get('language')
        meta['defaultBranch'] = api.get('default_branch') or branch
    except Exception as e:  # 비인증 API 한도 등 — 메타 없이도 적재는 된다
        log(f'GitHub API 메타 생략: {e}')
    return meta


def extract_blocks(repo_dir):
    """리프 심볼 기준 — 클래스는 메서드로 대체하고, 메서드가 없는 클래스만 CLASS 로 남긴다.
    (카탈로그 §4 규칙: 같은 파일에서 부모·자식을 동시에 인덱싱하지 않는다)"""
    blocks, skipped = [], 0
    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = sorted(d for d in dirs if d.lower() not in SKIP_DIRS)
        for name in sorted(files):
            if not name.endswith('.py') or name.startswith('test_') or name.endswith('_test.py'):
                continue
            path = os.path.join(root, name)
            if os.path.getsize(path) > MAX_FILE_BYTES:
                skipped += 1
                continue
            rel = os.path.relpath(path, repo_dir)
            try:
                src = open(path, encoding='utf-8', errors='replace').read()
                tree = ast.parse(src)
            except (SyntaxError, ValueError):
                skipped += 1
                continue
            lines = src.splitlines()

            def block(node, symbol_type, parent=None):
                start, end = node.lineno, getattr(node, 'end_lineno', node.lineno)
                return {'filePath': rel, 'symbolType': symbol_type, 'symbolName': node.name,
                        'parentSymbolName': parent, 'programmingLanguage': 'Python',
                        'startLine': start, 'endLine': end,
                        'codeContent': '\n'.join(lines[start - 1:end])}

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    blocks.append(block(node, 'FUNCTION'))
                elif isinstance(node, ast.ClassDef):
                    methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    if methods:
                        blocks.extend(block(m, 'METHOD', node.name) for m in methods)
                    else:
                        blocks.append(block(node, 'CLASS'))
    if len(blocks) > MAX_BLOCKS:
        log(f'code block {len(blocks)}개 → 상한 {MAX_BLOCKS}개로 자름 (파일 경로순)')
        blocks = blocks[:MAX_BLOCKS]
    return blocks, skipped


# ── 4. 단락 분리 → ingest chunks ─────────────────────────────────

def split_chunks(src_dir, blocks, work):
    symbols_path = os.path.join(work, 'symbols.json')
    with open(symbols_path, 'w') as f:
        json.dump([{'name': f"{b['parentSymbolName']}.{b['symbolName']}" if b['parentSymbolName'] else b['symbolName'],
                    'file': b['filePath'], 'type': b['symbolType']} for b in blocks], f)
    out = os.path.join(work, 'auto_chunks.json')
    # LLM 타임아웃 150초 — 실험 경로의 480초와 분리 (근거는 latex2chunks.LLM_TIMEOUT 주석)
    os.environ.setdefault('CODEATLAS_LLM_TIMEOUT', '150')
    run_streaming([sys.executable, os.path.join(HERE, 'latex2chunks.py'), 'split', src_dir,
                   '--symbols-json', symbols_path, '--single-para-no-llm', '--out', out], 'latex2chunks 실패')
    return json.load(open(out))['chunks']


def run_streaming(cmd, fail_msg):
    """하위 스크립트 출력을 줄 단위로 바로 흘려보낸다 — LATEX_SPLIT 처럼 몇 분 걸리는
    단계에서 화면이 멈춘 것처럼 보이지 않게."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    for line in p.stdout:
        log(line.rstrip())
    if p.wait():
        raise SystemExit(fail_msg)


def latex_to_display(content):
    """chunk 본문은 화면·임베딩용으로 평문화한다. 원문 슬라이스(검수 기준)는
    auto_chunks.json 에 그대로 남는다 — 카탈로그의 기존 chunk 들도 평문이다."""
    paras = [latex2chunks.latex_to_text(p) for p in re.split(r'\n\s*\n', content)]
    return '\n\n'.join(p for p in paras if p)


def to_ingest_chunks(auto_chunks):
    out = []
    for c in auto_chunks:
        text = latex_to_display(c['content'])
        if len(text) < 40:  # \label 만 남은 조각 등
            continue
        out.append({'chunkIndex': len(out), 'content': text,
                    'sectionTitle': c.get('sectionTitle'), 'subsectionTitle': c.get('subsectionTitle'),
                    'tokenCount': len(text.split())})
    return out


# ── 5. 적재 ───────────────────────────────────────────────────────

def run_ingest(doc, work):
    path = os.path.join(work, 'ingest.json')
    with open(path, 'w') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    ingest = os.path.join(HERE, 'ingest.py')
    for extra in (['--dry-run'], []):
        run_streaming([sys.executable, ingest, path, *extra], 'ingest 실패' + (' (검증)' if extra else ''))


def paper_id_of(arxiv_id):
    lit = arxiv_id.replace("'", "''")
    rows = latex2chunks.psql_json(f"SELECT json_agg(id) FROM papers WHERE arxiv_id = '{lit}'")
    return rows[0] if rows else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--arxiv', required=True, help='arXiv ID (예: 1505.04597)')
    ap.add_argument('--github', required=True, help='구현 저장소 URL')
    ap.add_argument('--relation', default='OFFICIAL', help='paper_repositories.relation_type')
    ap.add_argument('--work', required=True, help='작업 디렉터리 (소스·클론·중간 JSON)')
    args = ap.parse_args()
    arxiv_id = re.sub(r'^(https?://arxiv\.org/(abs|pdf)/)?', '', args.arxiv.strip()).replace('.pdf', '')
    arxiv_id = re.sub(r'v\d+$', '', arxiv_id)  # 버전 접미사 제거 — upsert 키는 버전 없는 ID
    os.makedirs(args.work, exist_ok=True)

    stage('ARXIV_META', f'arXiv {arxiv_id} 메타데이터')
    paper = arxiv_meta(arxiv_id)
    log(f'{paper["title"]} ({paper["publishedDate"]}, 저자 {len(paper["authors"])}명)')

    stage('EPRINT', 'LaTeX 소스 다운로드')
    src_dir = download_eprint(arxiv_id, os.path.join(args.work, 'eprint'))
    log(f'소스 디렉터리: {os.path.relpath(src_dir, args.work)}')

    stage('REPO_CLONE', f'{args.github} 클론')
    repo_dir = os.path.join(args.work, 'repo')
    shutil.rmtree(repo_dir, ignore_errors=True)
    repo = clone_repo(args.github, repo_dir)
    log(f'{repo["ownerName"]}/{repo["repositoryName"]} @{repo["commitHash"][:7]} '
        f'★{repo["starCount"]} {repo["licenseName"] or "라이선스 미확인"} {repo["primaryLanguage"] or ""}')

    stage('CODE_BLOCKS', 'Python ast 로 함수·메서드 추출')
    blocks, skipped = extract_blocks(repo_dir)
    if not blocks:
        raise SystemExit('저장소에서 Python 함수·메서드를 하나도 찾지 못했습니다 — 현재 업로드는 Python 저장소만 지원합니다')
    log(f'code block {len(blocks)}개 (파일 {len({b["filePath"] for b in blocks})}개, 건너뜀 {skipped})')

    stage('LATEX_SPLIT', 'qwen3 가 단락 경계 제안 — 섹션당 수십 초')
    auto = split_chunks(src_dir, blocks, args.work)
    chunks = to_ingest_chunks(auto)
    if not chunks:
        raise SystemExit('단락을 하나도 만들지 못했습니다')
    log(f'chunk {len(chunks)}개')

    stage('INGEST', 'papers · paper_chunks · repositories · code_blocks 적재')
    repo.update({'relationType': args.relation, 'isPrimary': True, 'codeBlocks': blocks})
    doc = {'papers': [{**paper, 'chunks': chunks, 'repositories': [repo]}]}
    run_ingest(doc, args.work)
    paper_id = paper_id_of(arxiv_id)
    if not paper_id:
        raise SystemExit('적재 후 papers 에서 논문을 찾지 못했습니다')

    print(f'##RESULT paperId={paper_id} chunks={len(chunks)} blocks={len(blocks)}', flush=True)


if __name__ == '__main__':
    main()
