import { api } from './http';

export interface RagIngestionStats {
  total_chunks: number;
  total_sources: number;
  total_questions: number;
  reviewed_questions: number;
  unreviewed_questions: number;
  chunks_by_chapter: Record<string, number>;
  chunks_by_source_type: Record<string, number>;
  avg_chunk_length: number;
  pages_processed: number;
}

export interface RagSource {
  id: number;
  source_type: string;
  title: string;
  grade: string;
  subject: string;
  year?: number | null;
  file_path?: string | null;
  original_filename?: string | null;
  status: string;
}

export interface RagReembedRequest {
  source_id?: number | null;
  source_type?: string | null;
  batch_size: number;
  dry_run: boolean;
  force: boolean;
  resume_failed: boolean;
}

export interface RagReembedResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface RagReembedStatus {
  job_id: string;
  status: string;
  progress: number;
  total_chunks: number;
  total_candidates: number;
  processed: number;
  updated: number;
  skipped: number;
  failed: number;
  embedding_model?: string | null;
  dry_run: boolean;
  error?: string | null;
}

export interface RagEvaluationResponse {
  status: string;
  passed: boolean;
  report_json_path: string;
  report_markdown_path: string;
  metrics: Record<string, number | string | boolean | null>;
  threshold_failures: string[];
}

export interface RetrievedChunkLog {
  id: number;
  rank: number;
  chunk_id?: number | null;
  source_id?: number | null;
  source_type?: string | null;
  page_number?: number | null;
  content_type?: string | null;
  similarity_score?: number | null;
  hybrid_score?: number | null;
  rerank_score?: number | null;
  used_in_answer: boolean;
  created_at: string;
}

export interface RagQueryLog {
  id: number;
  user_id?: number | null;
  query_text: string;
  normalized_query?: string | null;
  route: string;
  source_mode?: string | null;
  top_k: number;
  min_similarity: number;
  embedding_model?: string | null;
  retrieval_latency_ms?: number | null;
  generation_latency_ms?: number | null;
  total_latency_ms?: number | null;
  result_count: number;
  max_similarity?: number | null;
  avg_similarity?: number | null;
  low_confidence: boolean;
  answer_confidence?: number | null;
  created_at: string;
  retrieved_chunks: RetrievedChunkLog[];
}

export interface RagDebugResponse {
  chunks: Array<{
    id: number;
    source_id: number;
    content: string;
    source_type: string;
    content_type: string;
    page_number?: number | null;
    similarity_score: number;
  }>;
  diagnostics: Record<string, unknown>;
}

export const adminRagApi = {
  async getStats(): Promise<RagIngestionStats> {
    const { data } = await api.get<RagIngestionStats>('/admin/ingestion/stats');
    return data;
  },

  async getSources(): Promise<RagSource[]> {
    const { data } = await api.get<RagSource[]>('/admin/ingestion/sources');
    return data;
  },

  async startReembed(payload: RagReembedRequest): Promise<RagReembedResponse> {
    const { data } = await api.post<RagReembedResponse>('/admin/rag/reembed', payload);
    return data;
  },

  async getReembedStatus(jobId: string): Promise<RagReembedStatus> {
    const { data } = await api.get<RagReembedStatus>(`/admin/rag/reembed/status/${jobId}`);
    return data;
  },

  async runEvaluation(): Promise<RagEvaluationResponse> {
    const { data } = await api.post<RagEvaluationResponse>('/admin/rag/evaluate', {
      fail_on_threshold: false,
      top_k: 5,
    });
    return data;
  },

  async getLatestEvaluation(): Promise<RagEvaluationResponse> {
    const { data } = await api.get<RagEvaluationResponse>('/admin/rag/evaluation/latest');
    return data;
  },

  async getQueryLogs(params?: { low_confidence?: boolean; limit?: number }): Promise<RagQueryLog[]> {
    const { data } = await api.get<RagQueryLog[]>('/admin/rag/query-logs', { params });
    return data;
  },

  async retrieveDebug(query: string): Promise<RagDebugResponse> {
    const { data } = await api.post<RagDebugResponse>('/rag/retrieve-debug', {
      query,
      top_k: 6,
      min_similarity: 0,
    });
    return data;
  },
};
