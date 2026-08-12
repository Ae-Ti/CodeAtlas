#!/usr/bin/env python3
"""노트 마크다운 9편 → 구조화 레코드.

두 가지 서식을 다룹니다.
  A) CHUNK 형식  — BERT / CLIP / Llama / Segment Anything / Stable Diffusion / ViT
  B) 판정 형식   — ResNet / U-Net / YOLO  (기존 Attention 노트와 같은 모양)
"""
import re
import unicodedata

CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩'

ALIAS = {
    '논문위치': 'loc', '위치': 'loc',
    '논문원문': 'paper', '논문내용': 'paper', '논문핵심텍스트': 'paper', '논문텍스트': 'paper',
    '논문대응텍스트': 'paper',
    '구현목적': 'meaning', '논문구현의미': 'meaning', '논문의미': 'meaning', '구현흐름': 'meaning',
    'git코드위치': 'codeloc', 'git위치': 'codeloc',
    'git코드': 'code', '코드원문': 'code', '코드': 'code', '대응코드': 'code',
    '실제코드': 'code', '저장소추가코드': 'code',
    '매칭': 'match', '코드매칭': 'match', 'codematch': 'match', '논문↔코드매칭': 'match',
    '논문↔코드매핑': 'match', '논문↔코드': 'match', 'mapping': 'match', '논문연결': 'match',
    'codetype': 'kind', '판정': 'kind',
    'db저장': 'db', 'db': 'db',
    '예상코드': 'expected',
}


def norm_head(t):
    t = t.strip().lstrip('#').strip()
    t = ''.join(c for c in t if c not in CIRCLED)          # ① 제거는 NFKC 앞에서 (NFKC가 '1'로 바꿔버림)
    t = unicodedata.normalize('NFKC', t).strip()
    t = re.sub(r'^\s*\d+\s*[.)]?\s*', '', t)
    t = re.sub(r'[\s()（）\-–—:：]', '', t).lower()
    return t


def fences(text):
    return [m.group(1).rstrip() for m in re.finditer(r'```[a-zA-Z]*\n(.*?)```', text, re.S)]


def quotes(text):
    out, buf = [], []
    for line in text.splitlines():
        if line.startswith('>'):
            buf.append(line[1:].strip())
        elif buf:
            s = ' '.join(x for x in buf if x).strip()
            if s:
                out.append(s)
            buf = []
    if buf:
        s = ' '.join(x for x in buf if x).strip()
        if s:
            out.append(s)
    return out


def parse_loc(block):
    """'Section 2 BERT / Page 3' → (section, page_start, page_end)"""
    sec, p1, p2 = None, None, None
    m = re.search(r'(Section[^\n]*|Appendix[^\n]*|Abstract|Figure[^\n]*)', block, re.I)
    if m:
        sec = m.group(1).strip()
    pages = re.findall(r'Page[s]?\s*([0-9]+)\s*(?:[-~–]\s*([0-9]+))?', block, re.I)
    if pages:
        p1 = int(pages[0][0])
        p2 = int(pages[0][1]) if pages[0][1] else p1
    return sec, p1, p2


FILE_LABEL = re.compile(r'(파일|경로|File|Path)\s*[:：]?\s*$', re.I)
SYM_LABEL = re.compile(r'(함수|클래스|메서드|블록|Function|Class|Method)\s*[:：]?\s*$', re.I)
PATH_RE = re.compile(r'[\w./\\-]+\.(py|cpp|cu|prototxt|c|h|hpp|yaml|yml|cfg|json|sh|ipynb)\b')


