import { useState, useMemo, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BookOpen, Code2, ExternalLink, X, FileCode } from 'lucide-react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { mockPapers } from '../data/papers';
import { getChunksByPaperId } from '../data/chunks';
import { getCodeBlocksForChunk, type CodeBlock } from '../data/codeBlocks';

const chunkTypeColors: Record<string, string> = {
  method: 'var(--primary)',
  architecture: 'var(--accent)',
  training: 'var(--warning)',
  evaluation: 'var(--success)',
};

// Deterministic mock "keyword overlap" so the similarity score is explainable
// (vector similarity vs. how many chunk keywords also appear in the code).
function computeKeywordOverlap(chunkText: string, code: CodeBlock): number {
  const stopWords = new Set(['that', 'this', 'with', 'from', 'into', 'were', 'have', 'each', 'they', 'their']);
  const chunkWords = Array.from(new Set(
    chunkText.toLowerCase().match(/[a-z]{4,}/g)?.filter(w => !stopWords.has(w)) ?? []
  ));
  if (chunkWords.length === 0) return 0;
  const codeCorpus = `${code.codeText} ${code.explanation} ${code.functionName} ${code.className ?? ''}`.toLowerCase();
  const matches = chunkWords.filter(w => codeCorpus.includes(w)).length;
  return Math.min(1, matches / chunkWords.length);
}

