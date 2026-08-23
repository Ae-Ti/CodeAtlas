import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { UploadCloud, FileJson, Loader2, CheckCircle2, Circle, AlertCircle, ArrowRight, Clock } from 'lucide-react';
import { api, ApiError, type UploadJob } from '../api/client';
import { ErrorBox } from '../components/AsyncStates';

/** 단계 이름 → 화면 라벨. 백엔드 UploadJobService 의 단계 이름과 1:1 */
const STAGE_LABEL: Record<string, string> = {
  ARXIV_META: 'arXiv 메타데이터',
  EPRINT: 'LaTeX 소스 다운로드',
  REPO_CLONE: '저장소 클론',
  CODE_BLOCKS: '코드 블록 추출 (ast)',
  LATEX_SPLIT: '단락 분리 (Qwen3)',
  VALIDATE: 'JSON 검증',
  INGEST: 'DB 적재',
  EMBEDDING: '임베딩 (nomic-embed-text)',
  CURATION: '큐레이션 (Qwen3 설명 생성)',
};

function stageState(job: UploadJob, stage: string): 'done' | 'running' | 'failed' | 'pending' {
  const idx = job.stages.indexOf(stage);
  const cur = job.stage ? job.stages.indexOf(job.stage) : -1;
  if (job.status === 'DONE') return 'done';
  if (idx < cur) return 'done';
  if (idx === cur) return job.status === 'FAILED' ? 'failed' : 'running';
  return 'pending';
}

function elapsed(from: string | null, to: string | null): string {
  if (!from) return '';
  const ms = (to ? new Date(to).getTime() : Date.now()) - new Date(from).getTime();
  const s = Math.max(0, Math.round(ms / 1000));
  return s < 60 ? `${s}초` : `${Math.floor(s / 60)}분 ${s % 60}초`;
}

function JobCard({ job }: { job: UploadJob }) {
  const logRef = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [job.log.length]);

  const icon = {
    done: <CheckCircle2 size={16} color="var(--success-light)" />,
    running: <Loader2 size={16} className="spinning" color="var(--primary-light)" />,
    failed: <AlertCircle size={16} color="var(--warning)" />,
    pending: <Circle size={16} color="var(--text-muted)" />,
  };

  return (
    <div className="glass-card" style={{ padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 600 }}>{job.label}</span>
        <span className="badge" style={{
          background: job.status === 'DONE' ? 'rgba(16,185,129,0.15)' : job.status === 'FAILED' ? 'rgba(245,158,11,0.15)' : 'rgba(59,130,246,0.15)',
          color: job.status === 'DONE' ? 'var(--success-light)' : job.status === 'FAILED' ? 'var(--warning)' : 'var(--primary-light)',
        }}>
          {job.status}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Clock size={12} /> {elapsed(job.startedAt, job.finishedAt) || '대기 중'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 14 }}>
        {job.stages.map(stage => {
          const st = stageState(job, stage);
          return (
            <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem',
              color: st === 'pending' ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
              {icon[st]}
              <span style={{ minWidth: 200 }}>{STAGE_LABEL[stage] ?? stage}</span>
              {st === 'running' && job.stageMessage && (
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{job.stageMessage}</span>
              )}
            </div>
          );
        })}
      </div>

      {job.status === 'DONE' && job.paperId != null && (
        <div className="cross-paper-notice" style={{ marginBottom: 12 }}>
          <CheckCircle2 size={14} />
          <span>
            적재 완료 — chunk {job.chunks ?? '?'}개 · code block {job.codeBlocks ?? '?'}개 · 매핑 {job.mappings ?? 0}건.{' '}
            <Link to={`/papers/${job.paperId}`} style={{ color: 'var(--primary-light)', fontWeight: 600 }}>
              논문 보기 <ArrowRight size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
            </Link>
          </span>
        </div>
      )}
      {job.status === 'FAILED' && (
        <p style={{ display: 'flex', gap: 6, color: 'var(--warning)', fontSize: '0.82rem', marginBottom: 12 }}>
          <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} /> {job.error}
        </p>
      )}

      {job.log.length > 0 && (
        <pre ref={logRef} className="sql-code" style={{ maxHeight: 220, overflow: 'auto', fontSize: '0.72rem', lineHeight: 1.5, whiteSpace: 'pre-wrap', margin: 0 }}>
          {job.log.join('\n')}
        </pre>
      )}
    </div>
  );
}

