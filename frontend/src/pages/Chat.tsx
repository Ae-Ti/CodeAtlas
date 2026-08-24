import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, Send, Loader2, Sparkles, BookOpen, Code2, RotateCcw, AlertCircle } from 'lucide-react';

/** 백엔드 ChatController.Source 와 1:1 */
interface ChatSource {
  paperId: number;
  paperTitle: string;
  chunkId: number;
  sectionTitle: string | null;
  score: number;
  codeRepository: string | null;
  codeSymbol: string | null;
  codeFile: string | null;
}

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  latencyMs?: number;
  error?: string;
  streaming?: boolean;
}

const STARTERS = [
  'CodeAtlas는 어떤 서비스야?',
  'multi-head attention은 어느 코드에 구현돼 있어?',
  'NL2SQL은 어떻게 안전하게 막아놨어?',
  '새 논문은 어떻게 추가해?',
];

/**
 * POST /api/chat 의 SSE 를 fetch 스트림으로 읽는다 (EventSource 는 POST 를 못 보낸다).
 * 이벤트: sources(JSON) → token({t}: JSON — 공백·줄바꿈 보존)… → done(JSON) | error(텍스트)
 */
async function streamChat(
  messages: { role: string; content: string }[],
  on: { sources: (s: ChatSource[]) => void; token: (t: string) => void; done: (latencyMs: number) => void; error: (e: string) => void },
  signal: AbortSignal,
) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ messages }),
    signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `요청 실패 (${res.status})`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  const dispatch = (block: string) => {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    const payload = data.join('\n');
    if (event === 'sources') on.sources(JSON.parse(payload));
    else if (event === 'token') on.token(JSON.parse(payload).t);
    else if (event === 'done') on.done(JSON.parse(payload).latencyMs);
    else if (event === 'error') on.error(payload);
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      if (block.trim()) dispatch(block);
    }
  }
}

/**
 * 존재하는 근거([1..n])를 가리키지 않는 [n] 마커를 본문에서 지운다 — 근거가 0개인데 모델이
 * 관성으로 붙인 [1] 같은 댕글링 인용이 8회 중 3회 관찰됐다(#55 리뷰 A 실측). 프롬프트 지시는
 * 모델이 어기므로, 화면에 못 박는 이 필터가 유일하게 결정적인 층이다.
 */
function stripDanglingCitations(text: string, sourceCount: number): string {
  return text.replace(/\s?\[(\d+)\]/g, (m, d) => {
    const n = Number(d);
    return n >= 1 && n <= sourceCount ? m : '';
  });
}

