import '@testing-library/jest-dom/vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { adminRagApi } from '../../api';
import { SourcesPage } from './SourcesPage';
import type { RagSourceStatus } from '../../api/adminRagApi';

vi.mock('../../api', () => ({
  adminRagApi: {
    getRagSources: vi.fn(),
    getStats: vi.fn(),
    getSourcePages: vi.fn(),
    scanRagSource: vi.fn(),
  },
  toErrorMessage: (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback),
}));

const mockedAdminRagApi = vi.mocked(adminRagApi);

const textbookSource: RagSourceStatus = {
  id: 'textbook',
  db_source_id: null,
  source_type: 'textbook',
  file_path: 'src/data/textbooks/syria_grade_9/Chemistry.pdf',
  filename: 'Chemistry.pdf',
  checksum_sha256: '3e94fe8be9d4c750c0253d3b81dc12ddf826ec6c901a2def17427d32cb5f9187',
  page_count: 96,
  file_size_bytes: 111_704_064,
  last_modified_at: '2026-07-04T09:10:00+00:00',
  ingestion_status: 'not_registered',
  extraction_status: 'complete',
  chunk_status: 'partial',
  embedding_status: 'not_embedded',
  errors: [],
  warnings: ['missing_chunk_pages:7'],
  counts: {
    extraction_pages: 96,
    reviewed_chunks: 720,
    chunked_pages: 89,
    missing_chunk_pages: 7,
    ready_chunks: 670,
    needs_review_chunks: 50,
  },
};

const solutionSource: RagSourceStatus = {
  id: 'solution_book',
  db_source_id: 2,
  source_type: 'solution_book',
  file_path: 'src/data/processed/Chemistry_Solution_Book.pdf',
  filename: 'Chemistry_Solution_Book.pdf',
  checksum_sha256: '2b8ed4051308d3f52d8fb1c33ffc8da50f539db882624ef318a9b68dedd9b1c0',
  page_count: 35,
  file_size_bytes: 834_560,
  last_modified_at: '2026-07-04T09:10:00+00:00',
  ingestion_status: 'reviewed_source_ready',
  extraction_status: 'complete',
  chunk_status: 'complete',
  embedding_status: 'not_embedded',
  errors: [],
  warnings: [],
  counts: {
    extraction_pages: 35,
    reviewed_chunks: 24,
    chunked_pages: 35,
    missing_chunk_pages: 0,
    ready_chunks: 7,
    needs_review_chunks: 17,
  },
};

describe('SourcesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAdminRagApi.getRagSources.mockResolvedValue([textbookSource, solutionSource]);
    mockedAdminRagApi.getStats.mockResolvedValue({
      total_chunks: 0,
      total_sources: 0,
      total_questions: 0,
      reviewed_questions: 0,
      unreviewed_questions: 0,
      chunks_by_chapter: {},
      chunks_by_source_type: {},
      avg_chunk_length: 0,
      pages_processed: 0,
    });
    mockedAdminRagApi.getSourcePages.mockResolvedValue([]);
    mockedAdminRagApi.scanRagSource.mockResolvedValue({ ...textbookSource, db_source_id: 1, ingestion_status: 'reviewed_source_ready' });
  });

  it('renders both canonical PDF sources with status metadata', async () => {
    render(<SourcesPage />);

    expect((await screen.findAllByText(/Chemistry\.pdf/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Chemistry_Solution_Book\.pdf/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('كتاب الكيمياء').length).toBeGreaterThan(0);
    expect(screen.getAllByText('كتاب الحلول').length).toBeGreaterThan(0);
    expect(screen.getByText(/96.*صفحة/)).toBeInTheDocument();
    expect(screen.getByText(/35.*صفحة/)).toBeInTheDocument();
    expect(screen.getAllByText('partial').length).toBeGreaterThan(0);
    expect(screen.getByText('missing_chunk_pages:7')).toBeInTheDocument();
  });

  it('scans a source and refreshes the source list', async () => {
    const user = userEvent.setup();
    render(<SourcesPage />);

    await screen.findAllByText(/Chemistry\.pdf/);
    await user.click(screen.getAllByRole('button', { name: 'Scan' })[0]);

    await waitFor(() => {
      expect(mockedAdminRagApi.scanRagSource).toHaveBeenCalledWith('textbook');
    });
    expect(mockedAdminRagApi.getRagSources).toHaveBeenCalledTimes(2);
  });
});
