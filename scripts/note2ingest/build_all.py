#!/usr/bin/env python3
"""노트 9편 → ingest JSON 9개 (역매칭판).

파일적재_문제점.md 의 문제 1·2·5·6을 노트 수정 없이 해결합니다.
노트에 경로·심볼이 없어도 코드 본문을 저장소 원문에 역매칭해 위치를 특정합니다.
"""
import collections
import json
import os
import re
import sys

SC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SC)
from parse_md import parse_format_a, parse_format_b     # noqa: E402
from locate import Repo                                  # noqa: E402

ING = '/Users/ungsik/Desktop/CodeAtlas/CodeAtlas_git/CodeAtlas/database/ingest'
META = json.load(open(os.path.join(SC, 'arxiv_meta.json'), encoding='utf-8'))

PAPERS = {
    'BERT':    ('1810.04805', 'a', 'bert', dict(
        slug='google-research/bert', branch='master', relation='OFFICIAL',
        sha='eedf5716ce1268e56f0a50264a88cafad334ac61', license='Apache-2.0', stars=40057)),
    'CLIP':    ('2103.00020', 'a', 'clip', dict(
        slug='openai/CLIP', branch='main', relation='OFFICIAL',
        sha='d05afc436d78f1c48dc0dbf8e5980a9d471f35f6', license='MIT', stars=34155)),
    'Llama':   ('2407.21783', 'a', 'llama3', dict(
        slug='meta-llama/llama3', branch='main', relation='OFFICIAL',
        sha='a0940f9cf7065d45bb6675660f80d305c041a754', license='NOASSERTION', stars=29262)),
    'Segment': ('2304.02643', 'a', 'segment_anything', dict(
        slug='facebookresearch/segment-anything', branch='main', relation='OFFICIAL',
        sha='dca509fe793f601edb92606367a655c15ac00fdf', license='Apache-2.0', stars=54671)),
    'Stable':  ('2112.10752', 'a', 'latent_diffusion', dict(
        slug='CompVis/latent-diffusion', branch='main', relation='OFFICIAL',
        sha='a506df5756472e2ebaf9078affdde2c4f1502cd4', license='MIT', stars=14127)),
    'Vision':  ('2010.11929', 'a', 'vision_transformer', dict(
        slug='google-research/vision_transformer', branch='main', relation='OFFICIAL',
        sha='64801f1b3b367b3611cc27a3d45cc22870a36fb3', license='Apache-2.0', stars=12666)),
    'ResNet':  ('1512.03385', 'b', 'resnet', dict(
        slug='KaimingHe/deep-residual-networks', branch='master', relation='OFFICIAL',
        sha='a7026cb6d478e131b765b898c312e25f9f6dc031', license='MIT', stars=6750)),
    'U-net':   ('1505.04597', 'b', 'unet', dict(
        slug='Miltos-90/UNet_Biomedical_Image_Segmentation', branch='main', relation='COMMUNITY',
        sha='a50669d1cbbb256b12b05f60817e0e4b37dea9f6', license=None, stars=33)),
    'YOLO':    ('1506.02640', 'b', 'yolo', dict(
        slug='pjreddie/darknet', branch='master', relation='OFFICIAL',
        sha='f6afaabcdf85f77e7aff2ec55c020c0e297c77f9', license='NOASSERTION', stars=26492)),
}

TYPE_OK = {'FILE', 'CLASS', 'FUNCTION', 'METHOD', 'MODULE'}


def md_of(key):
    return next(f for f in os.listdir(ING) if f.startswith(key) and f.endswith('.md'))


