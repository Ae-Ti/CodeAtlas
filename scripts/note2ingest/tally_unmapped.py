#!/usr/bin/env python3
"""매핑하지 않은 단락 61건을 사유별로 집계합니다 (결과보고서 §2.4).

"약 54 / 약 7" 같은 어림수를 제출 문서에 남기면 그 숫자만 공격받습니다. 그래서
61건을 하나씩 판정하고, 판정 근거를 이 파일에 적어 재현 가능하게 만듭니다.

판정 기준 — **왜 코드가 안 붙었는가**로 나눕니다.

  A 저장소가 그 구현을 배포하지 않음
      논문은 구현 요소로 서술했지만 인용 저장소에 그 코드가 없습니다.
      예) llama3·segment-anything 은 추론 코드만 배포 — 학습·loss·데이터 파이프라인 없음
          deep-residual-networks 는 ResNet-101 **deploy** prototxt 한 개뿐 —
          solver·CIFAR·detection 이 전부 없음
  B 코드로 표현되는 대상이 아님
      실험 결과·벤치마크 수치, Figure/Table, Reference 항목, 타 시스템 설명,
      하드웨어·일정 사실, 결론.
  C 저장소에는 있으나 인덱싱 범위 밖
      코드가 존재하지만 이번 큐레이션에서 블록으로 뽑지 않았습니다.
  D 대응이 느슨해 큐레이터가 정답셋에 넣지 않음
      후보 심볼은 있으나 "이 단락의 구현"이라 단정하기 어려워 비워 둔 것.

A·C·D 의 구분이 중요합니다 — A 는 데이터의 한계가 아니라 **공개된 구현의 한계**이고,
C·D 는 우리 쪽에서 더 할 수 있었던 부분입니다.

    python3 scripts/note2ingest/tally_unmapped.py
    python3 scripts/note2ingest/tally_unmapped.py --list      # 61건 전체를 판정과 함께
"""
import argparse
import collections
import subprocess
import sys

#: (arxiv_id, chunk_index) → 판정. 61건 전부를 명시합니다 — 규칙 추론이 아니라 개별 판정입니다.
VERDICT = {
    # ── Attention (jadore801120: 모델·train.py·Optim·Translator 인덱싱됨)
    ('1706.03762', 2): 'B',   # BLEU 결과 수치
    ('1706.03762', 32): 'B',  # self-attention·RNN·conv 복잡도 비교표
    ('1706.03762', 36): 'B',  # 8개 P100 GPU — 하드웨어 사실
    ('1706.03762', 37): 'B',  # 학습 스텝 수 — 실행 인자이지 코드가 아님
    ('1706.03762', 45): 'A',  # checkpoint 평균 — 저장소에 averaging 구현 없음
    ('1706.03762', 49): 'D',  # Base model 하이퍼파라미터 — Transformer.__init__ 인자로 느슨히 대응
    ('1706.03762', 50): 'D',  # Big Transformer 설정 — 같음
    ('1706.03762', 51): 'A',  # learned positional embedding — 저장소는 sinusoid 만 구현
    ('1706.03762', 52): 'B',  # 구문 분석 과제 결과
    ('1706.03762', 53): 'D',  # beam size 21·α=0.3 — Translator 는 있으나 그 값은 인자
    ('1706.03762', 59): 'B',  # attention 가중치 시각화 (Figure)
    # ── Latent Diffusion
    ('2112.10752', 28): 'B',  # 실험 절
    # ── Llama 3 (추론 코드만 배포 — generation/model/tokenizer 3파일)
    ('2407.21783', 15): 'A',
    ('2407.21783', 16): 'A',
    ('2407.21783', 17): 'A',
    ('2407.21783', 18): 'A',
    ('2407.21783', 19): 'B',  # 벤치마크 결과
    # ── Segment Anything (추론 전용 — 인코더·디코더·predictor 만)
    ('2304.02643', 24): 'A',  # Loss Function
    ('2304.02643', 25): 'A',  # SA-1B Dataset
    ('2304.02643', 26): 'A',  # Data Engine
    ('2304.02643', 27): 'B',  # 실험 절
    # ── ResNet (deep-residual-networks: ResNet-101-deploy.prototxt 한 개뿐)
    ('1512.03385', 3): 'B',   # ILSVRC·COCO 결과
    ('1512.03385', 4): 'B',   # Figure 1
    ('1512.03385', 29): 'B',  # "dropout 을 쓰지 않았다" — 부재 서술
    ('1512.03385', 30): 'A',  # 10-crop testing — deploy prototxt 에 테스트 코드 없음
    ('1512.03385', 31): 'A',  # multi-scale testing — 같음
    ('1512.03385', 39): 'A',  # CIFAR-10 구조 — 저장소에 CIFAR 정의 없음
    ('1512.03385', 40): 'A',  # CIFAR 학습 설정 — solver 없음
    ('1512.03385', 41): 'A',  # CIFAR data augmentation — 없음
    ('1512.03385', 42): 'A',  # 110층 warm-up — solver 없음
    ('1512.03385', 43): 'B',  # layer response 분석 결과
    ('1512.03385', 44): 'B',  # 1202층 실험 결과
    ('1512.03385', 45): 'A',  # detection 백본 사용 — 저장소에 detection 없음
    ('1512.03385', 46): 'B',  # Reference 항목
    ('1512.03385', 48): 'B',  # Reference 항목
    ('1512.03385', 53): 'A',  # COCO detection 학습 설정
    ('1512.03385', 54): 'A',  # box refinement
    ('1512.03385', 56): 'A',  # global context feature
    ('1512.03385', 57): 'A',  # detection multi-scale testing
    ('1512.03385', 58): 'A',  # region proposal·분류기 앙상블
    ('1512.03385', 59): 'A',  # ImageNet detection 200 classes
    ('1512.03385', 62): 'A',  # fully convolutional localization
    ('1512.03385', 63): 'A',  # R-CNN 상위 200 proposal
    # ── YOLO (darknet: cfg + C 함수 일부 인덱싱)
    ('1506.02640', 5): 'B',   # 45 FPS 수치
    ('1506.02640', 7): 'B',   # 전체 이미지 문맥 — 개념 서술
    ('1506.02640', 8): 'B',   # sliding-window·R-CNN 설명 (타 시스템)
    ('1506.02640', 43): 'C',  # VOC 학습 데이터 — darknet 에 cfg/data 있으나 미인덱싱
    ('1506.02640', 55): 'B',  # small object 한계
    ('1506.02640', 56): 'B',  # DPM 비교
    ('1506.02640', 57): 'B',  # proposal 수 비교
    ('1506.02640', 58): 'B',  # general-purpose detector 주장
    ('1506.02640', 59): 'B',  # Table 1
    ('1506.02640', 60): 'B',  # Error Analysis 기준
    ('1506.02640', 61): 'B',  # Fast R-CNN 재점수화 실험
    ('1506.02640', 62): 'B',  # VOC 2012 mAP
    ('1506.02640', 63): 'B',  # small object 성능
    ('1506.02640', 64): 'B',  # artwork 일반화
    ('1506.02640', 65): 'B',  # Figure 5
    ('1506.02640', 66): 'C',  # webcam 실시간 — darknet examples/demo.c 존재, 미인덱싱
    ('1506.02640', 67): 'B',  # tracking 처럼 동작 — 동작 서술
    ('1506.02640', 68): 'B',  # 결론
}

