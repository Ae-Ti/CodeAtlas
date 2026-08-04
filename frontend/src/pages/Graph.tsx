import { useCallback, useMemo } from 'react';
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
import { mockPapers } from '../data/papers';
import { mockCodeBlocks } from '../data/codeBlocks';
import { mockChunks } from '../data/chunks';

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

function buildGraph() {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const paperX = 50;
  const codeX = 500;
  let codeY = 0;

  // Only show papers that have code mappings
  const mappedPaperIds = new Set<number>();
  mockChunks.forEach(chunk => {
    if (mockCodeBlocks[chunk.chunkId]) {
      mappedPaperIds.add(chunk.paperId);
    }
  });

  const papers = mockPapers.filter(p => mappedPaperIds.has(p.paperId));
  const codeNodeSet = new Set<string>();

  papers.forEach((paper, pi) => {
    const papNodeId = `paper-${paper.paperId}`;
    nodes.push({
      id: papNodeId,
      type: 'paperNode',
      position: { x: paperX, y: pi * 120 },
      data: { label: paper.title.length > 30 ? paper.title.slice(0, 30) + '...' : paper.title, paperId: paper.paperId },
    });

    // Find chunks with code blocks for this paper
    const paperChunks = mockChunks.filter(c => c.paperId === paper.paperId);
    paperChunks.forEach(chunk => {
      const codeBlocks = mockCodeBlocks[chunk.chunkId];
      if (!codeBlocks) return;

      codeBlocks.forEach(cb => {
        const codeNodeId = `code-${cb.codeBlockId}`;
        if (!codeNodeSet.has(codeNodeId)) {
          codeNodeSet.add(codeNodeId);
          nodes.push({
            id: codeNodeId,
            type: 'codeNode',
            position: { x: codeX, y: codeY },
            data: {
              label: (cb.className ? `${cb.className}.` : '') + cb.functionName,
              repo: cb.repoName,
            },
          });
          codeY += 90;
        }

        edges.push({
          id: `edge-${papNodeId}-${codeNodeId}-${chunk.chunkId}`,
          source: papNodeId,
          target: codeNodeId,
          animated: true,
          style: {
            stroke: cb.similarityScore > 0.9 ? '#10b981' : cb.similarityScore > 0.85 ? '#06b6d4' : '#64748b',
            strokeWidth: Math.max(1, cb.similarityScore * 3),
          },
          label: cb.similarityScore.toFixed(2),
          labelStyle: { fill: '#94a3b8', fontSize: 10, fontFamily: "'JetBrains Mono'" },
          labelBgStyle: { fill: '#1e293b', fillOpacity: 0.9 },
          labelBgPadding: [4, 4] as [number, number],
        });
      });
    });
  });

  return { nodes, edges };
}

export default function Graph() {
  const navigate = useNavigate();
  const { nodes: initialNodes, edges: initialEdges } = useMemo(buildGraph, []);
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

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
          <p className="page-subtitle">논문과 코드 구현체 간의 매핑 관계를 시각적으로 탐색합니다</p>
        </div>

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
              유사도 &gt; 0.90
            </div>
            <div className="legend-row">
              <span className="legend-line" style={{ background: '#06b6d4' }} />
              유사도 &gt; 0.85
            </div>
            <div className="legend-row">
              <span className="legend-line" style={{ background: '#64748b' }} />
              유사도 &le; 0.85
            </div>
            <div className="legend-row" style={{ color: 'var(--text-tertiary)', fontSize: '0.68rem' }}>
              엣지 굵기 = 유사도 크기
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
