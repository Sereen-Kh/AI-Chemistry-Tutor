import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { curriculumApi } from '../api';
import { quizzesApi } from '../api/quizzesApi';
import type { UnitCatalogItem } from '../types';
import { QuizzesPage } from './QuizzesPage';

vi.mock('../config/demoFallbacks', () => ({
  allowDemoFallbacks: false,
}));

vi.mock('../api', () => ({
  curriculumApi: { getUnits: vi.fn() },
  fallbackCurriculumUnits: [
    {
      id: 4,
      unit_number: 4,
      semester: 1,
      title_ar: 'وحدة تجريبية يجب ألا تظهر',
      order: 4,
      chapters: [],
    },
  ],
}));

vi.mock('../api/quizzesApi', () => ({
  quizGenerationErrorMessage: () => 'تعذر توليد الأسئلة من الخادم حالياً.',
  quizzesApi: {
    generateQuiz: vi.fn(),
    submitQuizResult: vi.fn(),
  },
}));

const mockedCurriculumApi = vi.mocked(curriculumApi);
const mockedQuizzesApi = vi.mocked(quizzesApi);

const reviewedUnit: UnitCatalogItem = {
  id: 14,
  unit_number: 4,
  semester: 1,
  title_ar: 'الكيمياء اللاعضوية',
  order: 4,
  chapters: [
    {
      id: 41,
      unit_id: 14,
      title_ar: 'المحاليل والتفاعلات اللاعضوية',
      order: 1,
      difficulty: 2,
      lessons: [
        {
          id: 401,
          chapter_id: 41,
          title_ar: 'المحاليل المائية',
          content_ar: 'محتوى مستورد من المنهج المُراجع',
          order: 1,
          difficulty: 2,
          duration_min: 45,
          page_start: 108,
          page_end: 115,
          topics: [
            {
              id: 4011,
              title_ar: 'التركيز المولي',
              difficulty: 1,
              order: 1,
            },
          ],
        },
      ],
    },
  ],
};

const renderPage = (entry = '/quiz') => {
  render(
    <MemoryRouter initialEntries={[entry]}>
      <QuizzesPage />
    </MemoryRouter>,
  );
};

afterEach(cleanup);

describe('QuizzesPage curriculum readiness', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render fallback lessons or auto-generate when curriculum is empty', async () => {
    mockedCurriculumApi.getUnits.mockResolvedValue([]);

    renderPage('/quiz?auto=true&lessonId=401');

    expect(await screen.findByText(/لا توجد بيانات منهج مستوردة/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'لا توجد دروس متاحة لتكوين اختبار' })).toBeInTheDocument();
    expect(screen.queryByText('وحدة تجريبية يجب ألا تظهر')).not.toBeInTheDocument();
    expect(screen.queryByText('تعذر تحميل بيانات الدرس المحدد.')).not.toBeInTheDocument();
    expect(mockedQuizzesApi.generateQuiz).not.toHaveBeenCalled();
  });

  it('reloads curriculum after a server failure', async () => {
    mockedCurriculumApi.getUnits
      .mockRejectedValueOnce(new Error('server unavailable'))
      .mockResolvedValueOnce([reviewedUnit]);

    renderPage();

    expect(await screen.findByText(/تعذر تحميل المنهج من الخادم/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'إعادة المحاولة' }));

    expect(await screen.findByText('المحاليل المائية')).toBeInTheDocument();
    await waitFor(() => expect(mockedCurriculumApi.getUnits).toHaveBeenCalledTimes(2));
  });
});
