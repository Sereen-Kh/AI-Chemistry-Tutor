import { describe, expect, it, vi, beforeEach } from 'vitest';

import { studyPlanApi } from './api/studyPlanApi';
import { api } from './api/http';

vi.mock('./api/http', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

vi.mock('./api/curriculumApi', () => ({
  fallbackCurriculumUnits: [],
}));

const mockedApi = vi.mocked(api);

describe('studyPlanApi real backend behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when backend has no study plans', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: [] });

    await expect(studyPlanApi.getActiveStudyPlan()).resolves.toBeNull();
  });

  it('does not fabricate an active plan when listing plans fails', async () => {
    mockedApi.get.mockRejectedValueOnce(new Error('network down'));

    await expect(studyPlanApi.getActiveStudyPlan()).rejects.toThrow('network down');
  });

  it('does not generate a local fallback plan when backend generation fails', async () => {
    mockedApi.get.mockResolvedValueOnce({ data: [] });
    mockedApi.post.mockRejectedValueOnce(new Error('server down'));

    await expect(studyPlanApi.generateStudyPlan({
      startDate: '2026-07-03',
      endDate: '2026-08-01',
      studyDays: ['sun'],
      lessonIds: [1],
      lessonDuration: '60',
      weeklyRest: 'none',
    })).rejects.toThrow('تعذر إنشاء خطة الدراسة من الخادم');
  });
});