/** 답변에 섞여 오는 최소한의 마크다운(코드 펜스·인라인 코드·굵게)만 렌더링한다 */
function renderLite(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const parts = text.split(/```(?:\w+)?\n?/);
  parts.forEach((part, i) => {
    if (i % 2 === 1) {
      out.push(<pre key={i} className="sql-code" style={{ whiteSpace: 'pre-wrap', margin: '8px 0' }}>{part.replace(/\n$/, '')}</pre>);
      return;
    }
    const segs = part.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/);
    out.push(
      <span key={i}>
        {segs.map((s, j) => {
          if (s.startsWith('`') && s.endsWith('`')) return <code key={j} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85em', background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: 4 }}>{s.slice(1, -1)}</code>;
          if (s.startsWith('**') && s.endsWith('**')) return <strong key={j}>{s.slice(2, -2)}</strong>;
          return s;
        })}
      </span>,
    );
  });
  return out;
}

/** 답변 본문이 실제로 인용한 [n] 의 근거만 보여준다 — 검색은 됐지만 안 쓴 단락은 숨긴다 */
function SourceChips({ sources, content }: { sources: ChatSource[]; content: string }) {
  const cited = sources.map((s, i) => [s, i] as const).filter(([, i]) => content.includes(`[${i + 1}]`));
  if (!cited.length) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
      {cited.map(([s, i]) => (
        <Link key={s.chunkId} to={`/papers/${s.paperId}?chunkId=${s.chunkId}`} className="query-example-btn"
          style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.72rem' }}
          title={`유사도 ${s.score.toFixed(2)}${s.codeSymbol ? ` · ${s.codeRepository} / ${s.codeFile}` : ''}`}>
          <span style={{ color: 'var(--primary-light)', fontWeight: 700 }}>[{i + 1}]</span>
          <BookOpen size={11} /> {s.paperTitle.length > 34 ? s.paperTitle.slice(0, 34) + '…' : s.paperTitle}
          {s.sectionTitle && <span style={{ color: 'var(--text-muted)' }}>§{s.sectionTitle}</span>}
          {s.codeSymbol && <span style={{ color: 'var(--success-light)', fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: 3 }}><Code2 size={10} />{s.codeSymbol}</span>}
        </Link>
      ))}
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages]);
  useEffect(() => () => abortRef.current?.abort(), []);

  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput('');
    const history = [...messages.filter(m => !m.error), { role: 'user' as const, content: q }];
    setMessages([...history, { role: 'assistant', content: '', streaming: true }]);
    setBusy(true);
    const ac = new AbortController();
    abortRef.current = ac;
    const patchLast = (f: (m: Msg) => Msg) => setMessages(prev => prev.map((m, i) => (i === prev.length - 1 ? f(m) : m)));
    try {
      await streamChat(
        history.map(m => ({ role: m.role, content: m.content })),
        {
          sources: s => patchLast(m => ({ ...m, sources: s })),
          token: t => patchLast(m => ({ ...m, content: m.content + t })),
          done: ms => patchLast(m => ({ ...m, latencyMs: ms, streaming: false })),
          error: e => patchLast(m => ({ ...m, error: e, streaming: false })),
        },
        ac.signal,
      );
    } catch (e) {
      if (!ac.signal.aborted) patchLast(m => ({ ...m, error: e instanceof Error ? e.message : String(e), streaming: false }));
    } finally {
      patchLast(m => ({ ...m, streaming: false }));
      setBusy(false);
    }
  };

  const reset = () => { abortRef.current?.abort(); setMessages([]); setBusy(false); };

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 900 }}>
        <div className="page-header" style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <h1 className="page-title">
              <MessageCircle size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
              Chat
            </h1>
            <p className="page-subtitle">
              서비스와 카탈로그에 대해 자유롭게 물어보세요 — 질문마다 논문 단락을 검색해 근거와 함께 답합니다 (qwen3:8b 로컬)
            </p>
          </div>
          {messages.length > 0 && (
            <button className="btn btn-ghost" onClick={reset} style={{ fontSize: '0.8rem' }}><RotateCcw size={14} /> 새 대화</button>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, minHeight: 320, marginBottom: 20 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-tertiary)' }}>
              <Sparkles size={48} style={{ marginBottom: 12, opacity: 0.2 }} />
              <p style={{ marginBottom: 16 }}>예시 질문으로 시작하거나 직접 입력하세요</p>
              <div className="query-examples" style={{ justifyContent: 'center' }}>
                {STARTERS.map(s => <button key={s} className="query-example-btn" onClick={() => send(s)}>{s}</button>)}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div className={m.role === 'user' ? 'glass-card' : 'glass-card ai-response'}
                style={{ padding: '12px 16px', maxWidth: '85%',
                  background: m.role === 'user' ? 'rgba(59,130,246,0.15)' : undefined,
                  fontSize: '0.92rem', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                {m.role === 'assistant' && m.streaming && !m.content && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                    <Loader2 size={14} className="spinning" />
                    {m.sources ? `근거 ${m.sources.length}개를 읽고 답을 쓰는 중…` : '카탈로그에서 관련 단락을 찾는 중…'}
                  </span>
                )}
                {renderLite(m.role === 'assistant' && !m.streaming ? stripDanglingCitations(m.content, m.sources?.length ?? 0) : m.content)}
                {m.error && (
                  <p style={{ display: 'flex', gap: 6, color: 'var(--warning)', fontSize: '0.82rem', marginTop: 6 }}>
                    <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 2 }} /> {m.error}
                  </p>
                )}
                {m.role === 'assistant' && !m.streaming && m.sources && <SourceChips sources={m.sources} content={m.content} />}
                {m.role === 'assistant' && m.latencyMs != null && (
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 6 }}>
                    {(m.latencyMs / 1000).toFixed(1)}초 · 인용 근거 {(m.sources ?? []).filter((_, i) => m.content.includes(`[${i + 1}]`)).length}개 · 저장되지 않음
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div style={{ display: 'flex', gap: 10, position: 'sticky', bottom: 16 }}>
          <input className="input" placeholder="무엇이든 물어보세요 — 서비스 사용법, 논문 내용, 코드 위치…"
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.nativeEvent.isComposing && send()}
            disabled={busy} style={{ fontSize: '0.95rem', padding: '14px 18px' }} />
          <button className="btn btn-primary" onClick={() => send()} disabled={busy || !input.trim()} style={{ flexShrink: 0, padding: '14px 22px' }}>
            {busy ? <Loader2 size={18} className="spinning" /> : <Send size={18} />}
          </button>
        </div>
        {messages.length > 0 && (
          <div className="query-examples" style={{ marginTop: 10 }}>
            {STARTERS.map(s => <button key={s} className="query-example-btn" onClick={() => send(s)} disabled={busy}>{s}</button>)}
          </div>
        )}
      </div>
      <style>{`.spinning { animation: spin 1s linear infinite; }`}</style>
    </div>
  );
}
