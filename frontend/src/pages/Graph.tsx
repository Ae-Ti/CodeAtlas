import { useCallback, useEffect, useMemo } from 'react';
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

function buildGraph(mappings: MappingRow[]): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const paperX = 50;
  const codeX = 500;
  let codeY = 0;

  const paperSeen = new Map<number, number>();   // paperId -> y
  const codeSeen = new Set<number>();

  for (const m of mappings) {
    const paperNodeId = `paper-${m.paperId}`;
    if (!paperSeen.has(m.paperId)) {
      const y = paperSeen.size * 140;
      paperSeen.set(m.paperId, y);
      nodes.push({
        id: paperNodeId,
        type: 'paperNode',
        position: { x: paperX, y },
        data: {
          label: m.paperTitle.length > 30 ? `${m.paperTitle.slice(0, 30)}...` : m.paperTitle,
          paperId: m.paperId,
        },
      });
    }

    const codeNodeId = `code-${m.codeBlockId}`;
    if (!codeSeen.has(m.codeBlockId)) {
      codeSeen.add(m.codeBlockId);
      nodes.push({
        id: codeNodeId,
        type: 'codeNode',
        position: { x: codeX, y: codeY },
        data: { label: symbolLabel(m), repo: m.repositoryName },
      });
      codeY += 90;
    }

    edges.push({
      // 같은 논문↔코드 쌍이 여러 chunk로 연결될 수 있어 chunkId까지 id에 넣습니다
      id: `edge-${paperNodeId}-${codeNodeId}-${m.chunkId}`,
      source: paperNodeId,
      target: codeNodeId,
      animated: true,
      style: {
        stroke: edgeColor(m.similarityScore),
        strokeWidth: Math.max(1, m.similarityScore * 3),
      },
      label: m.similarityScore.toFixed(2),
      labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: "'JetBrains Mono'" },
      labelBgStyle: { fill: '#1e293b', fillOpacity: 0.9 },
      labelBgPadding: [4, 4] as [number, number],
    });
  }

  return { nodes, edges };
}

export default function Graph() {
  const navigate = useNavigate();
  const { data, loading, error, reload } = useApi(() => api.mappings(60), []);

  const built = useMemo(() => buildGraph(data ?? []), [data]);
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
          <div className="graph-container">
            <ReactFlow
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
        )}
      </div>
    </div>
  );
}
