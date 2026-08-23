import { Link } from 'react-router-dom';
import { BookOpen, Code2, GitBranch, ArrowRight, Sparkles, Layers } from 'lucide-react';
import { api, symbolLabel } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Loading, ErrorBox, EmptyState } from '../components/AsyncStates';
import { useAnimateNumber } from '../hooks/useAnimateNumber';

function StatCard({ icon, value, label, color, delay }: {
  icon: React.ReactNode;
  value: number;
  label: string;
  color: string;
  delay: number;
}) {
  const animated = useAnimateNumber(value, { duration: 1200, delay });
  return (
    <div className="glass-card stat-card animate-fade-in-up" style={{ animationDelay: `${delay}ms` }}>
      <div className="stat-icon" style={{ background: `${color}20`, color }}>{icon}</div>
      <div className="stat-value" style={{ color }}>{animated}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function StatsRow() {
  const { data, loading, error, reload } = useApi(() => api.stats(), []);

  if (loading) return <Loading message="통계를 불러오는 중..." padding={40} />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="stats-grid" style={{ marginBottom: 48 }}>
      <StatCard icon={<BookOpen size={20} />} value={data.papers} label="논문 수" color="#3b82f6" delay={100} />
      <StatCard icon={<Layers size={20} />} value={data.chunks} label="논문 Chunks" color="#8b5cf6" delay={200} />
      <StatCard icon={<Code2 size={20} />} value={data.codeBlocks} label="코드 블록" color="#10b981" delay={300} />
      <StatCard icon={<GitBranch size={20} />} value={data.mappings} label="매핑 수" color="#06b6d4" delay={400} />
    </div>
  );
}

function RecentMappings() {
  const { data, loading, error, reload } = useApi(() => api.mappings(6), []);

  if (loading) return <Loading message="매핑 결과를 불러오는 중..." padding={40} />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!data?.length) {
    return (
      <EmptyState
        icon={<GitBranch size={40} />}
        title="아직 사전계산된 매핑이 없습니다."
        hint="POST /api/admin/curate-pending 으로 큐레이션 배치를 실행하세요."
      />
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
      {data.map((m, i) => (
        <Link to={`/papers/${m.paperId}?chunkId=${m.chunkId}`} key={`${m.chunkId}-${m.codeBlockId}`} style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="glass-card animate-fade-in-up" style={{ padding: 24, animationDelay: `${(i + 1) * 100}ms`, cursor: 'pointer' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', background: 'rgba(139, 92, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <BookOpen size={16} color="var(--accent-light)" />
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--accent-light)', fontWeight: 600, marginBottom: 2 }}>{m.sectionTitle}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{m.paperTitle}</div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '4px 0' }}>
              <div style={{ width: '100%', height: 1, background: 'var(--border)' }} />
              <ArrowRight size={16} color="var(--text-muted)" style={{ margin: '0 8px', flexShrink: 0 }} />
              <div style={{ width: '100%', height: 1, background: 'var(--border)' }} />
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginTop: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Code2 size={16} color="var(--success-light)" />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--success-light)', fontWeight: 600, marginBottom: 2 }}>
                  {symbolLabel(m)}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{m.repositoryName}</div>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 700, color: 'var(--success-light)' }}>
                {m.similarityScore.toFixed(2)}
              </div>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="page">
      <div className="container">
        {/* Hero */}
        <div style={{ textAlign: 'center', marginBottom: 56, paddingTop: 32 }}>
          <div className="animate-fade-in-up" style={{ marginBottom: 16 }}>
            <span className="badge badge-nlp" style={{ fontSize: '0.7rem', padding: '6px 14px' }}>
              <Sparkles size={12} style={{ marginRight: 4 }} /> AI-Powered Paper-to-Code Mapping
            </span>
          </div>
          <h1 className="animate-fade-in-up stagger-1" style={{ fontSize: '3.2rem', fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1.1, marginBottom: 16 }}>
            Code<span className="gradient-text">Atlas</span>
          </h1>
          <p className="animate-fade-in-up stagger-2" style={{ color: 'var(--text-secondary)', fontSize: '1.15rem', maxWidth: 600, margin: '0 auto', lineHeight: 1.6 }}>
            AI 논문의 핵심 개념과 오픈소스 코드 구현체를 자동으로 매핑하여 연결합니다.
            MCP Agent 기반 검색과 TACC 컨텍스트 선별로 정확한 코드를 찾아냅니다.
          </p>
          <div className="animate-fade-in-up stagger-3" style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 28 }}>
            <Link to="/papers" className="btn btn-primary">
              <BookOpen size={16} /> 논문 탐색하기
            </Link>
            <Link to="/agent" className="btn btn-accent">
              <Sparkles size={16} /> AI Agent 체험
            </Link>
          </div>
        </div>

        <StatsRow />

        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>논문별 대표 매핑</h2>
            <Link to="/papers" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              전체 보기 <ArrowRight size={14} />
            </Link>
          </div>
          <RecentMappings />
        </div>

        {/* Architecture overview */}
        <div style={{ marginTop: 56, textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: 24 }}>시스템 아키텍처</h2>
          <div className="glass-card" style={{ padding: 40, display: 'flex', justifyContent: 'center', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
            {[
              { icon: <BookOpen size={24} />, label: 'arXiv Papers', sub: 'PDF Parsing', color: 'var(--accent)' },
              { icon: <Layers size={24} />, label: 'Chunking', sub: 'Section Split', color: 'var(--primary)' },
              { icon: <Code2 size={24} />, label: 'Embedding', sub: 'pgvector', color: 'var(--cyan)' },
              { icon: <Sparkles size={24} />, label: 'MCP Agent', sub: 'TACC + NL2SQL', color: 'var(--warning)' },
              { icon: <GitBranch size={24} />, label: 'Mapping', sub: 'Visualization', color: 'var(--success)' },
            ].map((step, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {i > 0 && <ArrowRight size={16} color="var(--text-muted)" />}
                <div style={{ textAlign: 'center' }}>
                  <div style={{ width: 56, height: 56, borderRadius: 'var(--radius-lg)', background: `${step.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 8px', color: step.color }}>
                    {step.icon}
                  </div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{step.label}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>{step.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
