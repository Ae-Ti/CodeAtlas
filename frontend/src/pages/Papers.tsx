import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, BookOpen, Calendar, ExternalLink, ArrowRight, GitBranch } from 'lucide-react';
import { api, type Paper } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Loading, ErrorBox, EmptyState } from '../components/AsyncStates';

const STATUS_FILTERS = ['All', 'COMPLETED', 'PROCESSING', 'PENDING', 'FAILED'] as const;

// Script-2.sql의 processing_status 값에 맞춘 배지 색상.
// (mock 시절의 task 분류(NLP/CV/RL)는 실제 스키마에 없는 컬럼이라 제거했습니다)
const statusBadgeClass: Record<string, string> = {
  COMPLETED: 'badge-nlp',
  PROCESSING: 'badge-multimodal',
  PENDING: 'badge-rl',
  FAILED: 'badge-cv',
};

export default function Papers() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [activeStatus, setActiveStatus] = useState<string>('All');
  const { data, loading, error, reload } = useApi(() => api.papers(), []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = search.trim().toLowerCase();
    return data.filter((p: Paper) => {
      const matchStatus = activeStatus === 'All' || p.processingStatus === activeStatus;
      const matchSearch = q === '' ||
        p.title.toLowerCase().includes(q) ||
        p.authors.some(a => a.toLowerCase().includes(q)) ||
        (p.arxivId ?? '').toLowerCase().includes(q);
      return matchStatus && matchSearch;
    });
  }, [data, search, activeStatus]);

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">
            <BookOpen size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            논문 탐색
          </h1>
          <p className="page-subtitle">AI 논문을 탐색하고 관련 코드 구현체를 찾아보세요</p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 16, marginBottom: 28, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: 1, minWidth: 240 }}>
            <Search size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              className="input"
              style={{ paddingLeft: 40 }}
              placeholder="논문 제목 · 저자 · arXiv ID 검색..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {STATUS_FILTERS.map(s => (
              <button
                key={s}
                className={`btn ${activeStatus === s ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '8px 16px', fontSize: '0.8rem' }}
                onClick={() => setActiveStatus(s)}
              >
                {s === 'All' ? '전체' : s}
              </button>
            ))}
          </div>
        </div>

        {loading && <Loading message="논문 목록을 불러오는 중..." />}
        {error && <ErrorBox error={error} onRetry={reload} />}

        {data && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
            {filtered.map((paper, i) => {
              const goToPaper = () => navigate(`/papers/${paper.paperId}`);
              const year = paper.publishedDate ? paper.publishedDate.slice(0, 4) : '—';
              return (
                // <Link>가 아니라 <div role="link"> — 카드 안에 PDF용 실제 <a>가 있어서
                // <a> 중첩(유효하지 않은 HTML)을 피해야 합니다.
                <div
                  key={paper.paperId}
                  role="link"
                  tabIndex={0}
                  className="glass-card paper-card animate-fade-in-up"
                  style={{ animationDelay: `${i * 60}ms`, opacity: 0 }}
                  onClick={goToPaper}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goToPaper(); } }}
                >
                  <div className="paper-task">
                    <span className={`badge ${statusBadgeClass[paper.processingStatus] ?? 'badge-rl'}`}>
                      {paper.processingStatus}
                    </span>
                  </div>
                  <h3 className="paper-title">{paper.title}</h3>
                  <p className="paper-authors">{paper.authors.join(', ') || '저자 정보 없음'}</p>
                  <p className="paper-abstract">{paper.abstractText ?? '초록이 등록되지 않았습니다.'}</p>
                  <div className="paper-meta">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Calendar size={12} /> {year}
                    </span>
                    <span>{paper.chunkCount} chunks</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}
                          title="코드 매핑이 사전계산된 chunk 수">
                      <GitBranch size={12} /> {paper.mappedChunkCount}/{paper.chunkCount} 매핑
                    </span>
                    <span className="card-hint" style={{ marginLeft: 'auto' }}>
                      자세히 보기 <ArrowRight size={12} />
                    </span>
                  </div>
                  {paper.pdfUrl && (
                    <div className="paper-pdf-row">
                      <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                        <ExternalLink size={12} /> PDF
                      </a>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {data && filtered.length === 0 && (
          <EmptyState
            icon={<BookOpen size={48} style={{ opacity: 0.3 }} />}
            title={data.length === 0 ? '적재된 논문이 없습니다.' : '검색 결과가 없습니다'}
            hint={data.length === 0 ? 'database/seed_demo.sql 이 적재됐는지 확인하세요.' : undefined}
          />
        )}
      </div>
    </div>
  );
}
