# note2ingest — 노트 마크다운 → ingest JSON

`database/ingest/*.md` (Notion 내보내기)를 `scripts/ingest.py`가 받는 JSON으로 바꿉니다.

## 실행 순서

```bash
python3 scripts/note2ingest/build_all.py         # 노트 → ingest JSON 9개
python3 scripts/note2ingest/augment_content.py   # ar5iv 논문 원문으로 content 보강
python3 scripts/note2ingest/add_secondary.py     # 참조 구현 저장소 추가 (ViT/ResNet/U-Net/YOLO)
python3 scripts/note2ingest/add_secondary2.py    # 2차 보강 (BERT/CLIP/SAM/LDM)
python3 scripts/note2ingest/fix_license_unet.py  # 라이선스 실측값 반영
```

## 파일

| 파일 | 역할 |
|---|---|
| `parse_md.py` | 노트 마크다운 2서식 파서 (CHUNK 형식 / 판정 형식) |
| `locate.py` | 코드 본문 → 저장소 위치 역매칭. Python(ast) · C(중괄호) · prototxt · cfg |
| `build_all.py` | 노트 → ingest JSON |
| `augment_content.py` | 논문 원문 문단으로 `content` 보강 |
| `add_secondary.py` / `add_secondary2.py` | 참조 구현 저장소 등록 + 주제별 수동 매핑 |
| `fix_license_unet.py` | LICENSE 실측값 반영, GPL 저장소 교체 |

## 사전 준비

스크립트는 저장소 원문과 논문 HTML을 **로컬 캐시에서 읽습니다.**

```
<스크립트 디렉터리>/src/     <논문키>--<경로에서 / 를 ~ 로 바꾼 이름>
<스크립트 디렉터리>/papers/  <arxivId>.html      (ar5iv)
<스크립트 디렉터리>/trees/   <owner_repo>.json   (GitHub git/trees)
<스크립트 디렉터리>/arxiv_meta.json
```

캐시가 없으면 GitHub raw / ar5iv / arXiv API 에서 다시 받아야 합니다.
`build_all.py` 상단의 `PAPERS` 에 저장소 slug·커밋 SHA 가 고정돼 있어
같은 커밋으로 받으면 결과가 재현됩니다.

## 노트 표준 서식

새 논문은 아래 형태로 작성하면 역매칭 없이 바로 붙습니다.
자세한 내용은 [docs/파일적재_문제점.md](../../docs/파일적재_문제점.md) 문제 4 참고.

```markdown
# CHUNK 01

## 제목
Multi-Head Attention

## 논문 위치
Section 3.2.2
Page 4-5

## 논문 원문
> Multi-head attention allows the model to jointly attend to information ...

## Git 코드
파일: transformer/SubLayers.py
심볼: MultiHeadAttention.forward
```