export default function Upload() {
  const [arxivId, setArxivId] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [relation, setRelation] = useState('OFFICIAL');
  const [jsonFile, setJsonFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // 목록은 최초 1회, 진행 중인 작업은 2초마다 상세(로그 포함)를 당겨온다
  useEffect(() => {
    api.uploadJobs().then(setJobs).catch(() => {});
  }, []);
  useEffect(() => {
    if (!activeId) return;
    let stop = false;
    const tick = async () => {
      try {
        const j = await api.uploadJob(activeId);
        if (stop) return;
        setJobs(prev => prev.some(p => p.id === j.id) ? prev.map(p => (p.id === j.id ? j : p)) : [j, ...prev]);
        if (j.status === 'DONE' || j.status === 'FAILED') return;
      } catch { /* 다음 tick 에 재시도 */ }
      if (!stop) timer = setTimeout(tick, 2000);
    };
    let timer = setTimeout(tick, 0);
    return () => { stop = true; clearTimeout(timer); };
  }, [activeId]);

  const submitArxiv = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const job = await api.uploadArxiv(arxivId.trim(), githubUrl.trim(), relation);
      setJobs(prev => [job, ...prev]);
      setActiveId(job.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const submitJson = async () => {
    if (!jsonFile) return;
    setError(null);
    setSubmitting(true);
    try {
      const text = await jsonFile.text();
      JSON.parse(text); // 형식 오류는 서버까지 가지 않고 여기서 잡는다
      const job = await api.uploadIngestJson(jsonFile.name, text);
      setJobs(prev => [job, ...prev]);
      setActiveId(job.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof SyntaxError ? `JSON 형식 오류: ${e.message}` : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const running = jobs.some(j => j.status === 'RUNNING' || j.status === 'QUEUED');

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">
            <UploadCloud size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            논문·코드 업로드
          </h1>
          <p className="page-subtitle">
            arXiv 논문과 GitHub 구현 저장소를 카탈로그에 추가합니다 — 단락 분리 → 적재 → 임베딩 → 큐레이션까지 자동
          </p>
        </div>

        <div className="agent-results" style={{ marginBottom: 32 }}>
          {/* 자동 적재 */}
          <div className="glass-card" style={{ padding: 24 }}>
            <div className="agent-section-title"><UploadCloud size={14} /> arXiv + GitHub 로 자동 적재</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
              <input className="input" placeholder="arXiv ID — 예: 1505.04597 (또는 arxiv.org/abs/… URL)"
                value={arxivId} onChange={e => setArxivId(e.target.value)} />
              <input className="input" placeholder="GitHub 저장소 URL — 예: https://github.com/milesial/Pytorch-UNet"
                value={githubUrl} onChange={e => setGithubUrl(e.target.value)} />
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <select className="input" value={relation} onChange={e => setRelation(e.target.value)} style={{ flex: 1 }}>
                  <option value="OFFICIAL">OFFICIAL — 저자 공식 구현</option>
                  <option value="COMMUNITY">COMMUNITY — 커뮤니티 재구현</option>
                </select>
                <button className="btn btn-primary" onClick={submitArxiv}
                  disabled={submitting || running || !arxivId.trim() || !githubUrl.trim()} style={{ flexShrink: 0 }}>
                  {submitting ? <Loader2 size={16} className="spinning" /> : <UploadCloud size={16} />} 적재 시작
                </button>
              </div>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', lineHeight: 1.6, marginTop: 12 }}>
              arXiv 에 LaTeX 소스가 있는 논문 + Python 저장소만 지원합니다. 단락 분리와 큐레이션이 Qwen3 를
              섹션·단락마다 호출하므로 <strong>논문 한 편에 10~30분</strong> 걸립니다. 그동안 Ollama 가 이 작업에
              묶여 Chat·AI 답변 같은 라이브 생성은 느려집니다. 같은 arXiv ID 를 다시 올리면 덮어씁니다(upsert).
            </p>
          </div>

          {/* JSON 직접 업로드 */}
          <div className="glass-card" style={{ padding: 24 }}>
            <div className="agent-section-title"><FileJson size={14} /> ingest JSON 직접 업로드</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
              <input type="file" accept="application/json,.json" className="input"
                onChange={e => setJsonFile(e.target.files?.[0] ?? null)} style={{ flex: 1 }} />
              <button className="btn btn-ghost" onClick={submitJson} disabled={submitting || running || !jsonFile} style={{ flexShrink: 0 }}>
                <FileJson size={16} /> 업로드
              </button>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', lineHeight: 1.6, marginTop: 12 }}>
              단락·코드 블록을 직접 작성한 경우 (형식: <code>database/ingest_example.json</code>, 절차:
              <code> docs/A_논문DB구축_가이드.md</code>). LaTeX 소스가 없는 논문이나 Python 이 아닌 저장소는 이 경로로.
              <code>scripts/ingest.py --dry-run</code> 과 같은 검증을 먼저 거칩니다.
            </p>
          </div>
        </div>

        {error && <div style={{ marginBottom: 24 }}><ErrorBox error={error} /></div>}
        {running && (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginBottom: 16 }}>
            작업은 한 번에 하나만 돕니다 (LLM 단계가 직렬이라 동시에 돌려도 빨라지지 않습니다). 진행 중인 작업이 끝나면 다음을 올릴 수 있습니다.
          </p>
        )}

        <div className="agent-section-title">업로드 작업</div>
        {jobs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: 'var(--text-tertiary)' }}>
            <UploadCloud size={48} style={{ marginBottom: 12, opacity: 0.2 }} />
            <p>아직 업로드한 작업이 없습니다. 위에서 arXiv ID 와 저장소 URL 을 넣어 시작하세요.</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {jobs.map(job => (
              <div key={job.id} onClick={() => setActiveId(job.id)} style={{ cursor: job.log.length ? 'default' : 'pointer' }}>
                <JobCard job={job} />
              </div>
            ))}
          </div>
        )}
      </div>
      <style>{`.spinning { animation: spin 1s linear infinite; }`}</style>
    </div>
  );
}
