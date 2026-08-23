import { useState, useEffect } from 'react';
import { Sparkles, Send, Clock, CheckCircle2, Loader2, Database, Filter, MessageSquare, AlertCircle, Code2, Zap, FileCode } from 'lucide-react';
import { api, symbolLabel, ApiError, type AgentQueryResponse, type CodeCandidate, type NlSqlResult, type ToolTiming } from '../api/client';
import { useAnimateNumber } from '../hooks/useAnimateNumber';
import { ErrorBox } from '../components/AsyncStates';
import CodeViewerModal from '../components/CodeViewerModal';

const exampleQueries = [
  'multi-head attention은 코드로 어떻게 구현됐어?',
  'scaled dot-product attention 구현 위치',
  'residual connection이 코드 어디에 있어?',
];

const exampleSqlQueries = [
  'star 수 상위 3개 repository 알려줘',
  '2020년 이후 발표된 논문 목록',
  '논문별로 연결된 repository 개수',
];

function McpToolCard({ tool, delay }: { tool: ToolTiming; delay: number }) {
  const [status, setStatus] = useState<'pending' | 'running' | 'done'>('pending');

  useEffect(() => {
    const t1 = setTimeout(() => setStatus('running'), delay);
    // 실제 측정된 latencyMs를 그대로 재생하되, 너무 길면 데모가 멈춰 보이므로 상한을 둔다
    const t2 = setTimeout(() => setStatus('done'), delay + Math.min(tool.latencyMs, 1500));
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [tool, delay]);

  const statusIcon = {
    pending: <Clock size={16} />,
    running: <Loader2 size={16} className="spinning" />,
    done: tool.status === 'empty' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />,
  };

  return (
    <div className="glass-card mcp-tool-card animate-fade-in-up" style={{ animationDelay: `${delay}ms`, opacity: 0 }}>
      <div className={`tool-status-icon ${status === 'done' && tool.status === 'empty' ? 'pending' : status}`}>
        {statusIcon[status]}
      </div>
      <div className="tool-info">
        <div className="tool-name">{tool.toolName}</div>
        <div className="tool-latency">
          {status === 'done'
            ? `${tool.latencyMs}ms${tool.status === 'empty' ? ' · 결과 없음' : ''}`
            : status === 'running' ? 'Processing...' : 'Waiting...'}
        </div>
      </div>
    </div>
  );
}

function TaccFunnel({ initial, removed, selected }: { initial: number; removed: number; selected: number }) {
  const animInitial = useAnimateNumber(initial, { duration: 800, delay: 400 });
  const animRemoved = useAnimateNumber(removed, { duration: 800, delay: 600 });
  const animSelected = useAnimateNumber(selected, { duration: 800, delay: 800 });

  const maxHeight = 160;
  // initial이 0이면 0으로 나누게 되므로 방어
  const ratio = (n: number) => (initial > 0 ? maxHeight * (n / initial) : 0);

  return (
    <div className="tacc-funnel">
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: maxHeight, background: 'var(--gradient-primary)' }} />
        <div className="tacc-value" style={{ color: 'var(--primary-light)' }}>{animInitial}</div>
        <div className="tacc-label">Initial<br />Contexts</div>
      </div>
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: ratio(removed), background: 'linear-gradient(135deg, var(--error), var(--warning))' }} />
        <div className="tacc-value" style={{ color: 'var(--warning)' }}>-{animRemoved}</div>
        <div className="tacc-label">Removed</div>
      </div>
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: ratio(selected), background: 'var(--gradient-success)' }} />
        <div className="tacc-value" style={{ color: 'var(--success-light)' }}>{animSelected}</div>
        <div className="tacc-label">Selected<br />Contexts</div>
      </div>
    </div>
  );
}

