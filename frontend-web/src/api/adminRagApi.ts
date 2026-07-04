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
  metadata_json?: Record<string, unknown> | unknown[] | null;
  chunk_count?: number;
  embedded_chunk_count?: number;
  question_count?: number;
  pages_summary?: Record<string, number>;
  canonical_source?: boolean;
  file_sha256?: string | null;
  file_size_bytes?: number | null;
  page_count?: number | null;
  reviewed_metadata_version?: string | null;
  reviewed_metadata_status?: string | null;
  ready_for_embedding?: boolean | null;
  embedding_status?: string | null;
  missing_metadata_count?: number;
  manual_review_count?: number;
  reviewed_chunks_path?: string | null;
  reviewed_preview_path?: string | null;
  reviewed_metadata_path?: string | null;
}

export interface CanonicalSourceStatus {
  source_type: string;
  title: string;
  file_path: string;
  grade: string;
  subject: string;
  year?: number | null;
  exists: boolean;
  file_size_bytes?: number | null;
  sha256?: string | null;
  page_count?: number | null;
  source_id?: number | null;
  source_status?: string | null;
  chunk_count: number;
  embedded_chunk_count: number;
  reviewed_metadata_version?: string | null;
  reviewed_metadata_status?: string | null;
  ready_for_embedding: boolean;
  missing_metadata_count: number;
  manual_review_count: number;
  embedding_status: string;
  reviewed_chunks_path?: string | null;
  reviewed_preview_path?: string | null;
  reviewed_metadata_path?: string | null;
  errors: string[];
}

export interface CanonicalSourcesValidationResponse {
  sources: CanonicalSourceStatus[];
  registered_count: number;
  updated_count: number;
  missing_count: number;
  reviewed_metadata_version?: string | null;
  ready_for_embedding: boolean;
  can_prepare_chunks: boolean;
}

export interface PrepareReviewedChunksResponse {
  status: string;
  write: boolean;
  reviewed_metadata_version: string;
  ready_for_embedding: boolean;
  textbook: Record<string, unknown>;
  solution_book: Record<string, unknown>;
  counts: Record<string, number>;
  blocking_issues: string[];
  files_written: string[];
  backups: string[];
}

export interface EmbeddingReadiness {
  reviewed_metadata_version?: string | null;
  status: string;
  ready_for_embedding: boolean;
  blocking_issues: string[];
  required_chunk_metadata: string[];
  allowed_source_types: string[];
  embedding_model: string;
  embedding_dimension: number;
  vector_store: string;
  vector_index: string;
  textbook_chunks_total: number;
  textbook_missing_metadata_count: number;
  solution_chunks_total: number;
  solution_manual_review_count: number;
  solution_bad_endings_count: number;
  ready_chunk_count: number;
  needs_review_chunk_count: number;
  blocked_chunk_count: number;
}

export interface IngestionPage {
  id?: number | null;
  source_id: number;
  job_id?: number | null;
  page_number: number;
  page_type: string;
  status: string;
  extraction_methods?: string[] | Record<string, unknown> | null;
  cache_path?: string | null;
  char_count: number;
  completeness_score: number;
  warnings_json?: unknown[] | Record<string, unknown> | null;
  errors_json?: unknown[] | Record<string, unknown> | null;
  content_preview?: string | null;
}

export interface IngestionRetryPageResponse {
  page_id: number;
  status: string;
  message: string;
  page?: IngestionPage | null;
  chunks_deleted: number;
  questions_deleted: number;
  chunks_created: number;
  questions_created: number;
  cache_invalidation: Record<string, number>;
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

  async validateCanonicalSources(): Promise<CanonicalSourcesValidationResponse> {
    const { data } = await api.post<CanonicalSourcesValidationResponse>('/admin/ingestion/sources/validate');
    return data;
  },

  async prepareReviewedChunks(payload: { write?: boolean } = {}): Promise<PrepareReviewedChunksResponse> {
    const { data } = await api.post<PrepareReviewedChunksResponse>('/admin/ingestion/prepare-reviewed-chunks', {
      write: payload.write ?? true,
      include_textbook: true,
      include_solution_book: true,
    });
    return data;
  },

  async getEmbeddingReadiness(): Promise<EmbeddingReadiness> {
    const { data } = await api.get<EmbeddingReadiness>('/admin/ingestion/embedding-readiness');
    return data;
  },

  async getSource(sourceId: number): Promise<RagSource> {
    const { data } = await api.get<RagSource>(`/admin/ingestion/sources/${sourceId}`);
    return data;
  },

  async getSourcePages(sourceId: number): Promise<IngestionPage[]> {
    const { data } = await api.get<IngestionPage[]>(`/admin/ingestion/pages/${sourceId}`);
    return data;
  },

  async retryPage(pageId: number): Promise<IngestionRetryPageResponse> {
    const { data } = await api.post<IngestionRetryPageResponse>(`/admin/ingestion/retry-page/${pageId}`);
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
