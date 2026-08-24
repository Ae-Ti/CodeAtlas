/**
 * CodeAtlas 백엔드 API 클라이언트.
 *
 * 타입은 backend의 응답 record와 1:1로 맞춰져 있습니다.
 * 백엔드 DTO를 바꾸면 여기도 같이 바꿔야 합니다 — docs/api-spec.md 참고.
 *
 * dev에서는 vite proxy가 /api를 localhost:8080으로 넘깁니다 (vite.config.ts).
 * 배포 시에는 VITE_API_BASE로 절대 URL을 넣을 수 있습니다.
 */
const BASE = import.meta.env.VITE_API_BASE ?? '';

/** 백엔드가 내려주는 공통 에러 형식 — { error, detail } */
export class ApiError extends Error {
  // tsconfig의 erasableSyntaxOnly 때문에 생성자 파라미터 프로퍼티는 쓸 수 없습니다
  status: number;
  code: string;

  constructor(status: number, code: string, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch {
    // fetch 자체가 실패 = 서버가 안 떠 있거나 네트워크 문제
    throw new ApiError(0, 'NETWORK', '백엔드에 연결할 수 없습니다. localhost:8080에서 서버가 실행 중인지 확인하세요.');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.error ?? 'UNKNOWN', body?.detail ?? `요청 실패 (${res.status})`);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body) });

// ─────────────────────────────────────────────────────────
// 타입
// ─────────────────────────────────────────────────────────

export interface Paper {
  paperId: number;
  title: string;
  abstractText: string | null;
  authors: string[];
  arxivId: string | null;
  pdfUrl: string | null;
  publishedDate: string | null;   // ISO date
  processingStatus: string;
  chunkCount: number;
  mappedChunkCount: number;
}

export interface PaperChunk {
  chunkId: number;
  sectionTitle: string | null;
  subsectionTitle: string | null;
  chunkIndex: number;
  chunkText: string;
}

/** MCP ChunkResult — 검색 결과에는 유사도 score가 붙는다 */
export interface ChunkResult {
  chunkId: number;
  paperId: number;
  sectionTitle: string | null;
  chunkText: string;
  score: number;
}

/** /api/mapping/search 결과 — MCP CodeCandidate + 라인번호/GitHub URL */
export interface CodeMatch {
  codeBlockId: number;
  repositoryName: string;
  filePath: string;
  symbolName: string | null;
  symbolType: string;
  parentSymbolName: string | null;
  startLine: number | null;
  endLine: number | null;
  codeContent: string;
  similarityScore: number;
  githubUrl: string | null;
}

/** /api/agent/query 결과 — 라인번호·GitHub URL은 없다 */
export interface CodeCandidate {
  codeBlockId: number;
  repositoryName: string;
  filePath: string;
  symbolName: string | null;
  symbolType: string;
  parentSymbolName: string | null;
  codeContent: string;
  similarityScore: number;
}

export interface ToolTiming {
  toolName: string;
  status: string;
  latencyMs: number;
}

export interface TaccSummary {
  /** 사전계산 경로에서는 배치 시점 수치가 DB에 없어 null */
  initialContexts: number | null;
  removedContexts: number | null;
  selectedContexts: number;
}

export interface AgentQueryResponse {
  queryChunk: ChunkResult;
  results: CodeCandidate[];
  explanation: string;
  source: 'precomputed' | 'live';
  /**
   * false면 이 논문에 연결된 저장소가 없어 전체 코퍼스로 폴백한 결과 —
   * results가 전부 **다른 논문의 구현**이므로 화면에서 반드시 그렇게 밝혀야 합니다.
   * (사전계산 경로는 항상 true — 폴백 결과는 저장되지 않습니다)
   */
  paperScoped: boolean;
  mappingReason: string | null;
  tacc: TaccSummary;
  mcpTools: ToolTiming[];
}

export interface NlSqlResult {
  generatedSql: string;
  columns: string[];
  rows: Record<string, string | number | boolean | null>[];
  isReadOnly: boolean;
}

export interface Stats {
  papers: number;
  chunks: number;
  repositories: number;
  codeBlocks: number;
  mappings: number;
}

