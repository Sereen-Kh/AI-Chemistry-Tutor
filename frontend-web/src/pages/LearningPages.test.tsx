import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { curriculumApi } from '../api';
import type { UnitCatalogItem } from '../types';
import { LessonsPage } from './LearningPages';

vi.mock('../config/demoFallbacks', () => ({
  allowDemoFallbacks: false,
}));

vi.mock('../api', () => ({
  aiApi: { ask: vi.fn() },
  curriculumApi: { getUnits: vi.fn() },
  fallbackCurriculumUnits: [
    {
      id: 4,
      unit_number: 4,
      semester: 1,
      title_ar: 'الكيمياء اللاعضوية التجريبية',
      order: 4,
      chapters: [],
    },
  ],
}));

const mockedCurriculumApi = vi.mocked(curriculumApi);

const reviewedUnit: UnitCatalogItem = {
  id: 14,
  unit_number: 4,
  semester: 1,
  title_ar: 'الكيمياء اللاعضوية',
  description_ar: 'محتوى المنهج المستورد',
  order: 4,
  chapters: [
    {
      id: 41,
      unit_id: 14,
      title_ar: 'المحاليل والتفاعلات اللاعضوية',
      order: 1,
      difficulty: 2,
      lessons: [],
    },
  ],
};

const renderPage = () => {
  render(
    <MemoryRouter>
      <LessonsPage />
    </MemoryRouter>,
  );
};

afterEach(cleanup);

describe('LessonsPage curriculum loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('does not show demo curriculum when the production API returns no units', async () => {
    mockedCurriculumApi.getUnits.mockResolvedValue([]);

    renderPage();

    expect(await screen.findByText(/لا توجد بيانات منهج مستوردة/)).toBeInTheDocument();
    expect(screen.queryByText('الكيمياء اللاعضوية التجريبية')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'إعادة المحاولة' })).toBeInTheDocument();
  });

  it('renders curriculum returned by the backend', async () => {
    mockedCurriculumApi.getUnits.mockResolvedValue([reviewedUnit]);

    renderPage();

    expect(await screen.findByText('الكيمياء اللاعضوية')).toBeInTheDocument();
    expect(screen.getByText('محتوى المنهج المستورد')).toBeInTheDocument();
    expect(screen.queryByText(/بيانات تجريبية/)).not.toBeInTheDocument();
  });

  it('retries after an API failure', async () => {
    mockedCurriculumApi.getUnits
      .mockRejectedValueOnce(new Error('server unavailable'))
      .mockResolvedValueOnce([reviewedUnit]);

    renderPage();

    expect(await screen.findByText(/تعذر تحميل بنية الكتاب/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'إعادة المحاولة' }));

    expect(await screen.findByText('الكيمياء اللاعضوية')).toBeInTheDocument();
    expect(mockedCurriculumApi.getUnits).toHaveBeenCalledTimes(2);
  });
});
