#!/usr/bin/env python3
"""노트 코드 조각 → 저장소 안의 (파일, 심볼, 시작줄, 끝줄) 역추적.

노트에 파일 경로·심볼명이 없어도 코드 본문만 있으면 위치를 찾습니다.
Python(AST) / C(중괄호 매칭) / prototxt·cfg(블록 파서) 세 가지를 지원합니다.
"""
import ast
import collections
import os
import re

# ── 심볼 인덱스 ────────────────────────────────────────────────


def index_python(text):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    parent_of = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                parent_of[child] = node
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            par = parent_of.get(node)
            pname = par.name if isinstance(par, (ast.ClassDef, ast.FunctionDef)) else None
            kind = 'CLASS' if isinstance(node, ast.ClassDef) else ('METHOD' if pname else 'FUNCTION')
            out.append((node.name, kind, pname, node.lineno, node.end_lineno))
    return out


C_FUNC = re.compile(
    r'^(?!\s)(?:[A-Za-z_][\w]*[\w\s\*]*?)\s\*?(\w+)\s*\([^;{]*\)\s*\{', re.M)


def index_c(text):
    """중괄호 매칭으로 최상위 함수 경계를 잡습니다."""
    lines = text.splitlines()
    out = []
    for m in C_FUNC.finditer(text):
        name = m.group(1)
        start = text[:m.start()].count('\n') + 1
        depth, i, end = 0, m.end() - 1, None
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = text[:i].count('\n') + 1
                    break
            i += 1
        if end and end - start < 400:
            out.append((name, 'FUNCTION', None, start, end))
    return out


def index_prototxt(text):
    """Caffe prototxt: 파일 머리(net 정의) + layer { } 블록."""
    lines = text.splitlines()
    out = []
    net = re.search(r'^name:\s*"([^"]+)"', text, re.M)
    first = next((i for i, l in enumerate(lines) if l.strip().startswith('layer')), len(lines))
    if net and first > 0:
        out.append((net.group(1), 'MODULE', None, 1, first))
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('layer'):
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count('{') - lines[j].count('}')
                if depth == 0 and j > i:
                    break
                j += 1
            body = '\n'.join(lines[i:j + 1])
            nm = re.search(r'name:\s*"([^"]+)"', body)
            if nm:
                out.append((nm.group(1), 'MODULE', net.group(1) if net else None, i + 1, j + 1))
            i = j
        i += 1
    return out


def index_cfg(text):
    """darknet cfg: [section] 블록."""
    lines = text.splitlines()
    heads = [(i, l.strip().strip('[]')) for i, l in enumerate(lines) if re.match(r'^\[\w+\]', l.strip())]
    out = []
    for k, (i, name) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append((f'{name}[{k}]', 'MODULE', None, i + 1, end))
    return out


LANG = {'.py': ('Python', index_python), '.c': ('C', index_c), '.cu': ('C', index_c),
        '.h': ('C', index_c), '.prototxt': ('Prototxt', index_prototxt),
        '.cfg': ('Config', index_cfg)}


class Repo:
    """key 로 받아둔 저장소 원문 전체를 메모리에 올려두고 역추적합니다."""

    def __init__(self, src_dir, key):
        self.files = {}
        prefix = key + '--'
        for fn in os.listdir(src_dir):
            if not fn.startswith(prefix):
                continue
            path = fn[len(prefix):].replace('~', '/')
            ext = os.path.splitext(path)[1]
            if ext not in LANG:
                continue
            try:
                text = open(os.path.join(src_dir, fn), encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            lang, indexer = LANG[ext]
            self.files[path] = {'text': text, 'lines': text.splitlines(),
                                'lang': lang, 'symbols': indexer(text)}
        # 줄 → 파일 역인덱스 (공백 제거 후)
        self.line_index = collections.defaultdict(list)
        for path, f in self.files.items():
            for n, line in enumerate(f['lines'], 1):
                s = line.strip()
                if len(s) >= 12:
                    self.line_index[s].append((path, n))
        # 공백을 전부 없앤 본문 + (위치 → 줄번호) 사상
        # 노트 코드가 줄바꿈만 다르게 재포맷된 경우를 잡기 위한 것
        for path, f in self.files.items():
            squashed, at_line = [], []
            for n, line in enumerate(f['lines'], 1):
                for ch in line:
                    if not ch.isspace():
                        squashed.append(ch)
                        at_line.append(n)
            f['squashed'] = ''.join(squashed)
            f['at_line'] = at_line

    @staticmethod
    def _squash(s):
        return ''.join(ch for ch in s if not ch.isspace())

    def _locate_squashed(self, note_code, hint_path=None, min_votes=2):
        """공백을 무시하고 노트 코드 조각을 저장소 본문에서 찾습니다."""
        q = self._squash(note_code)
        if len(q) < 32:
            return None
        # 노트 코드가 축약·재포맷된 경우가 많아 짧은 창을 촘촘히 훑습니다.
        windows = [q[i:i + 32] for i in range(0, max(1, len(q) - 32), 16)][:80]
        votes = collections.Counter()
        for w in windows:
            if len(w) < 32:
                continue
            found = []
            for path, f in self.files.items():
                if hint_path and path != hint_path:
                    continue
                pos = f['squashed'].find(w)
                if pos >= 0:
                    found.append((path, pos))
            if len(found) != 1:          # 저장소 안에서 유일한 조각만 인정
                continue
            path, pos = found[0]
            line = self.files[path]['at_line'][pos]
            sym = self.symbol_at(path, line)
            votes[(path, sym[0] if sym else None, sym[3] if sym else None)] += 1
        if not votes:
            return None
        (path, name, start), hits = votes.most_common(1)[0]
        if hits < min_votes or name is None:
            return None
        sym = next(s for s in self.files[path]['symbols'] if s[0] == name and s[3] == start)
        return (path, sym[0], sym[1], sym[2], sym[3], sym[4], hits)

    def symbol_at(self, path, line):
        cands = [s for s in self.files[path]['symbols'] if s[3] <= line <= s[4]]
        return min(cands, key=lambda s: s[4] - s[3]) if cands else None

    def locate(self, note_code, hint_path=None, min_hits=2):
        """노트 코드 → (path, name, kind, parent, start, end). 못 찾으면 None."""
        if not note_code:
            return None
        needles = [l.strip() for l in note_code.splitlines() if len(l.strip()) >= 12]
        if not needles:
            return None
        votes = collections.Counter()
        for s in needles:
            for path, n in self.line_index.get(s, []):
                if hint_path and path != hint_path:
                    continue
                sym = self.symbol_at(path, n)
                votes[(path, sym[0] if sym else None, sym[3] if sym else None)] += 1
        if votes:
            (path, name, start), hits = votes.most_common(1)[0]
            if hits >= min_hits and name is not None:
                sym = next(s for s in self.files[path]['symbols']
                           if s[0] == name and s[3] == start)
                return (path, sym[0], sym[1], sym[2], sym[3], sym[4], hits)
        # 줄 단위로 안 맞으면 공백 무시 매칭 (노트가 재포맷된 경우)
        return self._locate_squashed(note_code, hint_path)

    def slice(self, path, start, end):
        return '\n'.join(self.files[path]['lines'][start - 1:end])

    def lang(self, path):
        return self.files[path]['lang']
