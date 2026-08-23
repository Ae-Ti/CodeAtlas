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
            language="python"
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