export default function PaperDetail() {
  const { paperId } = useParams<{ paperId: string }>();
  const [searchParams] = useSearchParams();
  const paper = mockPapers.find(p => p.paperId === Number(paperId));
  const chunks = useMemo(() => getChunksByPaperId(Number(paperId)), [paperId]);

  const chunkIdParam = searchParams.get('chunkId');
  const [activeChunkId, setActiveChunkId] = useState<number | null>(() => {
    const parsed = chunkIdParam ? Number(chunkIdParam) : null;
    if (parsed && chunks.some(c => c.chunkId === parsed)) return parsed;
    return chunks[0]?.chunkId || null;
  });
  const [viewingCode, setViewingCode] = useState<CodeBlock | null>(null);

  const activeChunk = useMemo(
    () => chunks.find(c => c.chunkId === activeChunkId) ?? null,
    [chunks, activeChunkId]
  );

  const codeResults = useMemo(() => {
    if (!activeChunkId) return [];
    return getCodeBlocksForChunk(activeChunkId);
  }, [activeChunkId]);

  // Chunks in this paper that already have code mappings, for the empty-state suggestion.
  const mappedChunks = useMemo(
    () => chunks.filter(c => getCodeBlocksForChunk(c.chunkId).length > 0),
    [chunks]
  );
  const suggestedChunk = mappedChunks.find(c => c.chunkId !== activeChunkId) ?? null;

  const handleCloseModal = useCallback(() => setViewingCode(null), []);
  const handleEditorMount: OnMount = useCallback((editor) => {
    // Monaco can mount before its flex/grid parent has resolved a real
    // height and miscalculate its size as 0 — force a re-layout once mounted.
    requestAnimationFrame(() => editor.layout());
  }, []);

  if (!paper) {
    return (
      <div className="page">
        <div className="container" style={{ textAlign: 'center', paddingTop: 80 }}>
          <p style={{ color: 'var(--text-tertiary)' }}>논문을 찾을 수 없습니다</p>
          <Link to="/papers" className="btn btn-ghost" style={{ marginTop: 16 }}>
            <ArrowLeft size={16} /> 논문 목록으로
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page paper-detail-page">
      <div className="container">
        {/* Back + Title */}
        <div style={{ marginBottom: 28 }}>
          <Link to="/papers" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 12 }}>
            <ArrowLeft size={14} /> 논문 목록
          </Link>
          <h1 className="page-title" style={{ fontSize: '1.6rem' }}>{paper.title}</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            {paper.authors} · {paper.year} · <span className={`badge badge-${paper.task.toLowerCase()}`} style={{ marginLeft: 4 }}>{paper.task}</span>
          </p>
        </div>

        {/* Split View */}
        <div className="split-view">
          {/* Left: Chunks */}
          <div className="split-left">
            <div className="agent-section-title">
              <BookOpen size={14} /> Paper Chunks ({chunks.length})
            </div>
            <div className="chunk-list">
              {chunks.map(chunk => (
                <div
                  key={chunk.chunkId}
                  className={`chunk-item ${activeChunkId === chunk.chunkId ? 'active' : ''}`}
                  onClick={() => setActiveChunkId(chunk.chunkId)}
                >
                  <div className="chunk-type">
                    <span className="badge" style={{
                      background: `${chunkTypeColors[chunk.chunkType]}20`,
                      color: chunkTypeColors[chunk.chunkType],
                    }}>
                      {chunk.chunkType}
                    </span>
                  </div>
                  <div className="chunk-section">{chunk.sectionTitle}</div>
                  <div className="chunk-text">{chunk.chunkText}</div>
                  {activeChunkId !== chunk.chunkId && (
                    <div className="chunk-hint">코드 매칭 보기 <ArrowRight size={10} /></div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right: Code Results */}
          <div className="split-right">
            {/* Full text of the selected chunk — the left list only shows a 2-line preview */}
            {activeChunk && (
              <div className="glass-card active-chunk-panel">
                <div className="active-chunk-title">{activeChunk.sectionTitle}</div>
                <div className="active-chunk-text">{activeChunk.chunkText}</div>
              </div>
            )}

            <div className="agent-section-title">
              <Code2 size={14} /> Code Implementations ({codeResults.length})
            </div>
            {codeResults.length === 0 ? (
              <div className="glass-card" style={{ padding: 48, textAlign: 'center' }}>
                <Code2 size={40} color="var(--text-muted)" style={{ marginBottom: 12 }} />
                <p style={{ color: 'var(--text-tertiary)', marginBottom: 8 }}>
                  이 chunk는 아직 코드 매핑이 진행되지 않았습니다.
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  다른 chunk를 선택하면 매핑된 코드 구현체를 볼 수 있습니다.
                </p>
                {suggestedChunk && (
                  <button
                    className="btn btn-ghost"
                    style={{ marginTop: 20 }}
                    onClick={() => setActiveChunkId(suggestedChunk.chunkId)}
                  >
                    {suggestedChunk.sectionTitle} 보기 <ArrowRight size={14} />
                  </button>
                )}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {codeResults.map((code, i) => {
                  const keywordOverlap = activeChunk ? computeKeywordOverlap(activeChunk.chunkText, code) : 0;
                  return (
                    <div
                      key={code.codeBlockId}
                      className="glass-card code-result-card animate-fade-in-up"
                      style={{ animationDelay: `${i * 80}ms`, opacity: 0 }}
                      onClick={() => setViewingCode(code)}
                    >
                      <div className="result-header">
                        <div>
                          <div className="result-repo">{code.repoName}</div>
                          <div className="result-file">{code.filePath}:{code.startLine}-{code.endLine}</div>
                        </div>
                        <div>
                          <div className="similarity-bar-wrapper" style={{ width: 140 }}>
                            <div className="similarity-bar">
                              <div className="similarity-bar-fill" style={{ '--fill-width': `${code.similarityScore * 100}%` } as React.CSSProperties} />
                            </div>
                            <span className="similarity-score">{code.similarityScore.toFixed(2)}</span>
                          </div>
                          <div className="similarity-breakdown" title="벡터 유사도와 chunk-코드 키워드 매칭 비율의 합성 점수입니다">
                            벡터 {code.similarityScore.toFixed(2)} · 키워드 {Math.round(keywordOverlap * 100)}%
                          </div>
                        </div>
                      </div>

                      <div className="result-func">
                        <FileCode size={12} />
                        {code.className ? `${code.className}.` : ''}{code.functionName}
                      </div>

                      <pre className="result-code-preview">
                        {code.codeText.split('\n').slice(0, 6).join('\n')}{code.codeText.split('\n').length > 6 ? '\n...' : ''}
                      </pre>

                      <div className="result-explanation">{code.explanation}</div>

                      <div className="result-actions">
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                          onClick={e => { e.stopPropagation(); setViewingCode(code); }}
                        >
                          <FileCode size={12} /> 코드 뷰어 열기
                        </button>
                        <a href={code.githubUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: '0.75rem' }} onClick={e => e.stopPropagation()}>
                          <ExternalLink size={12} /> GitHub
                        </a>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Monaco Editor Modal */}
      {viewingCode && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                <span style={{ color: 'var(--success-light)', fontFamily: 'var(--font-mono)' }}>
                  {viewingCode.className ? `${viewingCode.className}.` : ''}{viewingCode.functionName}
                </span>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginLeft: 8 }}>
                  {viewingCode.repoName} / {viewingCode.filePath}
                </span>
              </h3>
              <button className="modal-close" onClick={handleCloseModal}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body" style={{ height: 500 }}>
              <Editor
                height={500}
                language="python"
                theme="vs-dark"
                value={viewingCode.codeText}
                onMount={handleEditorMount}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: "'JetBrains Mono', monospace",
                  lineNumbers: (n: number) => String(n + viewingCode.startLine - 1),
                  scrollBeyondLastLine: false,
                  padding: { top: 16 },
                  renderLineHighlight: 'all',
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