LABEL = {
    'A': '저장소가 그 구현을 배포하지 않음',
    'B': '코드로 표현되는 대상이 아님',
    'C': '저장소엔 있으나 인덱싱 범위 밖',
    'D': '대응이 느슨해 정답셋에 넣지 않음',
}

SQL = """
WITH man AS (SELECT DISTINCT paper_chunk_id FROM paper_code_mappings WHERE mapping_method='MANUAL')
SELECT p.arxiv_id || E'\\t' || c.chunk_index || E'\\t' || coalesce(c.subsection_title, c.section_title, '')
FROM paper_chunks c JOIN papers p ON p.id = c.paper_id
WHERE c.id NOT IN (SELECT paper_chunk_id FROM man)
ORDER BY p.id, c.chunk_index
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true', help='61건 전체를 판정과 함께 출력')
    ap.add_argument('--container', default='codeatlas-postgres')
    args = ap.parse_args()

    r = subprocess.run(['docker', 'exec', args.container, 'psql', '-U', 'codeatlas',
                        '-d', 'codeatlas', '-tAc', SQL], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'DB 조회 실패:\n{r.stderr}')
    rows = [l.split('\t') for l in r.stdout.splitlines() if l.strip()]

    cnt = collections.Counter()
    per_paper = collections.defaultdict(collections.Counter)
    missing = []
    for aid, idx, title in rows:
        v = VERDICT.get((aid, int(idx)))
        if v is None:
            missing.append((aid, idx, title))
            continue
        cnt[v] += 1
        per_paper[aid][v] += 1
        if args.list:
            print(f'  [{v}] {aid} #{idx:<3} {title[:60]}')

    if args.list:
        print()
    print(f'미매핑 단락 {len(rows)}건')
    for k in 'ABCD':
        print(f'  {k}  {LABEL[k]:<28} {cnt[k]:3}건 ({100 * cnt[k] / len(rows):.1f}%)')
    if missing:
        print(f'\n⚠️ 판정이 없는 단락 {len(missing)}건 — VERDICT 에 추가하세요:')
        for m in missing:
            print(f'   {m[0]} #{m[1]}  {m[2][:60]}')
        sys.exit(1)

    print('\n논문별:')
    for aid, c in per_paper.items():
        print('  %-12s %s' % (aid, '  '.join(f'{k}{c[k]}' for k in 'ABCD' if c[k])))


if __name__ == '__main__':
    main()