def resolve_all(key, repo_info):
    """레코드마다 (블록키, 사유) 를 정한다."""
    fmt = PAPERS[key][1]
    recs = (parse_format_a if fmt == 'a' else parse_format_b)(
        open(os.path.join(ING, md_of(key)), encoding='utf-8').read())
    repo = Repo(os.path.join(SC, 'src'), key)
    valid_paths = set(repo.files)

    blocks, order, chunk_block, unresolved = {}, [], {}, []
    for i, rec in enumerate(recs):
        hint = rec['filePath'] if rec['filePath'] in valid_paths else None
        if hint is None and rec['filePath']:
            base = os.path.basename(rec['filePath'])
            cand = [p for p in valid_paths if os.path.basename(p) == base]
            hint = cand[0] if len(cand) == 1 else None

        res = None
        # ① 노트가 경로+심볼을 다 준 경우 — AST 로 바로 확정
        if hint and rec['symbol']:
            name = rec['symbol'].split('.')[-1]
            parent = rec['symbol'].split('.')[-2] if '.' in rec['symbol'] else None
            hits = [s for s in repo.files[hint]['symbols'] if s[0] == name
                    and (parent is None or s[2] == parent)]
            if len(hits) == 1:
                s = hits[0]
                res = (hint, s[0], s[1], s[2], s[3], s[4], 99)
            elif len(hits) > 1 and rec['code']:
                # 동명 심볼이면 노트 코드로 어느 쪽인지 가린다 (문제 6)
                got = repo.locate(rec['code'], hint_path=hint)
                if got and got[1] == name:
                    res = got
        # ② 코드 본문 역매칭 (문제 1·2)
        if res is None and rec['code']:
            res = repo.locate(rec['code'], hint_path=hint) or repo.locate(rec['code'])

        if res is None:
            if not rec['code']:
                why = '노트에 대응 코드가 없음'
            elif 'EXPECTED' in (rec['kind'] or '') or '예상' in (rec['kind'] or ''):
                why = '노트가 (예상코드)로 표시한 블록 — 저장소에 실제로 없는 코드'
            else:
                why = (f'코드 본문을 {repo_info["slug"]}@{repo_info["sha"][:7]} 에서 찾지 못함 '
                       f'(노트 코드가 축약·재작성된 것으로 보임)')
            unresolved.append({'chunk': rec['tag'], 'title': rec['title'], 'issue': why})
            continue

        path, name, kind, parent, st, en, _ = res
        bkey = (path, name, st)
        if bkey not in blocks:
            blocks[bkey] = {
                'filePath': path, 'symbolName': name,
                'symbolType': kind if kind in TYPE_OK else 'MODULE',
                'parentSymbolName': parent, 'programmingLanguage': repo.lang(path),
                'startLine': st, 'endLine': en, 'codeContent': repo.slice(path, st, en),
                '_comment': (f'Verbatim from https://github.com/{repo_info["slug"]} '
                             f'@ {repo_info["sha"][:7]} — {path}:{st}-{en}'),
            }
            order.append(bkey)
        chunk_block[i] = bkey

    # 부모–자식 겹침 제거 (자식 우선, 정답 재지정) — §4 입도 규칙 3
    drop = set()
    for a in order:
        for b in order:
            if a != b and blocks[a]['filePath'] == blocks[b]['filePath'] \
               and blocks[a]['startLine'] <= blocks[b]['startLine'] \
               and blocks[a]['endLine'] >= blocks[b]['endLine']:
                drop.add(a)
    for i, bk in list(chunk_block.items()):
        if bk in drop:
            kids = [k for k in order if k not in drop
                    and blocks[k]['filePath'] == blocks[bk]['filePath']
                    and blocks[bk]['startLine'] <= blocks[k]['startLine']
                    and blocks[bk]['endLine'] >= blocks[k]['endLine']]
            if kids:
                chunk_block[i] = min(kids, key=lambda k: blocks[k]['endLine'] - blocks[k]['startLine'])
            else:
                chunk_block.pop(i)
    if drop:
        unresolved.append({'chunk': '-', 'title': '입도 정리 (§4 규칙 3)',
                           'issue': f'부모 블록 {len(drop)}개를 자식 심볼로 대체: '
                                    f'{sorted(blocks[k]["symbolName"] for k in drop)}'})
    order = [k for k in order if k not in drop]
    return recs, [blocks[k] for k in order], {i: blocks[k] for i, k in chunk_block.items()}, unresolved


