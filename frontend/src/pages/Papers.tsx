import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, BookOpen, Calendar, ExternalLink, ArrowRight } from 'lucide-react';
import { mockPapers, type Paper } from '../data/papers';
import { getChunksByPaperId } from '../data/chunks';

const tasks = ['All', 'NLP', 'CV', 'RL', 'Multimodal'] as const;

const taskBadgeClass: Record<string, string> = {
  NLP: 'badge-nlp',
  CV: 'badge-cv',
  RL: 'badge-rl',
  Multimodal: 'badge-multimodal',
};

export default function Papers() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [activeTask, setActiveTask] = useState<string>('All');

  const filtered = useMemo(() => {
    return mockPapers.filter((p: Paper) => {
      const matchTask = activeTask === 'All' || p.task === activeTask;
      const matchSearch = search === '' ||
        p.title.toLowerCase().includes(search.toLowerCase()) ||
        p.authors.toLowerCase().includes(search.toLowerCase());
      return matchTask && matchSearch;
    });
  }, [search, activeTask]);

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
              placeholder="논문 제목 또는 저자 검색..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {tasks.map(t => (
              <button
                key={t}
                className={`btn ${activeTask === t ? 'btn-primary' : 'btn-ghost'}`}
                style={{ padding: '8px 16px', fontSize: '0.8rem' }}
                onClick={() => setActiveTask(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Paper Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>
          {filtered.map((paper, i) => {
            const chunkCount = getChunksByPaperId(paper.paperId).length;
            const goToPaper = () => navigate(`/papers/${paper.paperId}`);
            return (
              // A <div> (not <Link>) because the card also contains a real
              // external <a> for the PDF — nesting <a> inside <a> is invalid
              // HTML and made the PDF link's navigation unpredictable.
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
                  <span className={`badge ${taskBadgeClass[paper.task]}`}>{paper.task}</span>
                </div>
                <h3 className="paper-title">{paper.title}</h3>
                <p className="paper-authors">{paper.authors}</p>
                <p className="paper-abstract">{paper.abstract}</p>
                <div className="paper-meta">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Calendar size={12} /> {paper.year}
                  </span>
                  <span>{chunkCount} chunks</span>
                  <span className="card-hint" style={{ marginLeft: 'auto' }}>
                    자세히 보기 <ArrowRight size={12} />
                  </span>
                </div>
                <div className="paper-pdf-row">
                  <a href={paper.pdfUrl} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                    <ExternalLink size={12} /> PDF
                  </a>
                </div>
              </div>
            );
          })}
        </div>

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 64, color: 'var(--text-tertiary)' }}>
            <BookOpen size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
            <p>검색 결과가 없습니다</p>
          </div>
        )}
      </div>
    </div>
  );
}
