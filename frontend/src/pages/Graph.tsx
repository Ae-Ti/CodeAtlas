import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitBranch } from 'lucide-react';
import { api, symbolLabel, type MappingRow } from '../api/client';
import { useApi } from '../hooks/useApi';
import { Loading, ErrorBox, EmptyState } from '../components/AsyncStates';

// Custom Paper Node
function PaperNodeComponent({ data }: { data: { label: string; paperId: number } }) {
  return (
    <div className="paper-node">
      <Handle type="source" position={Position.Right} style={{ background: 'var(--accent)' }} />
      <div className="node-type">📄 Paper</div>
      <div className="node-title">{data.label}</div>
    </div>
  );
}

// Custom Code Node
function CodeNodeComponent({ data }: { data: { label: string; repo: string } }) {
  return (
    <div className="code-node">
      <Handle type="target" position={Position.Left} style={{ background: 'var(--success)' }} />
      <div className="node-type">💻 Code</div>
      <div className="node-title">{data.label}</div>
      <div className="node-repo">{data.repo}</div>
    </div>
  );
}

const nodeTypes: NodeTypes = {
  paperNode: PaperNodeComponent,
  codeNode: CodeNodeComponent,
};

// 유사도 임계값 — 실제 pgvector 코사인 점수 분포에 맞춘 값입니다
// (mock 시절 0.90/0.85 기준은 실데이터에서 거의 전부 회색이 됩니다).
const HIGH = 0.75;
const MID = 0.65;

function edgeColor(score: number) {
  return score > HIGH ? '#10b981' : score > MID ? '#06b6d4' : '#64748b';
}

function buildGraph(mappings: MappingRow[], focusPaperId: number | null): { nodes: Node[]; edges: Edge[] } {
  // 논문별 클러스터(별자리) 배치 — #55 리뷰에서 A 확인한 최소 범위.
  // 이전의 2열(bipartite) 배치는 코드 노드가 도착 순서대로 오른쪽 열에 쌓여, 한 논문의
  // 코드가 열 전체에 흩어지고 모든 엣지가 길게 교차했다(논문 9편·60엣지에서 이미 실체가
  // 안 보임). 논문을 허브로 두고 그 코드들을 오른쪽 부채꼴로 붙이면 엣지가 클러스터 안에만
  // 있어 교차가 구조적으로 사라지고, 논문이 늘어도 그리드 행이 늘어날 뿐이다.
  // 한 코드 블록이 두 논문에 매핑되면 클러스터마다 복제한다(노드 id 에 paperId 포함) —
  // 공유 노드 하나를 두 클러스터가 당기는 것보다 시각적 명료함이 우선.
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // 포커스 모드(논문 칩 선택): 그 논문 클러스터 하나만 — 전체 뷰는 구조를, 포커스는 읽기를 맡는다.
  // 전체 뷰에서 노드·라벨이 작아 안 읽히는 문제(B 제보)의 답이 줌이 아니라 이 분리다.
  const shown = focusPaperId == null ? mappings : mappings.filter(m => m.paperId === focusPaperId);
  const byPaper = new Map<number, MappingRow[]>();
  for (const m of shown) {
    if (!byPaper.has(m.paperId)) byPaper.set(m.paperId, []);
    byPaper.get(m.paperId)!.push(m);
  }
  const focused = focusPaperId != null;

  const COLS = 3;          // 클러스터 그리드 열 수
  const CELL_W = 1050;     // 클러스터 간격 — 부채꼴 반지름 + 코드 노드 폭이 들어가는 크기
  // ⚠️ 여유를 갉아먹는 건 논문 수가 아니라 "논문당 코드 수"다 (#58 리뷰 A 계산):
  // 팬 5개 → ±60°, 세로 반경 329px, 행 간 여유 162px. 팬 7개면 spread 가 상한 170°에 닿아
  // 세로 반경 378px, 행 간 여유 64px — 노드 높이(74px)보다 작아져 겹친다. 논문당 코드가
  // 7개 이상이 되면 CELL_H 를 키우거나 spread 상한(아래 170)을 낮출 것.
  const CELL_H = 820;
  const RADIUS = 380;      // 허브(논문) → 코드 노드 거리

  let cluster = 0;
  for (const [paperId, rows] of byPaper) {
    const col = cluster % COLS;
    const row = Math.floor(cluster / COLS);
    const hubX = col * CELL_W;
    const hubY = row * CELL_H;
    cluster++;

    nodes.push({
      id: `paper-${paperId}`,
      type: 'paperNode',
      position: { x: hubX, y: hubY },
      data: {
        label: rows[0].paperTitle.length > 30 ? `${rows[0].paperTitle.slice(0, 30)}...` : rows[0].paperTitle,
        paperId,
      },
    });

    // 같은 코드 블록이 여러 chunk 로 연결될 수 있으므로 노드는 코드 블록 단위로 한 번만
    const codeIds = [...new Set(rows.map(m => m.codeBlockId))];
    codeIds.forEach((codeBlockId, j) => {
      const n = codeIds.length;
      // 허브 오른쪽 부채꼴 — 핸들 방향(논문 오른쪽 → 코드 왼쪽)과 일치해 엣지가 짧고 곧다
      const spread = n > 1 ? Math.min(170, (n - 1) * 30) : 0;
      const deg = n > 1 ? -spread / 2 + (spread * j) / (n - 1) : 0;
      const rad = (deg * Math.PI) / 180;
      const m = rows.find(r => r.codeBlockId === codeBlockId)!;
      nodes.push({
        id: `code-${paperId}-${codeBlockId}`,
        type: 'codeNode',
        position: { x: hubX + 240 + RADIUS * Math.cos(rad), y: hubY + RADIUS * Math.sin(rad) },
        data: { label: symbolLabel(m), repo: m.repositoryName },
      });
    });

    for (const m of rows) {
      edges.push({
        // 같은 논문↔코드 쌍이 여러 chunk로 연결될 수 있어 chunkId까지 id에 넣습니다
        id: `edge-paper-${paperId}-code-${m.codeBlockId}-${m.chunkId}`,
        source: `paper-${paperId}`,
        target: `code-${paperId}-${m.codeBlockId}`,
        animated: true,
        style: {
          stroke: edgeColor(m.similarityScore),
          strokeWidth: Math.max(1, m.similarityScore * 3),
        },
        // 유사도 숫자는 포커스 모드에서만 — 전체 뷰에서는 라벨 60개가 노이즈의 절반이다
        label: focused ? m.similarityScore.toFixed(2) : undefined,
        labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: "'JetBrains Mono'" },
        labelBgStyle: { fill: '#1e293b', fillOpacity: 0.9 },
        labelBgPadding: [4, 4] as [number, number],
      });
    }
  }

  return { nodes, edges };
}

