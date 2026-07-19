import '@testing-library/jest-dom/vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { dashboardApi } from '../api';
import type { DashboardResponse } from '../api/dashboardApi';
import { DashboardPage } from './DashboardPage';

vi.mock('../api', () => ({
  dashboardApi: {
    getDashboard: vi.fn(),
  },
  toErrorMessage: (_error: unknown, fallback: string) => fallback,
}));

const mockedDashboardApi = vi.mocked(dashboardApi);

const dashboardResponse = (overrides: Partial<DashboardResponse> = {}): DashboardResponse => ({
  semantics_version: 'dashboard-progress-v1',
  generated_at: '2026-07-19T09:00:00Z',
  user_id: 1,
  student_name: 'سارة',
  xp: 320,
  level: 3,
  streak_days: 4,
  curriculum_progress: {
    total_lessons: 9,
    completed_lessons: 3,
    percent: 33,
  },
  active_plan_progress: {
    plan_id: 12,
    total_scheduled_lessons: 8,
    completed_lessons: 3,
    in_progress_lessons: 1,
    overdue_lessons: 1,
    percent: 38,
    next_lesson: {
      id: 4,
      title_ar: 'المحاليل الحمضية',
      scheduled_date: '2026-07-19',
      status: 'in_progress',
      estimated_minutes: 45,
    },
  },
  primary_mission: {
    kind: 'overdue_lesson',
    title_ar: 'لديك درس متأخر',
    description_ar: 'المحاليل المائية لم يكتمل بعد.',
    action_label_ar: 'ابدأ الدرس',
    action_url: '/study-session/1?planId=12',
    reason_code: 'OLDEST_OVERDUE_PLAN_LESSON',
    lesson_id: 1,
    study_plan_id: 12,
  },
  weak_topics_state: 'ready',
  continue_lesson: {
    id: 4,
    title_ar: 'المحاليل الحمضية',
    chapter_id: 1,
    chapter_title_ar: 'المحاليل',
    progress_percent: null,
    progress: null,
    duration_min: 45,
    status: 'in_progress',
  },
  weak_topics: [
    {
      topic_id: 9,
      title_ar: 'التركيز المولي',
      accuracy_percent: 60,
      answered_questions: 5,
      attempt_count: 1,
      last_evidence_at: '2026-07-18T09:00:00Z',
      evidence_level: 'limited',
      reason: 'دقة إجاباتك أقل من 70٪.',
      action_url: '/quiz?topicId=9',
      best_quiz_score: 60,
    },
  ],
  due_flashcards: {
    due_count: 2,
    mastered_count: 4,
    total_reviewed: 8,
  },
  next_quiz: {
    title: 'راجع اختبار التركيز المولي',
    topic_id: 9,
    score: 3,
    total: 5,
  },
  study_plan: {
    id: 12,
    days_to_exam: 14,
    status: 'active',
  },
  notifications: { unread_count: 1 },
  quick_tools: [
    { label: 'اسأل الذكاء', route: '/ask-ai' },
    { label: 'اختبار', route: '/quiz' },
  ],
  data_quality: {
    has_curriculum_data: true,
    has_lesson_progress: true,
    has_active_study_plan: true,
    has_plan_items: true,
    has_quiz_evidence: true,
    has_weak_topic_evidence: true,
    weak_topic_answer_count: 5,
    weekly_xp_available: false,
  },
  overall_progress: 33,
  today_mission: 'المحاليل المائية لم يكتمل بعد.',
  current_streak: 4,
  lesson_progress_percentage: 33,
  flashcards_due_count: 2,
  weekly_xp: null,
  ...overrides,
});

const renderPage = () => {
  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
};

describe('DashboardPage dashboard-progress-v1', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders a loading skeleton before dashboard values', () => {
    mockedDashboardApi.getDashboard.mockReturnValue(new Promise(() => undefined));

    renderPage();

    expect(screen.getByLabelText('جار تحميل لوحة التعلم')).toBeInTheDocument();
    expect(screen.queryByText('320 XP إجمالي')).not.toBeInTheDocument();
  });

  it('keeps curriculum and active-plan progress visibly separate', async () => {
    mockedDashboardApi.getDashboard.mockResolvedValue(dashboardResponse());

    renderPage();

    expect(await screen.findByText('تقدم المنهج')).toBeInTheDocument();
    expect(screen.getByText('تقدم الخطة')).toBeInTheDocument();
    expect(screen.getByText('33%')).toBeInTheDocument();
    expect(screen.getByText('38%')).toBeInTheDocument();
    expect(screen.getByText('3 من 9 دروس مكتملة')).toBeInTheDocument();
    expect(screen.getByText('3 من 8 دروس مكتملة')).toBeInTheDocument();
    const missionLink = screen
      .getAllByRole('link', { name: 'ابدأ الدرس' })
      .find((link) => link.getAttribute('href') === '/study-session/1?planId=12');
    expect(missionLink).toBeDefined();
  });

  it('shows lesson status instead of a fabricated 50 percent', async () => {
    mockedDashboardApi.getDashboard.mockResolvedValue(dashboardResponse());

    renderPage();

    expect(await screen.findByText('قيد الدراسة')).toBeInTheDocument();
    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('shows quiz evidence for weak topics', async () => {
    mockedDashboardApi.getDashboard.mockResolvedValue(dashboardResponse());

    renderPage();

    expect(await screen.findByText('التركيز المولي')).toBeInTheDocument();
    expect(screen.getByText('دقة 60%')).toBeInTheDocument();
    expect(screen.getByText('5 إجابات عبر 1 محاولات')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'تدرّب الآن' })).toHaveAttribute('href', '/quiz?topicId=9');
  });

  it('renders no-plan and insufficient-evidence states without zero-over-zero', async () => {
    mockedDashboardApi.getDashboard.mockResolvedValue(dashboardResponse({
      active_plan_progress: null,
      weak_topics_state: 'insufficient_evidence',
      weak_topics: [],
      study_plan: null,
      data_quality: {
        ...dashboardResponse().data_quality,
        has_active_study_plan: false,
        has_plan_items: false,
        has_quiz_evidence: false,
        has_weak_topic_evidence: false,
        weak_topic_answer_count: 0,
      },
    }));

    renderPage();

    expect(await screen.findByText('لم تُنشئ خطة تحتوي على دروس مجدولة بعد.')).toBeInTheDocument();
    expect(screen.getByText('أكمل اختباراً قصيراً لنحدد نقاط الضعف بدقة.')).toBeInTheDocument();
    expect(screen.queryByText(/0 من 0/)).not.toBeInTheDocument();
  });

  it('shows an Arabic retry state and never renders mock analytics after API failure', async () => {
    mockedDashboardApi.getDashboard
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(dashboardResponse());

    renderPage();

    expect(await screen.findByText('تعذر تحميل لوحة التعلم. تحقق من الاتصال ثم أعد المحاولة.')).toBeInTheDocument();
    expect(screen.getByText('لن نعرض قيماً تجريبية بدلاً من بياناتك الحقيقية.')).toBeInTheDocument();
    expect(screen.queryByText('1240 XP')).not.toBeInTheDocument();
    expect(screen.queryByText('الحموض الضعيفة')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'إعادة المحاولة' }));

    await waitFor(() => expect(mockedDashboardApi.getDashboard).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('320 XP إجمالي')).toBeInTheDocument();
  });
});
