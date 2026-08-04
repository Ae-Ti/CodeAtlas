import { useState, useEffect, useRef } from 'react';
import { Sparkles, Send, Clock, CheckCircle2, Loader2, Database, Filter, MessageSquare, AlertCircle } from 'lucide-react';
import { mockAgentResponses, exampleQueries, type AgentResponse, type McpTool } from '../data/agentResponses';
import { useAnimateNumber } from '../hooks/useAnimateNumber';
import ReactMarkdown from 'react-markdown';

// Very small keyword-overlap scorer so free-form questions get the closest
// canned mock response instead of always falling back to the first one.
function findBestResponse(queryText: string): { response: AgentResponse; isExactMatch: boolean } {
  if (mockAgentResponses[queryText]) {
    return { response: mockAgentResponses[queryText], isExactMatch: true };
  }
  const queryWords = queryText.toLowerCase().match(/[a-z]{3,}/g) ?? [];
  let best = Object.values(mockAgentResponses)[0];
  let bestScore = -1;
  for (const response of Object.values(mockAgentResponses)) {
    const corpusWords = new Set((response.query + ' ' + response.aiResponse).toLowerCase().match(/[a-z]{3,}/g) ?? []);
    const score = queryWords.filter(w => corpusWords.has(w)).length;
    if (score > bestScore) {
      bestScore = score;
      best = response;
    }
  }
  return { response: best, isExactMatch: false };
}

function McpToolCard({ tool, delay }: { tool: McpTool; delay: number }) {
  const [status, setStatus] = useState<'pending' | 'running' | 'done' | 'error'>('pending');

  useEffect(() => {
    const t1 = setTimeout(() => setStatus('running'), delay);
    const t2 = setTimeout(() => setStatus(tool.status), delay + tool.latencyMs);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [tool, delay]);

  const statusIcon = {
    pending: <Clock size={16} />,
    running: <Loader2 size={16} className="spinning" />,
    done: <CheckCircle2 size={16} />,
    error: <AlertCircle size={16} />,
  };

  return (
    <div className="glass-card mcp-tool-card animate-fade-in-up" style={{ animationDelay: `${delay}ms`, opacity: 0 }}>
      <div className={`tool-status-icon ${status}`}>{statusIcon[status]}</div>
      <div className="tool-info">
        <div className="tool-name">{tool.toolName}</div>
        <div className="tool-latency">
          {status === 'done' ? `${tool.latencyMs}ms` : status === 'running' ? 'Processing...' : 'Waiting...'}
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
  return (
    <div className="tacc-funnel">
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: maxHeight, background: 'var(--gradient-primary)' }} />
        <div className="tacc-value" style={{ color: 'var(--primary-light)' }}>{animInitial}</div>
        <div className="tacc-label">Initial<br />Contexts</div>
      </div>
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: maxHeight * (removed / initial), background: 'linear-gradient(135deg, var(--error), var(--warning))' }} />
        <div className="tacc-value" style={{ color: 'var(--warning)' }}>-{animRemoved}</div>
        <div className="tacc-label">Removed</div>
      </div>
      <div className="tacc-stage">
        <div className="tacc-bar" style={{ height: maxHeight * (selected / initial), background: 'var(--gradient-success)' }} />
        <div className="tacc-value" style={{ color: 'var(--success-light)' }}>{animSelected}</div>
        <div className="tacc-label">Selected<br />Contexts</div>
      </div>
    </div>
  );
}

export default function Agent() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isApproximateMatch, setIsApproximateMatch] = useState(false);
  const [runId, setRunId] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (q?: string) => {
    const queryText = q || query;
    if (!queryText.trim()) return;

    setIsLoading(true);
    setResult(null);
    setQuery(queryText);
    // Forces the MCP tool cards to remount and replay their pending -> running
    // -> done animation every time, even when resubmitting the same query.
    setRunId(id => id + 1);

    // Simulate API delay
    setTimeout(() => {
      const { response, isExactMatch } = findBestResponse(queryText);
      setResult(response);
      setIsApproximateMatch(!isExactMatch);
      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">
            <Sparkles size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            AI Agent 시연
          </h1>
          <p className="page-subtitle">MCP Agent에 질문하면 논문과 코드를 검색하고 분석 결과를 보여줍니다</p>
        </div>

        {/* Query Input */}
        <div className="agent-query-section">
          <div style={{ display: 'flex', gap: 12 }}>
            <input
              ref={inputRef}
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

        {/* Results */}
        {result && (
          <>
            {isApproximateMatch && (
              <div className="agent-mock-notice">
                <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                <span>
                  이 데모는 예시 질문 3개에 한해 정확한 mock 응답을 제공합니다. 입력하신 질문과 가장 가까운 예시 결과를 보여드리고 있어요.
                </span>
              </div>
            )}
            <div className="agent-results">
            {/* Left Column */}
            <div>
              {/* MCP Tools */}
              <div style={{ marginBottom: 32 }}>
                <div className="agent-section-title">
                  <Sparkles size={14} /> MCP Tool Execution
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {result.mcpTools.map((tool, i) => (
                    <McpToolCard key={`${runId}-${tool.toolName}`} tool={tool} delay={i * 300} />
                  ))}
                </div>
              </div>

              {/* TACC */}
              <div style={{ marginBottom: 32 }}>
                <div className="agent-section-title">
                  <Filter size={14} /> TACC Context Selection
                </div>
                <div className="glass-card" style={{ padding: 8 }}>
                  <TaccFunnel
                    initial={result.tacc.initialContexts}
                    removed={result.tacc.removedContexts}
                    selected={result.tacc.selectedContexts}
                  />
                </div>
              </div>

              {/* NL2SQL */}
              {result.nl2sql && (
                <div>
                  <div className="agent-section-title">
                    <Database size={14} /> NL2SQL Result
                  </div>
                  <div className="glass-card nl2sql-card">
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 8 }}>
                      <strong>Natural Query:</strong> {result.nl2sql.naturalQuery}
                    </div>
                    <div className="sql-code">{result.nl2sql.generatedSql}</div>
                    <table>
                      <thead>
                        <tr>
                          {Object.keys(result.nl2sql.results[0] || {}).map(key => (
                            <th key={key}>{key}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.nl2sql.results.map((row, i) => (
                          <tr key={i}>
                            {Object.values(row).map((val, j) => (
                              <td key={j}>{typeof val === 'number' ? val.toLocaleString() : val}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: AI Response */}
            <div>
              <div className="agent-section-title">
                <MessageSquare size={14} /> AI Response
              </div>
              <div className="glass-card ai-response">
                <ReactMarkdown>{result.aiResponse}</ReactMarkdown>
              </div>
            </div>
          </div>
          </>
        )}

        {/* Empty state */}
        {!result && !isLoading && (
          <div style={{ textAlign: 'center', padding: 80, color: 'var(--text-tertiary)' }}>
            <Sparkles size={56} style={{ marginBottom: 16, opacity: 0.2 }} />
            <p style={{ fontSize: '1.05rem' }}>위의 예시 질문을 클릭하거나 직접 질문을 입력해보세요</p>
          </div>
        )}

        {/* Loading state */}
        {isLoading && (
          <div style={{ textAlign: 'center', padding: 80 }}>
            <Loader2 size={40} className="spinning" style={{ color: 'var(--primary)', marginBottom: 16 }} />
            <p style={{ color: 'var(--text-secondary)' }}>MCP Agent가 분석 중입니다...</p>
          </div>
        )}
      </div>

      <style>{`
        .spinning {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  );
}
