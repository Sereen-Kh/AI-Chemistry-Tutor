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

export interface RagSourceStatus {
  id: 'textbook' | 'solution_book';
  db_source_id?: number | null;
  source_type: 'textbook' | 'solution_book';
  file_path: string;
  filename: string;
  checksum_sha256?: string | null;
  page_count?: number | null;
  file_size_bytes?: number | null;
  last_modified_at?: string | null;
  ingestion_status: string;
  extraction_status: string;
  chunk_status: string;
  embedding_status: string;
  errors: string[];
  warnings: string[];
  counts: Record<string, number>;
}

export interface RagChunkExplorerItem {
  id: number;
  source_id: number;
  source_type: string;
  source_file?: string | null;
  reviewed_chunk_id?: number | string | null;
  content_type: string;
  page_number?: number | null;
  unit_id?: number | string | null;
  lesson_id?: number | string | null;
  topic_id?: number | null;
  printed_page_start?: number | null;
  printed_page_end?: number | null;
  quality_status?: string | null;
  reviewed_metadata_version?: string | null;
  embedding_status: string;
  embedding_model?: string | null;
  embedding_error?: string | null;
  content_hash?: string | null;
  missing_metadata: string[];
  embedding_allowed?: boolean;
  rag_search_allowed?: boolean;
  student_generation_allowed?: boolean;
  warning_required?: boolean;
  reason_codes?: string[];
  legacy_unmapped?: boolean;
  stale?: boolean;
  content_preview: string;
  metadata_json?: Record<string, unknown> | unknown[] | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RagChunkExplorerResponse {
  total: number;
  limit: number;
  offset: number;
  items: RagChunkExplorerItem[];
  counts: Record<string, number>;
  filtered_total?: number;
  global_counts?: Record<string, number>;
}

export interface RagChunkExplorerParams {
  source_type?: string;
  quality_status?: string;
  embedding_status?: string;
  unit_id?: string;
  lesson_id?: string;
  missing_metadata?: boolean;
  missing_metadata_field?: string;
  page_start?: number;
  page_end?: number;
  reviewed_metadata_version?: string;
  legacy_unmapped?: boolean;
  embedding_error?: string;
  content_type?: string;
  search?: string;
  limit?: number;
  offset?: number;
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

export interface LoadReviewedChunksResponse {
  status: string;
  clear_existing: boolean;
  dry_run: boolean;
  would_write: boolean;
  reviewed_metadata_version?: string | null;
  sources: Record<string, unknown>;
  chunks_deleted: number;
  chunks_inserted: number;
  chunks_updated: number;
  chunks_unchanged: number;
  chunks_stale: number;
  embedding_reset: number;
  skipped_blocked: number;
  skipped_missing_metadata: number;
  skipped_empty_content: number;
  embedding_status: string;
  next_step: string;
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
  reviewed_metadata_version?: string | null;
  skipped_missing_metadata_count?: number;
  skipped_blocked_count?: number;
  skipped_stale_count?: number;
  source_id?: number | null;
  source_type?: string | null;
  result?: Record<string, unknown> | null;
}

export interface RagPreflightResponse {
  status: string;
  database: {
    dialect: string;
    reachable: boolean;
    pgvector_available: boolean;
    pgvector_version?: string | null;
    embedding_dimension: number;
    vector_index_present: boolean;
    vector_index_name?: string | null;
    vector_index_type?: string | null;
    distance_operator?: string | null;
    vector_column_type?: string | null;
    vector_dimension_valid?: boolean;
  };
  provider: { provider: string; model: string; configured: boolean };
  reviewed_metadata: {
    exists: boolean;
    status: string;
    version?: string | null;
    ready_for_embedding: boolean;
    blocking_issues: string[];
  };
  sources: Record<string, boolean>;
  chunks: Record<string, number>;
  can_load_chunks: boolean;
  can_embed: boolean;
  can_evaluate: boolean;
  blocking_issues: string[];
  warnings: string[];
}

export interface RagEvaluationResponse {
  status: string;
  passed: boolean;
  reviewed_metadata_version?: string | null;
  embedding_model?: string | null;
  preconditions: Record<string, unknown>;
  report_json_path: string;
  report_markdown_path: string;
  metrics: Record<string, unknown>;
  threshold_failures: string[];
  failed_cases: Array<Record<string, unknown>>;
}

export interface RagQaResponse {
  status: string;
  reviewed_metadata_version?: string | null;
  embedding_model?: string | null;
  preconditions: Record<string, unknown>;
  metrics: Record<string, unknown>;
  threshold_failures: string[];
  failed_cases: Array<Record<string, unknown>>;
  report_json_path: string;
  report_markdown_path?: string | null;
}

export interface RagOperationsResponse {
  status: string;
  window_hours: number;
  active_reviewed_metadata_version?: string | null;
  embedding_model: string;
  student_retrieval_enabled: boolean;
  production_gate_required: boolean;
  production_gate_status: Record<string, unknown>;
  query_volume: number;
  no_result_rate: number;
  low_confidence_rate: number;
  average_retrieval_latency_ms: number;
  p95_retrieval_latency_ms: number;
  source_type_distribution: Record<string, number>;
  quality_status_counts: Record<string, number>;
  missing_citation_metadata_count: number;
  latest_embedding_job?: Record<string, unknown> | null;
  latest_evaluation?: Record<string, unknown> | null;
  latest_student_flow_qa?: Record<string, unknown> | null;
  degraded_reasons: string[];
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

  async getRagSources(): Promise<RagSourceStatus[]> {
    const { data } = await api.get<RagSourceStatus[]>('/admin/rag/sources');
    return data;
  },

  async getPreflight(): Promise<RagPreflightResponse> {
    const { data } = await api.get<RagPreflightResponse>('/admin/rag/preflight');
    return data;
  },

  async getRagSource(sourceId: string): Promise<RagSourceStatus> {
    const { data } = await api.get<RagSourceStatus>(`/admin/rag/sources/${sourceId}`);
    return data;
  },

  async scanRagSource(sourceId: string): Promise<RagSourceStatus> {
    const { data } = await api.post<RagSourceStatus>(`/admin/rag/sources/${sourceId}/scan`);
    return data;
  },

  async getRagChunks(params?: RagChunkExplorerParams): Promise<RagChunkExplorerResponse> {
    const { data } = await api.get<RagChunkExplorerResponse>('/admin/rag/chunks', { params });
    return data;
  },

  async getRagChunk(chunkId: number): Promise<RagChunkExplorerItem> {
    const { data } = await api.get<RagChunkExplorerItem>(`/admin/rag/chunks/${chunkId}`);
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

  async loadReviewedChunks(payload: { dry_run?: boolean; clear_existing?: boolean } = {}): Promise<LoadReviewedChunksResponse> {
    const { data } = await api.post<LoadReviewedChunksResponse>('/admin/ingestion/load-reviewed-chunks', {
      dry_run: payload.dry_run ?? true,
      clear_existing: payload.clear_existing ?? false,
      include_textbook: true,
      include_solution_book: true,
    });
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

  async getLatestQa(): Promise<RagQaResponse> {
    const { data } = await api.get<RagQaResponse>('/admin/rag/qa/latest');
    return data;
  },

  async getOperations(windowHours = 24): Promise<RagOperationsResponse> {
    const { data } = await api.get<RagOperationsResponse>('/admin/rag/operations', {
      params: { window_hours: windowHours },
    });
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