def make_doc(key):
    arxiv, fmt, out_name, repo_info = PAPERS[key]
    meta = META[arxiv]
    recs, blocks, chunk_block, unresolved = resolve_all(key, repo_info)

    chunks = []
    for i, rec in enumerate(recs):
        body = '\n\n'.join(rec['paper']) if rec['paper'] else ''
        note = f'노트 {rec["tag"]}'
        if rec['kind']:
            note += f' / 판정 {rec["kind"]}'
        if not body:
            body = (rec['meaning'] or rec['title'] or rec['tag'])[:800]
            note += ' / content=구현 설명 (노트에 논문 인용 없음)'
            unresolved.append({'chunk': rec['tag'], 'title': rec['title'],
                               'issue': '노트에 논문 원문 인용이 없어 구현 설명을 content 로 사용'})
        c = {'chunkIndex': i,
             'sectionTitle': (rec['section'] or rec['title'] or rec['tag'])[:255],
             'subsectionTitle': (rec['title'] or rec['tag'])[:255],
             'content': body, 'pageStart': rec['page'][0], 'pageEnd': rec['page'][1],
             '_comment': note}
        b = chunk_block.get(i)
        if b:
            c['mappedCode'] = [{
                'githubUrl': f'https://github.com/{repo_info["slug"]}',
                'filePath': b['filePath'], 'symbolName': b['symbolName'],
                'startLine': b['startLine'],
                'reason': re.sub(r'\s+', ' ', (rec['match'] or rec['meaning'] or ''))[:400]
                          or f'{b["filePath"]}:{b["startLine"]} 의 {b["symbolName"]} 이 이 단락의 구현',
            }]
        chunks.append(c)

    owner, name = repo_info['slug'].split('/')
    return {
        '_comment': ('노트 마크다운에서 생성. content 는 노트가 인용한 논문 원문, '
                     'codeContent 는 저장소 원문에서 잘라온 것(줄 번호는 AST·블록 파서 실측). '
                     '노트에 경로·심볼이 없는 경우 코드 본문을 저장소에 역매칭해 특정했습니다.'),
        '_sourceMarkdown': md_of(key),
        '_unresolved': unresolved,
        'papers': [{
            'arxivId': arxiv, 'title': meta['title'], 'abstract': meta['abstract'],
            'pdfUrl': f'https://arxiv.org/pdf/{arxiv}', 'publishedDate': meta['publishedDate'],
            'authors': meta['authors'], 'chunks': chunks,
            'repositories': [{
                'githubUrl': f'https://github.com/{repo_info["slug"]}',
                'ownerName': owner, 'repositoryName': name, 'defaultBranch': repo_info['branch'],
                'commitHash': repo_info['sha'], 'licenseName': repo_info['license'],
                'primaryLanguage': (blocks[0]['programmingLanguage'] if blocks else None),
                'starCount': repo_info['stars'], 'relationType': repo_info['relation'],
                'isPrimary': True, 'codeBlocks': blocks,
            }],
        }],
    }, out_name


def main():
    print(f'{"논문":10}{"chunk":>7}{"블록":>6}{"매핑":>6}{"미해결":>7}')
    tot = collections.Counter()
    for key in PAPERS:
        doc, out_name = make_doc(key)
        p = doc['papers'][0]
        with open(os.path.join(ING, out_name + '_ingest.json'), 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
            f.write('\n')
        mapped = sum(1 for c in p['chunks'] if c.get('mappedCode'))
        nb = len(p['repositories'][0]['codeBlocks'])
        tot['chunk'] += len(p['chunks'])
        tot['block'] += nb
        tot['map'] += mapped
        print(f'{key:10}{len(p["chunks"]):7}{nb:6}{mapped:6}{len(doc["_unresolved"]):7}')
    print(f'{"합계":10}{tot["chunk"]:7}{tot["block"]:6}{tot["map"]:6}')


if __name__ == '__main__':
    main()
