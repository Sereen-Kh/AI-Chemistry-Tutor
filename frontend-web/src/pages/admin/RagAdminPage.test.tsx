import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import { adminRagApi } from '../../api';
import type { RagPreflightResponse, RagSourceStatus } from '../../api/adminRagApi';
import { RagAdminPage } from './RagAdminPage';

vi.mock('../../api', () => ({
  adminRagApi: {
    getStats: vi.fn(),
    getSources: vi.fn(),
    getQueryLogs: vi.fn(),
    getEmbeddingReadiness: vi.fn(),
    getPreflight: vi.fn(),
    getRagSources: vi.fn(),
    getLatestEvaluation: vi.fn(),
    getLatestQa: vi.fn(),
    getOperations: vi.fn(),
    getReembedStatus: vi.fn(),
  },
  toErrorMessage: (_error: unknown, fallback: string) => fallback,
}));

const mockedApi = vi.mocked(adminRagApi);

const source: RagSourceStatus = {
  id: 'textbook',
  source_type: 'textbook',
  file_path: 'src/data/textbooks/syria_grade_9/Chemistry.pdf',
  filename: 'Chemistry.pdf',
  page_count: 96,
  ingestion_status: 'not_registered',
  extraction_status: 'complete',
  chunk_status: 'partial',
  embedding_status: 'not_embedded',
  errors: [],
  warnings: [],
  counts: { reviewed_chunks: 720 },
};

const preflight = (overrides: Partial<RagPreflightResponse> = {}): RagPreflightResponse => ({
  status: 'degraded',
  database: {
    dialect: 'postgresql',
    reachable: true,
    pgvector_available: true,
    embedding_dimension: 768,
    vector_index_present: true,
    vector_index_type: 'ivfflat',
    distance_operator: 'vector_cosine_ops',
  },
  provider: { provider: 'gemini', model: 'gemini-embedding-001', configured: true },
  reviewed_metadata: {
    exists: true,
    status: 'reviewed',
    version: '2026-06-reviewed-v1',
    ready_for_embedding: true,
    blocking_issues: [],
  },
  sources: { textbook_found: true, solution_book_found: true },
  chunks: {
    ready_chunks: 677,
    needs_review_chunks: 67,
    blocked_chunks: 0,
    pending_embeddings: 744,
    processing_embeddings: 0,
    completed_embeddings: 0,
    failed_embeddings: 0,
  },
  can_load_chunks: true,
  can_embed: true,
  can_evaluate: false,
  blocking_issues: [],
  warnings: ['EMBEDDING_INDEX_EMPTY'],
  ...overrides,
});

describe('RagAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.getStats.mockResolvedValue({
      total_chunks: 744,
      total_sources: 2,
      total_questions: 0,
      reviewed_questions: 0,
      unreviewed_questions: 0,
      chunks_by_chapter: {},
      chunks_by_source_type: { textbook: 720, solution_book: 24 },
      avg_chunk_length: 0,
      pages_processed: 131,
    });
    mockedApi.getSources.mockResolvedValue([]);
    mockedApi.getQueryLogs.mockResolvedValue([]);
    mockedApi.getEmbeddingReadiness.mockResolvedValue({
      status: 'reviewed',
      ready_for_embedding: true,
      blocking_issues: [],
      required_chunk_metadata: [],
      allowed_source_types: ['textbook', 'solution_book'],
      embedding_model: 'gemini-embedding-001',
      embedding_dimension: 768,
      vector_store: 'pgvector',
      vector_index: 'ivfflat/cosine',
      textbook_chunks_total: 720,
      textbook_missing_metadata_count: 0,
      solution_chunks_total: 24,
      solution_manual_review_count: 17,
      solution_bad_endings_count: 0,
      ready_chunk_count: 677,
      needs_review_chunk_count: 67,
      blocked_chunk_count: 0,
    });
    mockedApi.getPreflight.mockResolvedValue(preflight());
    mockedApi.getRagSources.mockResolvedValue([source]);
    mockedApi.getLatestEvaluation.mockRejectedValue(new Error('no evaluation'));
    mockedApi.getLatestQa.mockResolvedValue({
      status: 'passed',
      reviewed_metadata_version: '2026-06-reviewed-v1',
      embedding_model: 'gemini-embedding-001',
      preconditions: { mode: 'unit' },
      metrics: { overall_pass_rate: 1 },
      threshold_failures: [],
      failed_cases: [],
      report_json_path: 'reports/rag_qa_report.json',
    });
    mockedApi.getOperations.mockResolvedValue({
      status: 'degraded',
      window_hours: 24,
      last_updated_at: '2026-07-13T08:00:00Z',
      active_reviewed_metadata_version: '2026-06-reviewed-v1',
      embedding_model: 'gemini-embedding-001',
      student_retrieval_enabled: true,
      production_gate_required: false,
      production_gate_status: {},
      preflight_status: 'ready',
      total_eligible_chunks: 744,
      embedded_eligible_chunks: 744,
      embedding_completion_rate: 1,
      ready_chunks: 629,
      needs_review_chunks: 115,
      blocked_chunks: 0,
      stale_chunks: 0,
      query_volume: 12,
      no_result_rate: 0.1,
      low_confidence_rate: 0.2,
      average_retrieval_latency_ms: 125,
      p95_retrieval_latency_ms: 240,
      source_type_distribution: { textbook: 10, solution_book: 2 },
      quality_status_counts: { ready: 11, needs_review: 1 },
      missing_citation_metadata_count: 0,
      degraded_reasons: ['RAG_EVALUATION_REPORT_MISSING'],
    });
  });

  it('shows readiness counts and empty-index warning without starting a job', async () => {
    render(<MemoryRouter><RagAdminPage /></MemoryRouter>);

    expect(await screen.findByText('سير عمل الإدخال المراجَع')).toBeInTheDocument();
    expect(screen.getByText(/EMBEDDING_INDEX_EMPTY/)).toBeInTheDocument();
    expect(screen.getAllByText('677').length).toBeGreaterThan(0);
    expect(mockedApi.getReembedStatus).not.toHaveBeenCalled();
    expect(screen.getByText('تشغيل RAG في الإنتاج')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getAllByText('744').length).toBeGreaterThan(0);
  });

  it('disables write actions when preflight is blocked', async () => {
    mockedApi.getPreflight.mockResolvedValue(preflight({
      status: 'blocked',
      can_load_chunks: false,
      can_embed: false,
      blocking_issues: ['REVIEWED_METADATA_NOT_READY'],
      warnings: [],
    }));

    render(<MemoryRouter><RagAdminPage /></MemoryRouter>);

    expect(await screen.findByText(/REVIEWED_METADATA_NOT_READY/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'تحميل المقاطع المراجعة' }).some((button) => button.hasAttribute('disabled'))).toBe(true);
    expect(screen.getAllByRole('button', { name: 'بدء التضمين' }).some((button) => button.hasAttribute('disabled'))).toBe(true);
  });
});