export interface MappingRow {
  paperId: number;
  paperTitle: string;
  chunkId: number;
  sectionTitle: string | null;
  codeBlockId: number;
  repositoryName: string;
  filePath: string;
  symbolName: string | null;
  parentSymbolName: string | null;
  similarityScore: number;
  verified: boolean;
}

// ─────────────────────────────────────────────────────────
// 엔드포인트
// ─────────────────────────────────────────────────────────

export const api = {
  stats: () => request<Stats>('/api/stats'),

  mappings: (limit = 50) => request<MappingRow[]>(`/api/mappings?limit=${limit}`),

  papers: () => request<Paper[]>('/api/papers'),

  chunks: (paperId: number) => request<PaperChunk[]>(`/api/papers/${paperId}/chunks`),

  /** SearchPaperChunk MCP tool과 같은 엔진 */
  searchChunks: (queryText: string, topK = 5, paperId?: number) =>
    post<ChunkResult[]>('/api/papers/chunks/search', { queryText, topK, paperId }),

  /** 순수 벡터 검색 — AI 설명 없음, 항상 빠름 */
  /**
   * `paperScoped`가 false면 이 논문에 연결된 저장소가 없어 전체 코퍼스로 폴백한 결과입니다.
   * 그 경우 결과는 전부 **다른 논문의 구현**이므로 화면에서 반드시 그렇게 밝혀야 합니다.
   */
  mappingSearch: (paperId: number, chunkId: number, topK = 5) =>
    post<{ queryChunk: ChunkResult; results: CodeMatch[]; paperScoped: boolean }>(
      '/api/mapping/search', { paperId, chunkId, topK }),

  /** 사전계산 결과가 있으면 즉시, 없으면 Qwen3를 그 자리에서 호출 (수십 초 소요 가능) */
  agentQuery: (query: string, paperId: number, chunkId: number) =>
    post<AgentQueryResponse>('/api/agent/query', { query, paperId, chunkId }),

  nl2sql: (query: string) => post<NlSqlResult>('/api/nl2sql', { query }),

  /**
   * 질문 텍스트에 실제로 답하는 유일한 경로 — 매 호출이 Qwen3 라이브 생성(수십 초).
   * DB에 아무것도 저장하지 않으며, 60초 하드 타임아웃을 넘기면 504(LLM_TIMEOUT)로 떨어진다.
   */
  agentAnswer: (query: string, paperId: number, chunkId: number) =>
    post<AgentAnswerResult>('/api/agent/answer', { query, paperId, chunkId }),

  /** 업로드 작업 — arXiv ID + GitHub URL 로 자동 적재 (분리·적재·임베딩·큐레이션, 수십 분) */
  uploadArxiv: (arxivId: string, githubUrl: string, relationType?: string) =>
    post<UploadJob>('/api/admin/upload', { arxivId, githubUrl, relationType }),

  /** 업로드 작업 — ingest JSON 직접 업로드 (검증 → 적재 → 임베딩 → 큐레이션) */
  uploadIngestJson: (fileName: string, json: string) =>
    request<UploadJob>(`/api/admin/upload/ingest-json?fileName=${encodeURIComponent(fileName)}`,
      { method: 'POST', body: json }),

  uploadJob: (id: string) => request<UploadJob>(`/api/admin/upload/${id}`),

  /** 파이썬 단계 진행 중인 작업 취소 — 임베딩·큐레이션 단계는 중단 불가(canceled=false) */
  uploadCancel: (id: string) => post<{ canceled: boolean }>(`/api/admin/upload/${id}/cancel`, {}),

  uploadJobs: () => request<UploadJob[]>('/api/admin/upload'),
};

export interface AgentAnswerResult {
  answer: string;
  latencyMs: number;
}

export interface UploadJob {
  id: string;
  type: 'arxiv' | 'json';
  label: string;
  status: 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED' | 'CANCELED';
  stage: string | null;
  stageMessage: string | null;
  stages: string[];
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  paperId: number | null;
  chunks: number | null;
  codeBlocks: number | null;
  mappings: number | null;
  error: string | null;
  log: string[];
}

/** METHOD면 `MultiHeadedAttention.forward` 형태로 표시 */
export function symbolLabel(c: { symbolName: string | null; parentSymbolName: string | null }): string {
  if (!c.symbolName) return '(unnamed)';
  return c.parentSymbolName ? `${c.parentSymbolName}.${c.symbolName}` : c.symbolName;
}
