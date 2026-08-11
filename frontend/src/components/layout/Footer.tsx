/**
 * 제3자 코드 라이선스 고지.
 *
 * CodeAtlas는 논문 단락 옆에 실제 저장소 코드를 그대로 인용해 보여줍니다.
 * Meta Llama 3 Community License §1.b.i(B)는 Llama Materials(추론 코드 포함)를
 * 배포·사용하는 제품의 UI에 "Built with Meta Llama 3" 표시를 요구하므로
 * 여기서 상시 노출합니다. 나머지 저장소 고지는 THIRD_PARTY_LICENSES.md 에 있습니다.
 */
const NOTICE_URL =
  'https://github.com/Ae-Ti/CodeAtlas/blob/main/database/THIRD_PARTY_LICENSES.md';

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <span className="footer-attr">Built with Meta Llama 3</span>
        <span className="footer-sep">·</span>
        <span>
          코드 인용 출처와 라이선스는{' '}
          <a href={NOTICE_URL} target="_blank" rel="noreferrer noopener">
            제3자 라이선스 고지
          </a>
          를 참고하세요.
        </span>
      </div>
    </footer>
  );
}