function Nl2SqlPanel() {
  const [sqlQuery, setSqlQuery] = useState('');
  const [result, setResult] = useState<NlSqlResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (q?: string) => {
    const text = (q ?? sqlQuery).trim();
    if (!text) return;
    setSqlQuery(text);
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.nl2sql(text));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="agent-section-title">
        <Database size={14} /> NL2SQL — metadata 자연어 질의
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          className="input"
          placeholder="논문/repository metadata에 대해 물어보세요..."
          value={sqlQuery}
          onChange={e => setSqlQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
        />
        <button className="btn btn-ghost" onClick={() => run()} disabled={loading} style={{ flexShrink: 0 }}>
          {loading ? <Loader2 size={16} className="spinning" /> : <Send size={16} />}
        </button>
      </div>
      {loading && (
        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.78rem', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Loader2 size={12} className="spinning" />
          Qwen3가 SQL을 생성해 실행하는 중입니다 — 보통 10~30초, 길면 1분 걸립니다.
        </p>
      )}
      <div className="query-examples" style={{ marginBottom: 12 }}>
        {exampleSqlQueries.map(q => (
          <button key={q} className="query-example-btn" onClick={() => run(q)}>{q}</button>
        ))}
      </div>

      {error && <ErrorBox error={error} />}

      {result && (
        <div className="glass-card nl2sql-card">
          {!result.isReadOnly && (
            <div style={{ color: 'var(--warning)', fontSize: '0.8rem', marginBottom: 8, display: 'flex', gap: 6 }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              SELECT 외 쿼리가 생성되어 서버가 실행을 거부했습니다 (read-only 가드).
            </div>
          )}
          <div className="sql-code">{result.generatedSql}</div>
          {result.rows.length > 0 ? (
            <table>
              <thead>
                <tr>{result.columns.map(c => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i}>
                    {result.columns.map(c => (
                      <td key={c}>{typeof row[c] === 'number' ? (row[c] as number).toLocaleString() : String(row[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{ color: 'var(--text-tertiary)', fontSize: '0.82rem', marginTop: 8 }}>
              결과가 없습니다. (생성된 SQL은 위에 그대로 표시됩니다)
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function Agent() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<AgentQueryResponse | null>(null);
  const [searchLatency, setSearchLatency] = useState(0);
  const [matchedScore, setMatchedScore] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState(0);
  const [viewingCode, setViewingCode] = useState<CodeCandidate | null>(null);

  const handleSubmit = async (q?: string) => {
    const queryText = (q ?? query).trim();
    if (!queryText) return;

    setQuery(queryText);
    setIsLoading(true);
    setError(null);
    setResult(null);
    // MCP tool 카드가 매번 pending → running → done 애니메이션을 다시 재생하도록 remount
    setRunId(id => id + 1);

    try {
      // 1) SearchPaperChunk — 자연어 질문에서 가장 가까운 논문 chunk를 찾는다
      const t0 = performance.now();
      const chunks = await api.searchChunks(queryText, 1);
      const elapsed = Math.round(performance.now() - t0);

      if (chunks.length === 0) {
        setError('질문과 매칭되는 논문 chunk를 찾지 못했습니다. 논문 데이터와 임베딩이 적재됐는지 확인하세요.');
        return;
      }
      setSearchLatency(elapsed);
      setMatchedScore(chunks[0].score);

      // 2) 찾은 chunk로 agent 질의 — 사전계산돼 있으면 즉시, 아니면 Qwen3 호출
      setResult(await api.agentQuery(queryText, chunks[0].paperId, chunks[0].chunkId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  };

  // 실제로 실행된 도구 목록 = 우리가 부른 SearchPaperChunk + 백엔드가 보고한 단계들
  const tools: ToolTiming[] = result
    ? [{ toolName: 'SearchPaperChunk', status: 'done', latencyMs: searchLatency }, ...result.mcpTools]
    : [];

  const tacc = result?.tacc;
  const hasFunnelNumbers = tacc?.initialContexts != null && tacc?.removedContexts != null;

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">
            <Sparkles size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            AI Agent 시연
          </h1>
          <p className="page-subtitle">
            질문 → SearchPaperChunk로 관련 논문 섹션을 찾고 → 대응 코드와 선택 근거를 보여줍니다
          </p>
        </div>

        {/* Query Input */}
        <div className="agent-query-section">
          <div style={{ display: 'flex', gap: 12 }}>
            <input
              className="input"
              placeholder="논문과 코드에 대해 질문해보세요..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              style={{ fontSize: '1rem', padding: '14px 18px' }}
            />
            <button className="btn btn-primary" onClick={() => handleSubmit()} disabled={isLoading} style={{ flexShrink: 0, padding: '14px 24px' }}>
              {isLoading ? <Loader2 size={18} className="spinning" /> : <Send size={18} />}
              질의
            </button>
          </div>
          <div className="query-examples">
            {exampleQueries.map(eq => (
              <button key={eq} className="query-example-btn" onClick={() => handleSubmit(eq)}>
                {eq}
              </button>
            ))}
          </div>
        </div>

        {error && <div style={{ marginBottom: 24 }}><ErrorBox error={error} /></div>}

        {result && (
          <>
            {/* 어떤 chunk가 선택됐는지 먼저 보여준다 — 결과 해석의 전제 */}
            <div className="glass-card" style={{ padding: 20, marginBottom: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>매칭된 논문 섹션</span>
                <span style={{ fontWeight: 700, color: 'var(--accent-light)' }}>
                  {result.queryChunk.sectionTitle ?? '(제목 없음)'}
                </span>
                <span className="badge" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--primary-light)' }}>
                  유사도 {matchedScore.toFixed(3)}
                </span>
                <span
                  className="badge"
                  title={result.source === 'precomputed'
                    ? '큐레이션 배치가 미리 계산해둔 결과 — 이 요청에서 Ollama를 호출하지 않았습니다'
                    : '사전계산 결과가 없어 이 요청에서 Qwen3를 직접 호출했습니다'}
                  style={{
                    marginLeft: 'auto',
                    background: result.source === 'precomputed' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                    color: result.source === 'precomputed' ? 'var(--success-light)' : 'var(--warning)',
                  }}
                >
                  {result.source === 'precomputed' ? <><Zap size={10} style={{ marginRight: 4 }} />precomputed</> : 'live'}
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: 1.6 }}>
                {result.queryChunk.chunkText}
              </p>
            </div>

            <div className="agent-results">
              {/* Left Column */}
              <div>
                <div style={{ marginBottom: 32 }}>
                  <div className="agent-section-title">
                    <Sparkles size={14} /> MCP Tool Execution
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {tools.map((tool, i) => (
                      <McpToolCard key={`${runId}-${tool.toolName}-${i}`} tool={tool} delay={i * 300} />
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: 32 }}>
                  <div className="agent-section-title">
                    <Filter size={14} /> TACC Context Selection
                  </div>
                  <div className="glass-card" style={{ padding: hasFunnelNumbers ? 8 : 20 }}>
                    {hasFunnelNumbers ? (
                      <TaccFunnel
                        initial={tacc!.initialContexts!}
                        removed={tacc!.removedContexts!}
                        selected={tacc!.selectedContexts}
                      />
                    ) : (
                      <div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--success-light)', marginBottom: 6 }}>
                          {result.mappingReason ?? `선택된 context ${tacc?.selectedContexts ?? 0}개`}
                        </div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', lineHeight: 1.6 }}>
                          사전계산된 결과라 배치 시점의 후보/제외 개수는 DB에 저장돼 있지 않습니다.
                          정확한 수치는 위 요약 문장으로 제공됩니다.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <Nl2SqlPanel />
              </div>

              {/* Right Column */}
              <div>
                <div className="agent-section-title">
                  <MessageSquare size={14} /> AI Response — 1위 매칭 근거
                </div>
                <div className="glass-card ai-response" style={{ marginBottom: 8 }}>
                  {result.results[0] && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8, fontFamily: 'var(--font-mono)' }}>
                      {result.results[0].repositoryName} / {symbolLabel(result.results[0])}
                    </div>
                  )}
                  {result.explanation}
                </div>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
                  Qwen3는 1위 코드에 대해서만 근거를 생성합니다. 2위 이하는 pgvector 유사도 순위입니다.
                </p>

                <div className="agent-section-title">
                  <Code2 size={14} /> Selected Code ({result.results.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {result.results.map((code, i) => (
                    <div
                      key={code.codeBlockId}
                      className="glass-card"
                      style={{ padding: 16, cursor: 'pointer' }}
                      onClick={() => setViewingCode(code)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <FileCode size={12} color="var(--success-light)" />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--success-light)', fontWeight: 600 }}>
                          {symbolLabel(code)}
                        </span>
                        {i === 0 && (
                          <span className="badge" style={{ background: 'rgba(139,92,246,0.15)', color: 'var(--accent-light)', fontSize: '0.62rem' }}>
                            AI 근거 대상
                          </span>
                        )}
                        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', fontWeight: 700 }}>
                          {code.similarityScore.toFixed(2)}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                        <span>{code.repositoryName} / {code.filePath}</span>
                        <span style={{ marginLeft: 'auto', color: 'var(--primary-light)', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Code2 size={11} /> 코드 보기
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {!result && !isLoading && !error && (
          <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-tertiary)' }}>
            <Sparkles size={56} style={{ marginBottom: 16, opacity: 0.2 }} />
            <p style={{ fontSize: '1.05rem' }}>위의 예시 질문을 클릭하거나 직접 질문을 입력해보세요</p>
          </div>
        )}

        {isLoading && (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <Loader2 size={40} className="spinning" style={{ color: 'var(--primary)', marginBottom: 16 }} />
            <p style={{ color: 'var(--text-secondary)' }}>MCP Agent가 분석 중입니다...</p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: 8 }}>
              사전계산되지 않은 chunk면 Qwen3를 지금 호출하므로 수십 초 걸릴 수 있습니다.
            </p>
          </div>
        )}
      </div>

      {viewingCode && <CodeViewerModal code={viewingCode} onClose={() => setViewingCode(null)} />}

      <style>{`
        .spinning {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
