#!/usr/bin/env python3
"""LaTeX 소스 → 단락(chunk) 자동 분리 — 업로드 파이프라인 1단계 (#41, 확장기능 §5.1).

설계 원칙 (§5.1 그대로):
  1. LLM 은 "어디서 자를지 + 소제목 + 매핑 가능 여부"만 제안한다.
     chunk 본문은 코드가 원문에서 그대로 슬라이스한다 — 원문이 LLM 을 거치면
     환각으로 미묘하게 변형되고, 그러면 "content 가 논문 원문" 검수 기준이 깨진다.
  2. 매핑 가능 여부는 논문 텍스트만으로 판단할 수 없다(미매핑 61건 중 24건·39.3%
     는 저장소가 그 구현을 배포하지 않는 경우 — tally_unmapped.py 집계). 그래서
     프롬프트에 **그 저장소의 심볼 목록을 동봉**하고 "이 단락에 대응하는 심볼이
     목록에 있는가"로 묻는다.
  3. 거짓 억제(진짜 매핑을 비매핑으로 오판)는 화면에서 조용히 사라져 발견이 안
     되므로 비대칭이 크다 — 확신이 없으면 mappable 쪽으로 판단하라고 지시한다.

카탈로그 DB 에는 아무것도 쓰지 않는다. 출력은 JSON 파일뿐이다 (#41 합의).

    # 분리 (LaTeX 소스 디렉터리 → chunks JSON)
    python3 scripts/latex2chunks.py split <latex_dir> --paper-id 1 --out /tmp/auto_chunks.json

    # 정답 대비 측정 (수동 큐레이션 chunk 와 대조)
    python3 scripts/latex2chunks.py eval /tmp/auto_chunks.json --paper-id 1

LaTeX 원문은 저자 저작권이므로 저장소에 커밋하지 않는다 — arXiv e-print 를
로컬에 받아 풀고 그 디렉터리를 넘긴다.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

OLLAMA = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
MODEL = os.environ.get('CODEATLAS_LLM', 'qwen3:8b')
# 호출당 LLM 타임아웃. 기본 480초는 실험 경로(#48) 기준값이고, 업로드 파이프라인은
# 150초로 줄여서 넘긴다(upload_pipeline.py) — 폴백(문단=chunk)이 품질 손실이 아니라는 것을
# §5.1 IoU 재측정이 이미 보여줬기 때문(문단 분할 0.822 > LLM 병합 0.701). 그렇다면 한 섹션에
# 480×3 = 24분을 기다릴 근거가 없다 — 150×3 + 백오프 = 8분이면 폴백으로 떨어진다.
LLM_TIMEOUT = int(os.environ.get('CODEATLAS_LLM_TIMEOUT', '480'))


# ── LaTeX 전처리 (순수 코드 — LLM 없음) ──────────────────────────────

def find_main_tex(src_dir):
    for name in sorted(os.listdir(src_dir)):
        if name.endswith('.tex'):
            with open(os.path.join(src_dir, name), errors='replace') as f:
                if '\\documentclass' in f.read():
                    return os.path.join(src_dir, name)
    sys.exit(f'\\documentclass 가 있는 .tex 를 {src_dir} 에서 찾지 못했습니다')


def strip_comments(text):
    # \% 는 퍼센트 리터럴이므로 남긴다
    return re.sub(r'(?<!\\)%.*', '', text)


def inline_inputs(path, seen=None):
    """\\input{...} 을 재귀로 병합해 한 문서로 만든다."""
    seen = seen or set()
    if path in seen:
        return ''
    seen.add(path)
    base = os.path.dirname(path)
    out = []
    with open(path, errors='replace') as f:
        for line in f:
            m = re.match(r'\s*\\input\{([^}]+)\}', line)
            if m:
                sub = os.path.join(base, m.group(1))
                if not sub.endswith('.tex'):
                    sub += '.tex'
                if os.path.exists(sub):
                    out.append(inline_inputs(sub, seen))
                    continue
            out.append(line)
    return ''.join(out)


ATOMIC_ENVS = ('figure', 'table', 'equation', 'align', 'algorithm', 'itemize', 'enumerate')


def split_paragraphs(body):
    """빈 줄 기준으로 자르되 figure/table 같은 환경 안에서는 자르지 않는다."""
    paras, buf, depth = [], [], 0
    for line in body.splitlines():
        for m in re.finditer(r'\\(begin|end)\{(\w+?)\*?\}', line):
            if m.group(2) in ATOMIC_ENVS:
                depth += 1 if m.group(1) == 'begin' else -1
        if not line.strip() and depth <= 0:
            if buf:
                paras.append('\n'.join(buf))
                buf = []
        else:
            buf.append(line)
    if buf:
        paras.append('\n'.join(buf))
    # 명령어만 있는 조각(\label 한 줄 등)은 앞 문단에 붙인다
    merged = []
    for p in paras:
        if merged and not latex_to_text(p).strip():
            merged[-1] += '\n\n' + p
        else:
            merged.append(p)
    return merged


def split_sections(doc):
    """\\section·\\subsection 경계로 자른다 — 문서 구조가 이미 주는 경계는
    LLM 에게 묻지 않는다. 호출 단위가 작아져 분할 제약 위반도 줄어든다."""
    sections = []
    m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', doc, re.S)
    if m:
        sections.append(('Abstract', m.group(1)))
    parts = re.split(r'\\section\*?\{([^}]*)\}', doc)
    # parts = [머리말, 제목1, 본문1, 제목2, 본문2, ...]
    for i in range(1, len(parts) - 1, 2):
        sec_title = re.sub(r'\\\w+|[{}]', '', parts[i]).strip()
        body = re.split(r'\\begin\{thebibliography\}|\\bibliography\{', parts[i + 1])[0]
        subs = re.split(r'\\(?:sub)?subsection\*?\{([^}]*)\}', body)
        if subs[0].strip():
            sections.append((sec_title, subs[0]))
        for j in range(1, len(subs) - 1, 2):
            sub_title = re.sub(r'\\\w+|[{}]', '', subs[j]).strip()
            sections.append((f'{sec_title} — {sub_title}', subs[j + 1]))
    return sections


def latex_to_text(s):
    """비교·표시용 평문화. 슬라이스된 원문 자체는 변형하지 않는다.

    수식은 자리표시자로 뭉개지 않고 \\command 만 걷어 식별자·숫자를 남긴다 —
    §3.2.2 처럼 수식(W^Q·h=8·d_k=64)이 곧 매핑 근거인 단락에서 자리표시자는
    판단 재료를 지워 거짓 억제를 만들었다(FN 17·18, A 의 A/B 재현 — #42 리뷰).
    """
    def keep(m):
        inner = re.sub(r'\\[a-zA-Z]+', ' ', m.group(1))
        return ' ' + re.sub(r'[{}\\]', ' ', inner) + ' '
    s = re.sub(r'\\(sub)*section\*?\{[^}]*\}', ' ', s)
    s = re.sub(r'\\(cite[pt]?|ref|label|eqref)\{[^}]*\}', ' ', s)
    s = re.sub(r'\\begin\{\w+\*?\}|\\end\{\w+\*?\}', ' ', s)
    s = re.sub(r'\$\$(.*?)\$\$', keep, s, flags=re.S)
    s = re.sub(r'\$(.*?)\$', keep, s, flags=re.S)
    s = re.sub(r'\\[a-zA-Z]+(\[[^\]]*\])?', ' ', s)
    s = re.sub(r'[{}~]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


# ── DB 조회 (읽기 전용 · json_agg 로 통짜 수신 — CONTRIBUTING §9) ──────

def psql_json(sql):
    r = subprocess.run(
        ['docker', 'exec', '-i', 'codeatlas-postgres', 'psql', '-U', 'codeatlas',
         '-d', 'codeatlas', '-tA', '-v', 'ON_ERROR_STOP=1'],
        input=sql, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'DB 조회 실패:\n{r.stderr}')
    out = r.stdout.strip()
    return json.loads(out) if out else []


def load_symbols(paper_id):
    rows = psql_json(f"""
        SELECT json_agg(json_build_object(
                 'name', CASE WHEN cb.parent_symbol_name IS NOT NULL
                              THEN cb.parent_symbol_name || '.' || cb.symbol_name
                              ELSE cb.symbol_name END,
                 'file', cb.file_path, 'type', cb.symbol_type))
        FROM code_blocks cb
        JOIN paper_repositories pr ON pr.repository_id = cb.repository_id
        WHERE pr.paper_id = {int(paper_id)}""")
    return rows or []


def load_manual_chunks(paper_id):
    return psql_json(f"""
        SELECT json_agg(json_build_object(
                 'chunkIndex', pc.chunk_index,
                 'sectionTitle', pc.section_title,
                 'content', pc.content,
                 'mapped', EXISTS (SELECT 1 FROM paper_code_mappings m
                                   WHERE m.paper_chunk_id = pc.id
                                     AND m.mapping_method = 'MANUAL'))
                 ORDER BY pc.chunk_index)
        FROM paper_chunks pc WHERE pc.paper_id = {int(paper_id)}""") or []


# ── LLM — 경계·라벨·매핑 가능 여부 제안 ─────────────────────────────

PROMPT = """당신은 논문 섹션을 의미 단위(chunk)로 나누는 도구입니다.

섹션 "{title}" 의 문단 목록입니다 (번호는 문단 순서):

{paras}

이 저장소의 코드 심볼 목록입니다:
{symbols}

작업:
1. 주제가 바뀌는 지점에서 자르세요. "cuts" 는 **그 번호의 문단 뒤에서 자른다**는
   뜻입니다 (예: 문단이 5개일 때 cuts=[2] 면 [1-2], [3-5] 두 조각).
   자를 곳이 없으면 cuts=[] 로 두세요.
2. 잘린 조각 순서대로 "segments" 에 항목을 하나씩 쓰세요 (조각 수 = cuts 수 + 1):
   - label: 짧은 한국어 소제목
   - mappable 판단 기준은 **심볼 목록이 전부**입니다. 목록을 하나씩 훑으면서 이
     조각이 서술하는 구조·동작·절차·설정을 구현했을 심볼이 있는지 보세요. 있으면
     mappable=true 와 그 심볼 이름을, 정말 없으면 mappable=false 를 쓰세요.
   - 조각의 "종류"로 판단하지 마세요. 학습 스케줄·배칭·디코딩 설정이라도 optimizer,
     dataloader, translator 류 심볼이 목록에 있으면 true 입니다. 반대로 실험 결과
     수치·Figure/Table 비교·감사의 글처럼 **어떤 코드로도 구현되지 않는 서술**만
     false 입니다.
   - **설정 값도 구현입니다**: warmup steps, beam size, length penalty, dropout 비율
     같은 수치는 그 값을 사용하는 코드(lr scheduler, beam search, translator 등)가
     목록에 있으면 mappable=true 입니다. "수치라서 코드가 아니다"로 판단하지 마세요.
   - 확신이 없으면 mappable=true 로 두세요. 잘못된 false 는 진짜 매핑을 화면에서
     조용히 숨기므로 잘못된 true 보다 해롭습니다.

JSON 만 출력하세요:
{{"cuts":[2],"segments":[{{"label":"...","mappable":true,"symbols":["Encoder.forward"]}},{{"label":"...","mappable":false,"symbols":[]}}]}}"""


def ollama_generate(prompt):
    req = urllib.request.Request(
        f'{OLLAMA}/api/generate',
        data=json.dumps({'model': MODEL, 'prompt': prompt, 'stream': False,
                         # seed 고정 — 환경 간 불일치는 못 막지만 세션 내 변수를
                         # 줄이고 "동일 세션 안에서는 결정적"을 코드로 뒷받침한다.
                         'options': {'temperature': 0, 'seed': 0}}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
        text = json.loads(resp.read())['response']
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    # 모델이 JSON 뒤에 설명을 덧붙이는 경우가 있어 탐욕 매칭 대신
    # 첫 '{' 부터 raw_decode 로 객체 하나만 떼어낸다.
    start = text.find('{')
    if start < 0:
        raise ValueError(f'JSON 없음: {text[:200]}')
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def plan_to_chunks(plan, n, title):
    """cuts 계약을 chunk 목록으로 바꾼다.

    cuts 는 어떤 부분집합이든 파티션으로서 유효하므로(범위 밖·중복만 걸러냄)
    "문단을 정확히 덮지 못함" 실패 모드가 없다. segments 가 조각 수와 어긋나면
    순서대로 붙이고 모자란 쪽은 mappable=None 으로 남긴다 — 조용히 지어내지 않는다.
    """
    cuts = sorted({c for c in plan.get('cuts', []) if isinstance(c, int) and 1 <= c < n})
    bounds = [0] + cuts + [n]
    segs = plan.get('segments', [])
    chunks = []
    for k in range(len(bounds) - 1):
        seg = segs[k] if k < len(segs) else {}
        chunks.append({
            'paragraphs': list(range(bounds[k] + 1, bounds[k + 1] + 1)),
            'label': seg.get('label') or title,
            'mappable': seg.get('mappable') if isinstance(seg.get('mappable'), bool) else None,
            'symbols': seg.get('symbols') or [],
        })
    return {'chunks': chunks}


def propose_chunks(title, paras, symbols):
    para_block = '\n'.join(f'[{i + 1}] {latex_to_text(p)[:600]}' for i, p in enumerate(paras))
    sym_block = '\n'.join(f"- {s['name']} ({s['file']})" for s in symbols)
    prompt = PROMPT.format(title=title, paras=para_block, symbols=sym_block)
    for attempt in (1, 2, 3):
        try:
            return plan_to_chunks(ollama_generate(prompt), len(paras), title)
        except Exception as e:
            print(f'   ⚠️ LLM 응답 파싱 실패 (시도 {attempt}): {e}', file=sys.stderr)
            # 타임아웃이 폴백의 주원인으로 특정됨 — 즉시 재시도하면 같은 부하에서
            # 또 죽는다. 짧게 물러났다 다시 간다. 마지막 시도 뒤에는 재시도가
            # 없으므로 바로 폴백으로 내려간다.
            if attempt < 3:
                time.sleep(10 * attempt)
    # 폴백: 문단 하나 = chunk 하나. 조용히 삼키지 않고 표시를 남긴다.
    return {'chunks': [{'paragraphs': [i + 1], 'label': title, 'mappable': None,
                        'symbols': [], 'fallback': True}
                       for i in range(len(paras))]}


# ── split / eval ─────────────────────────────────────────────────────

def ws_norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def cmd_split(args):
    doc = strip_comments(inline_inputs(find_main_tex(args.src_dir)))
    doc_norm = ws_norm(doc)
    sections = split_sections(doc)
    # 심볼 인벤토리: 업로드 파이프라인(upload_pipeline.py)은 적재 전이라 DB 에 논문이
    # 없으므로 파일로 넘긴다. 실험 경로(--paper-id)는 그대로 DB 에서 읽는다.
    if args.symbols_json:
        symbols = json.load(open(args.symbols_json))
    else:
        symbols = load_symbols(args.paper_id)
    print(f'섹션 {len(sections)}개 · 심볼 {len(symbols)}개 ({MODEL})')

    out, idx = [], 0
    for title, body in sections:
        paras = split_paragraphs(body)
        paras = [p for p in paras if latex_to_text(p).strip()]
        if not paras:
            continue
        if args.single_para_no_llm and len(paras) == 1:
            # 문단이 하나면 자를 곳이 없다 — 업로드 경로는 label·mappable 을 쓰지 않으므로
            # LLM 호출을 통째로 건너뛴다 (Acknowledgements 같은 짧은 섹션이 480초 타임아웃에
            # 걸려 업로드 전체를 20분 넘게 붙잡은 실측). 실험 경로(--paper-id)는 그대로 LLM 에 묻는다.
            # label 을 title 로 두면 subsection == section 이 돼 임베딩 텍스트에 제목이 두 번 들어간다
            plan = {'chunks': [{'paragraphs': [1], 'label': None, 'mappable': None, 'symbols': []}]}
        else:
            plan = propose_chunks(title, paras, symbols)
        for c in plan['chunks']:
            content = '\n\n'.join(paras[i - 1] for i in c['paragraphs'])
            # 원문 보존 검증 — 슬라이스한 문단이 병합 문서에 그대로 있어야 한다.
            # 공백 표현(빈 줄의 후행 공백 등)만 정규화해 비교한다.
            # 검수 기준 그 자체이므로 assert 가 아니라 raise — python -O 로 꺼지면 안 된다.
            for i in c['paragraphs']:
                if ws_norm(paras[i - 1]) not in doc_norm:
                    raise RuntimeError(f'원문 불일치: 문단 {i} ({title})')
            out.append({'chunkIndex': idx, 'sectionTitle': title,
                        'subsectionTitle': c.get('label'), 'content': content,
                        'mappable': c.get('mappable'), 'symbols': c.get('symbols', []),
                        'fallback': c.get('fallback', False)})
            idx += 1
        print(f'  {title}: 문단 {len(paras)} → chunk {len(plan["chunks"])}')

    with open(args.out, 'w') as f:
        json.dump({'paperId': args.paper_id, 'model': MODEL, 'chunks': out}, f,
                  ensure_ascii=False, indent=2)
    n_fb = sum(1 for c in out if c['fallback'])
    print(f'chunk {len(out)}개 → {args.out}' + (f' (폴백 {n_fb})' if n_fb else ''))


def tokens(text):
    return set(re.findall(r'[a-zA-Z]{3,}', text.lower()))


def cmd_eval(args):
    auto = json.load(open(args.auto_json))['chunks']
    manual = load_manual_chunks(args.paper_id)
    if not manual:
        sys.exit(f'paper {args.paper_id} 의 수동 chunk 가 DB 에 없습니다')

    # 경계: 수동 chunk 마다 가장 잘 겹치는 자동 chunk 를 찾는다.
    # 포함률(|∩|/|수동|)은 자동 chunk 가 클수록 유리해 거친 분할에 벌점이 없다 —
    # 섹션=chunk 무LLM 분할이 95.2% 를 받는 지표다(A 실측, #42 리뷰). 그래서
    # 정렬 판정과 헤드라인은 IoU(|∩|/|∪|) 기준으로 하고, 포함률은 참고로만 남긴다.
    auto_toks = [tokens(latex_to_text(c['content'])) for c in auto]
    aligned, cover_hits, iou_hits, iou_sum = [], 0, 0, 0.0
    for mch in manual:
        mt = tokens(mch['content'])
        cov_i, best_cov, best_iou = -1, 0.0, 0.0
        for i, at in enumerate(auto_toks):
            inter = len(mt & at)
            cov = inter / len(mt) if mt else 0
            iou = inter / len(mt | at) if (mt | at) else 0
            best_iou = max(best_iou, iou)
            if cov > best_cov:
                cov_i, best_cov = i, cov
        # 분류 판정 짝은 포함률 기준을 유지한다 — "이 수동 chunk 의 내용을 담은
        # 자동 chunk" 의 판단을 물려받는 것이라 IoU 로 조이면 판정 표본만 준다.
        aligned.append((mch, cov_i, best_cov))
        iou_sum += best_iou
        if best_iou >= args.iou:
            iou_hits += 1
        if best_cov >= args.cover:
            cover_hits += 1

    print(f'수동 {len(manual)} / 자동 {len(auto)} chunk')
    print(f'경계 정렬 (IoU 기준): IoU ≥ {args.iou:.0%} 인 수동 chunk '
          f'{iou_hits}/{len(manual)} ({100 * iou_hits / len(manual):.1f}%) · '
          f'평균 IoU {iou_sum / len(manual):.3f}')
    print(f'  (참고 — 포함률 ≥ {args.cover:.0%}: {cover_hits}/{len(manual)}. '
          f'거친 분할에 유리한 지표라 판정에는 쓰지 않음)')

    # 매핑 가능 여부: 정렬된 쌍에서 혼동행렬 (gold = MANUAL 매핑 존재 여부)
    tp = fp = fn = tn = skipped = 0
    fn_list = []
    for mch, i, cov in aligned:
        pred = auto[i]['mappable'] if i >= 0 else None
        if cov < args.cover or pred is None:
            skipped += 1
            continue
        gold = mch['mapped']
        if gold and pred:
            tp += 1
        elif gold and not pred:
            fn += 1
            fn_list.append(mch['chunkIndex'])
        elif not gold and pred:
            fp += 1
        else:
            tn += 1
    judged = tp + fp + fn + tn
    print(f'\n매핑 가능 여부 (판정 {judged} / 제외 {skipped} — 미정렬·폴백):')
    print(f'  gold 매핑 → 예측 매핑     TP {tp}')
    print(f'  gold 매핑 → 예측 비매핑   FN {fn}   ← 거짓 억제 (치명)')
    print(f'  gold 비매핑 → 예측 매핑   FP {fp}   (무해 — 기존 동작과 동일)')
    print(f'  gold 비매핑 → 예측 비매핑 TN {tn}   ← 자동화가 새로 잡은 것')
    if tn + fp:
        print(f'  특이도(gold 비매핑 중 TN): {tn}/{tn + fp} ({100 * tn / (tn + fp):.0f}%)')
    # "항상 true" 는 FN 0 / TN 0 인 공짜 기준선이다. 분류기의 실질 기여는
    # (TN 이득) 대 (FN 손실) 비교로 읽어야 한다 — FN 지표만 보면 항상-true 가 최강.
    print(f'  기준선(항상 true): FN 0 / TN 0 — 이 분류기의 순변화: FN +{fn} / TN +{tn}')
    if fn_list:
        print(f'  거짓 억제 chunk_index: {fn_list}')
    # gold 의 의미: '구현 불가'가 아니라 '큐레이터가 정답셋에 넣지 않기로 한 것'.
    # 프롬프트의 매핑 정의(설정 값도 구현)와 다를 수 있어 FP 에는 정의 불일치가 섞인다.


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sp = sub.add_parser('split', help='LaTeX 디렉터리 → chunks JSON')
    sp.add_argument('src_dir')
    sp.add_argument('--paper-id', type=int, help='심볼 인벤토리를 가져올 논문 (DB)')
    sp.add_argument('--symbols-json', help='심볼 인벤토리 파일 [{name, file}] — 적재 전 업로드 경로용')
    sp.add_argument('--single-para-no-llm', action='store_true',
                    help='문단이 하나뿐인 섹션은 LLM 없이 chunk 하나로 (업로드 경로용)')
    sp.add_argument('--out', required=True)
    ev = sub.add_parser('eval', help='자동 chunk 를 수동 큐레이션과 대조')
    ev.add_argument('auto_json')
    ev.add_argument('--paper-id', type=int, required=True)
    ev.add_argument('--cover', type=float, default=0.5, help='분류 판정 짝짓기 포함률 (기본 0.5)')
    ev.add_argument('--iou', type=float, default=0.5, help='경계 정렬 판정 IoU (기본 0.5)')
    args = ap.parse_args()
    if args.cmd == 'split' and args.paper_id is None and not args.symbols_json:
        ap.error('split 에는 --paper-id 또는 --symbols-json 이 필요합니다')
    cmd_split(args) if args.cmd == 'split' else cmd_eval(args)


if __name__ == '__main__':
    main()
