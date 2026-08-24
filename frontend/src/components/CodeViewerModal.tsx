import { useCallback } from 'react';
import { X } from 'lucide-react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { symbolLabel } from '../api/client';

/**
 * CodeMatch(라인번호·GitHub URL 있음)와 CodeCandidate(없음)를 모두 받을 수 있는 최소 형태.
 * startLine이 없으면 1부터 표시한다 — 코드 원문은 두 타입 모두 codeContent에 들어 있다.
 */
export interface ViewableCode {
  repositoryName: string;
  filePath: string;
  symbolName: string | null;
  parentSymbolName: string | null;
  codeContent: string;
  startLine?: number | null;
}

/**
 * 코퍼스에 실재하는 확장자만 매핑한다 (py 151 / prototxt 14 / c 9 / cfg 9).
 * 파이썬으로 고정하면 .c 원문에서 #include 가 주석으로 회색 처리되는 식으로
 * 하이라이팅이 조용히 거짓말을 하므로, 모르는 확장자는 plaintext 로 둔다.
 */
function languageOf(filePath: string): string {
  const ext = filePath.slice(filePath.lastIndexOf('.') + 1).toLowerCase();
  switch (ext) {
    case 'py': return 'python';
    case 'c':
    case 'h': return 'c';
    case 'cfg': return 'ini';
    default: return 'plaintext';
  }
}

export default function CodeViewerModal({ code, onClose }: { code: ViewableCode; onClose: () => void }) {
  const handleEditorMount: OnMount = useCallback((editor) => {
    // Monaco can mount before its flex/grid parent has resolved a real
    // height and miscalculate its size as 0 — force a re-layout once mounted.
    requestAnimationFrame(() => editor.layout());
  }, []);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <span style={{ color: 'var(--success-light)', fontFamily: 'var(--font-mono)' }}>
              {symbolLabel(code)}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginLeft: 8 }}>
              {code.repositoryName} / {code.filePath}
            </span>
          </h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="modal-body" style={{ height: 500 }}>
          <Editor
            height={500}
            language={languageOf(code.filePath)}
            theme="vs-dark"
            value={code.codeContent}
            onMount={handleEditorMount}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 14,
              fontFamily: "'JetBrains Mono', monospace",
              lineNumbers: (n: number) => String(n + (code.startLine ?? 1) - 1),
              scrollBeyondLastLine: false,
              padding: { top: 16 },
              renderLineHighlight: 'all',
            }}
          />
        </div>
      </div>
    </div>
  );
}