export default function Graph() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(() => api.mappings(60), []);
  const [focusPaperId, setFocusPaperId] = useState<number | null>(null);

  const papers = useMemo(() => {
    const seen = new Map<number, string>();
    for (const m of data ?? []) if (!seen.has(m.paperId)) seen.set(m.paperId, m.paperTitle);
    return [...seen.entries()];
  }, [data]);

  const built = useMemo(() => buildGraph(data ?? [], focusPaperId), [data, focusPaperId]);
  const [nodes, setNodes, onNodesChange] = useNodesState(built.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(built.edges);

  // useNodesState는 초기값만 받으므로, fetch가 끝난 뒤 한 번 밀어넣어야 합니다
  useEffect(() => {
    setNodes(built.nodes);
    setEdges(built.edges);
  }, [built, setNodes, setEdges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    if (node.type === 'paperNode' && node.data.paperId) {
      navigate(`/papers/${node.data.paperId}`);
    }
  }, [navigate]);

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1 className="page-title">
            <GitBranch size={28} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            연결 그래프
          </h1>
          <p className="page-subtitle">사전계산된 논문–코드 매핑 관계를 시각적으로 탐색합니다</p>
        </div>

        {loading && <Loading message="매핑 관계를 불러오는 중..." />}
        {error && <ErrorBox error={error} onRetry={reload} />}

        {data && data.length === 0 && (
          <EmptyState
            icon={<GitBranch size={48} style={{ opacity: 0.3 }} />}
            title="아직 사전계산된 매핑이 없습니다."
            hint="curl -X POST localhost:8080/api/admin/curate-pending 으로 큐레이션 배치를 실행하세요."
          />
        )}

        {data && data.length > 0 && (
          <>
          <div className="query-examples" style={{ marginBottom: 12 }}>
            <button className="query-example-btn" onClick={() => setFocusPaperId(null)}
              style={focusPaperId == null ? { borderColor: 'var(--primary)', color: 'var(--primary-light)' } : undefined}>
              전체
            </button>
            {papers.map(([id, title]) => (
              <button key={id} className="query-example-btn" onClick={() => setFocusPaperId(id)}
                style={focusPaperId === id ? { borderColor: 'var(--primary)', color: 'var(--primary-light)' } : undefined}>
                {title.length > 22 ? title.slice(0, 22) + '…' : title}
              </button>
            ))}
          </div>
          <div className="graph-container">
            <ReactFlow
              key={focusPaperId ?? 'all'}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.3}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--text-muted)" gap={24} size={1} />
              <Controls style={{ background: 'var(--bg-tertiary)', borderColor: 'var(--border)' }} />
              <MiniMap
                nodeColor={(node) => node.type === 'paperNode' ? '#8b5cf6' : '#10b981'}
                maskColor="rgba(0, 0, 0, 0.6)"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
              />
            </ReactFlow>

            <div className="graph-legend">
              <div className="legend-title">범례</div>
              <div className="legend-row">
                <span className="legend-dot" style={{ background: '#8b5cf6' }} />
                논문 (Paper)
              </div>
              <div className="legend-row">
                <span className="legend-dot" style={{ background: '#10b981' }} />
                코드 구현체 (Code)
              </div>
              <div className="legend-divider" />
              <div className="legend-row">
                <span className="legend-line" style={{ background: '#10b981' }} />
                유사도 &gt; {HIGH.toFixed(2)}
              </div>
              <div className="legend-row">
                <span className="legend-line" style={{ background: '#06b6d4' }} />
                유사도 &gt; {MID.toFixed(2)}
              </div>
              <div className="legend-row">
                <span className="legend-line" style={{ background: '#64748b' }} />
                유사도 &le; {MID.toFixed(2)}
              </div>
              <div className="legend-row" style={{ color: 'var(--text-tertiary)', fontSize: '0.68rem' }}>
                엣지 굵기 = 유사도 크기
              </div>
            </div>
          </div>
          </>
        )}
      </div>
    </div>
  );
}
