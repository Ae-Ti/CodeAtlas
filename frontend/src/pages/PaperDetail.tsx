import { useState, useMemo, useCallback, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BookOpen, Code2, ExternalLink, X, FileCode, Sparkles, Zap } from 'lucide-react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { api, symbolLabel, type CodeMatch, type AgentQueryResponse } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Loading, ErrorBox, EmptyState } from '../components/AsyncStates';

// Deterministic "keyword overlap" so the similarity score is explainable
// (vector similarity vs. how many chunk keywords also appear in the code).
function computeKeywordOverlap(chunkText: string, code: CodeMatch): number {
  const stopWords = new Set(['that', 'this', 'with', 'from', 'into', 'were', 'have', 'each', 'they', 'their']);
  const chunkWords = Array.from(new Set(
    chunkText.toLowerCase().match(/[a-z]{4,}/g)?.filter(w => !stopWords.has(w)) ?? []
  ));
  if (chunkWords.length === 0) return 0;
  const corpus = `${code.codeContent} ${code.filePath} ${code.symbolName ?? ''} ${code.parentSymbolName ?? ''}`.toLowerCase();
  const matches = chunkWords.filter(w => corpus.includes(w)).length;
  return Math.min(1, matches / chunkWords.length);
}

/** 선택된 chunk의 AI 근거. 사전계산돼 있으면 즉시, 아니면 그 자리에서 Qwen3를 부른다. */
function AiExplanation({ paperId, chunkId }: { paperId: number; chunkId: number }) {
  const [state, setState] = useState<{ data: AgentQueryResponse | null; loading: boolean; error: string | null }>(
    { data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    setState({ data: null, loading: true, error: null });
    api.agentQuery('이 섹션은 코드로 어떻게 구현됐어?', paperId, chunkId)
      .then(d => { if (!cancelled) setState({ data: d, loading: false, error: null }); })
      .catch((e: Error) => { if (!cancelled) setState({ data: null, loading: false, error: e.message }); });
    return () => { cancelled = true; };
  }, [paperId, chunkId]);

  if (state.loading) {
    return (
      <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
        <div className="agent-section-title" style={{ marginBottom: 8 }}>
          <Sparkles size={14} /> 1위 매칭 근거
        </div>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.85rem' }}>
          생성 중… 사전계산되지 않은 chunk면 Qwen3를 지금 호출하므로 수십 초 걸릴 수 있습니다.
        </p>
      </div>
    );
  }
  if (state.error || !state.data) return null;

  const { explanation, source, mappingReason, tacc, results } = state.data;
  const isPrecomputed = source === 'precomputed';
  const topCode = results[0];

  return (
    <div className="glass-card" style={{ padding: 20, marginBottom: 16 }}>
      <div className="agent-section-title" style={{ marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Sparkles size={14} /> 1위 매칭 근거
        <span
          className="badge"
          title={isPrecomputed
            ? '큐레이션 배치가 미리 계산해둔 결과 — Ollama를 호출하지 않았습니다'
            : '사전계산 결과가 없어 이 요청에서 Qwen3를 직접 호출했습니다'}
          style={{
            marginLeft: 'auto',
            background: isPrecomputed ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
            color: isPrecomputed ? 'var(--success-light)' : 'var(--warning)',
          }}
        >
          {isPrecomputed ? <><Zap size={10} style={{ marginRight: 4 }} />precomputed</> : 'live'}
        </span>
      </div>
      {/* 이 설명이 어느 코드에 대한 것인지 명시 — 아래 목록 전체에 대한 평가가 아닙니다 */}
      {topCode && (
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8, fontFamily: 'var(--font-mono)' }}>
          {topCode.repositoryName} / {symbolLabel(topCode)}
        </div>
      )}
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: 1.7 }}>{explanation}</p>
      <div style={{ marginTop: 10, fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        {mappingReason ?? `TACC: 후보 ${tacc.initialContexts} → 선택 ${tacc.selectedContexts}`}
      </div>
      <p style={{ marginTop: 8, fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
        아래 목록의 2위 이하는 pgvector 유사도 순위이며, AI가 따로 판단한 결과가 아닙니다.
      </p>
    </div>
  );
}

export default function PaperDetail() {
  const { paperId: paperIdParam } = useParams<{ paperId: string }>();
  const paperId = Number(paperIdParam);
  const [searchParams] = useSearchParams();

  const papersState = useApi(() => api.papers(), []);
  const chunksState = useApi(() => api.chunks(paperId), [paperId]);

  const paper = papersState.data?.find(p => p.paperId === paperId) ?? null;
  const chunks = useMemo(() => chunksState.data ?? [], [chunksState.data]);

  const [activeChunkId, setActiveChunkId] = useState<number | null>(null);
  const [viewingCode, setViewingCode] = useState<CodeMatch | null>(null);

  // chunk 목록이 도착한 뒤에 초기 선택을 정한다 (?chunkId= 우선, 없으면 첫 chunk)
  useEffect(() => {
    if (!chunks.length) return;
    const requested = Number(searchParams.get('chunkId'));
    const valid = chunks.some(c => c.chunkId === requested);
    setActiveChunkId(valid ? requested : chunks[0].chunkId);
  }, [chunks, searchParams]);

  const activeChunk = useMemo(
    () => chunks.find(c => c.chunkId === activeChunkId) ?? null,
    [chunks, activeChunkId]
  );

  const mappingState = useApi(
    () => activeChunkId
      ? api.mappingSearch(paperId, activeChunkId, 5)
      : Promise.resolve({ queryChunk: null as never, results: [] as CodeMatch[] }),
    [paperId, activeChunkId]
  );
  const codeResults = mappingState.data?.results ?? [];

  const handleCloseModal = useCallback(() => setViewingCode(null), []);
  const handleEditorMount: OnMount = useCallback((editor) => {
    // Monaco can mount before its flex/grid parent has resolved a real
    // height and miscalculate its size as 0 — force a re-layout once mounted.
    requestAnimationFrame(() => editor.layout());
  }, []);

  if (papersState.loading || chunksState.loading) {
    return <div className="page"><div className="container"><Loading message="논문을 불러오는 중..." padding={80} /></div></div>;
  }
  if (papersState.error || chunksState.error) {
    return (
      <div className="page"><div className="container" style={{ paddingTop: 40 }}>
        <ErrorBox error={papersState.error ?? chunksState.error!} onRetry={() => { papersState.reload(); chunksState.reload(); }} />
      </div></div>
    );
  }
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

  const year = paper.publishedDate ? paper.publishedDate.slice(0, 4) : '—';

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
            {paper.authors.join(', ') || '저자 정보 없음'} · {year}
            {paper.arxivId && <> · <span style={{ fontFamily: 'var(--font-mono)' }}>arXiv:{paper.arxivId}</span></>}
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
                    <span className="badge" style={{ background: 'rgba(139,92,246,0.15)', color: 'var(--accent-light)' }}>
                      #{chunk.chunkIndex}
                    </span>
                    {chunk.subsectionTitle && (
                      <span style={{ marginLeft: 6, fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {chunk.subsectionTitle}
                      </span>
                    )}
                  </div>
                  <div className="chunk-section">{chunk.sectionTitle ?? '(제목 없음)'}</div>
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
            {activeChunk && (
              <div className="glass-card active-chunk-panel">
                <div className="active-chunk-title">{activeChunk.sectionTitle ?? '(제목 없음)'}</div>
                <div className="active-chunk-text">{activeChunk.chunkText}</div>
              </div>
            )}

            {activeChunkId && <AiExplanation paperId={paperId} chunkId={activeChunkId} />}

            <div className="agent-section-title">
              <Code2 size={14} /> Code Implementations ({codeResults.length})
            </div>

            {mappingState.loading && <Loading message="코드 검색 중..." padding={32} />}
            {mappingState.error && <ErrorBox error={mappingState.error} onRetry={mappingState.reload} />}

            {!mappingState.loading && !mappingState.error && codeResults.length === 0 && (
              <EmptyState
                icon={<Code2 size={40} />}
                title="이 chunk에 매칭된 코드 구현체가 없습니다."
                hint="code_blocks 임베딩이 채워졌는지 확인하세요 (CODEATLAS_EMBEDDING_BACKFILL=true)."
              />
            )}

            {codeResults.length > 0 && (
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
                          <div className="result-repo">{code.repositoryName}</div>
                          <div className="result-file">
                            {code.filePath}{code.startLine != null ? `:${code.startLine}-${code.endLine}` : ''}
                          </div>
                        </div>
                        <div>
                          <div className="similarity-bar-wrapper" style={{ width: 140 }}>
                            <div className="similarity-bar">
                              <div className="similarity-bar-fill" style={{ '--fill-width': `${code.similarityScore * 100}%` } as React.CSSProperties} />
                            </div>
                            <span className="similarity-score">{code.similarityScore.toFixed(2)}</span>
                          </div>
                          <div className="similarity-breakdown" title="pgvector 코사인 유사도와 chunk-코드 키워드 매칭 비율입니다">
                            벡터 {code.similarityScore.toFixed(2)} · 키워드 {Math.round(keywordOverlap * 100)}%
                          </div>
                        </div>
                      </div>

                      <div className="result-func">
                        <FileCode size={12} />
                        {symbolLabel(code)}
                        <span style={{ marginLeft: 6, fontSize: '0.68rem', color: 'var(--text-muted)' }}>{code.symbolType}</span>
                      </div>

                      <pre className="result-code-preview">
                        {code.codeContent.split('\n').slice(0, 6).join('\n')}{code.codeContent.split('\n').length > 6 ? '\n...' : ''}
                      </pre>

                      <div className="result-actions">
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px 12px', fontSize: '0.75rem' }}
                          onClick={e => { e.stopPropagation(); setViewingCode(code); }}
                        >
                          <FileCode size={12} /> 코드 뷰어 열기
                        </button>
                        {code.githubUrl && (
                          <a href={code.githubUrl} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: '0.75rem' }} onClick={e => e.stopPropagation()}>
                            <ExternalLink size={12} /> GitHub
                          </a>
                        )}
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
                  {symbolLabel(viewingCode)}
                </span>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginLeft: 8 }}>
                  {viewingCode.repositoryName} / {viewingCode.filePath}
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
                value={viewingCode.codeContent}
                onMount={handleEditorMount}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 14,
                  fontFamily: "'JetBrains Mono', monospace",
                  lineNumbers: (n: number) => String(n + (viewingCode.startLine ?? 1) - 1),
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