def parse_codeloc(block):
    """라벨 줄 다음에 오는 코드펜스를 짝지어 (path, symbol) 추출."""
    path = symbol = None
    pending = None
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if FILE_LABEL.search(line):
            pending = 'path'
        elif SYM_LABEL.search(line):
            pending = 'symbol'
        elif line.startswith('```'):
            j = i + 1
            val = []
            while j < len(lines) and not lines[j].startswith('```'):
                val.append(lines[j])
                j += 1
            v = next((x.strip() for x in val if x.strip()), '')
            if pending == 'path' and not path:
                path = v
            elif pending == 'symbol' and not symbol:
                symbol = v
            elif not path and PATH_RE.search(v):
                path = v
            pending = None
            i = j
        i += 1
    if path is None:
        m = PATH_RE.search(block)
        if m:
            path = m.group(0)
    if symbol is None:
        m = re.search(r'`?\b([A-Za-z_][A-Za-z0-9_.]*)\s*\(\s*\)`?', block)
        if m:
            symbol = m.group(1)
    if path:
        path = PATH_RE.search(path).group(0) if PATH_RE.search(path) else path.strip('`" ')
    if symbol:
        symbol = re.sub(r'\(.*$', '', symbol).strip('`" .')
        symbol = symbol.split()[-1] if symbol.split() else None
    return path, symbol


def split_sections(body):
    """헤딩 기준으로 {키: 본문} + 제목 추출."""
    lines = body.splitlines()
    title, cur, secs = None, None, {}
    buf = []
    for line in lines:
        if re.match(r'^#{1,6}\s', line):
            if cur:
                secs.setdefault(cur, []).append('\n'.join(buf))
            key = ALIAS.get(norm_head(line))
            if key:
                cur, buf = key, []
            else:
                if title is None and norm_head(line) and not re.match(r'^#\s*CHUNK', line, re.I):
                    title = re.sub(r'^#+\s*', '', line).strip()
                cur, buf = None, []
        elif cur:
            buf.append(line)
    if cur:
        secs.setdefault(cur, []).append('\n'.join(buf))
    return title, {k: '\n'.join(v) for k, v in secs.items()}


def parse_format_a(text):
    parts = re.split(r'^#\s*CHUNK\s+([A-Za-z0-9\-]+)\s*$', text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        tag, body = parts[i], parts[i + 1]
        title, s = split_sections(body)
        sec, p1, p2 = parse_loc(s.get('loc', ''))
        path, sym = parse_codeloc(s.get('codeloc', '') or s.get('code', ''))
        code = max(fences(s.get('code', '')), key=len, default=None)
        out.append({'tag': tag, 'title': title, 'section': sec, 'page': (p1, p2),
                    'paper': quotes(s.get('paper', '')), 'meaning': s.get('meaning', '').strip(),
                    'filePath': path, 'symbol': sym, 'code': code,
                    'match': s.get('match', '').strip(), 'kind': s.get('kind', '').strip()})
    return out


def parse_format_b(text):
    page = None
    out = []
    blocks = re.split(r'^(#{1,3})\s+(.+)$', text, flags=re.M)
    cur = None
    i = 1
    while i < len(blocks) - 1:
        level, head, body = blocks[i], blocks[i + 1], blocks[i + 2]
        m = re.match(r'^(\d+)\s*페이지', head.strip())
        if level == '#' and m:
            page = int(m.group(1))
        elif level == '##' and re.match(r'^\d+[.)]', head.strip()):
            cur = {'tag': f'p{page}-{len(out)+1}', 'title': re.sub(r'^\d+[.)]\s*', '', head.strip()),
                   'section': None, 'page': (page, page), 'paper': [], 'meaning': '',
                   'filePath': None, 'symbol': None, 'code': None, 'match': '', 'kind': ''}
            out.append(cur)
        elif level == '###' and cur is not None:
            key = ALIAS.get(norm_head(head))
            if key == 'paper':
                cur['paper'] += quotes(body)
            elif key == 'code':
                c = max(fences(body), key=len, default=None)
                if c and not cur['code']:
                    cur['code'] = c
                    cur['meaning'] = re.sub(r'```.*?```', '', body, flags=re.S).strip()[:400]
            elif key == 'kind':
                cur['kind'] = ' '.join(fences(body)) or body.strip()[:60]
            elif key == 'expected':
                cur['kind'] = (cur['kind'] + ' EXPECTED').strip()
        i += 3
    return out
