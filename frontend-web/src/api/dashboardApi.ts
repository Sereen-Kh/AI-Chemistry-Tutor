import { api } from './http';

export type DashboardLessonStatus = 'not_started' | 'in_progress' | 'completed';
export type DashboardWeakTopicsState = 'ready' | 'insufficient_evidence';
export type DashboardMissionKind =
  | 'overdue_lesson'
  | 'today_lesson'
  | 'due_flashcards'
  | 'next_lesson'
  | 'create_plan';

export interface DashboardCurriculumProgress {
  total_lessons: number;
  completed_lessons: number;
  percent: number | null;
}

export interface DashboardPlanLesson {
  id: number;
  title_ar: string;
  scheduled_date?: string | null;
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped' | 'overdue';
  estimated_minutes: number;
}

export interface DashboardActivePlanProgress {
  plan_id: number;
  total_scheduled_lessons: number;
  completed_lessons: number;
  in_progress_lessons: number;
  overdue_lessons: number;
  percent: number | null;
  next_lesson?: DashboardPlanLesson | null;
}

export interface DashboardPrimaryMission {
  kind: DashboardMissionKind;
  title_ar: string;
  description_ar: string;
  action_label_ar: string;
  action_url: string;
  reason_code: string;
  lesson_id?: number | null;
  study_plan_id?: number | null;
}

export interface DashboardResponse {
  semantics_version: 'dashboard-progress-v1';
  generated_at: string;
  user_id: number;
  student_name: string;
  xp: number;
  level: number;
  streak_days: number;
  curriculum_progress: DashboardCurriculumProgress;
  active_plan_progress?: DashboardActivePlanProgress | null;
  primary_mission: DashboardPrimaryMission;
  weak_topics_state: DashboardWeakTopicsState;
  continue_lesson?: {
    id?: number | null;
    title_ar: string;
    chapter_id?: number | null;
    chapter_title_ar?: string | null;
    progress_percent?: number | null;
    duration_min: number;
    status: DashboardLessonStatus;
    progress?: number | null;
  } | null;
  weak_topics: Array<{
    topic_id: number;
    title_ar: string;
    accuracy_percent: number;
    answered_questions: number;
    attempt_count: number;
    last_evidence_at?: string | null;
    evidence_level: 'limited' | 'established';
    reason: string;
    action_url: string;
    best_quiz_score?: number | null;
  }>;
  due_flashcards: {
    due_count: number;
    mastered_count: number;
    total_reviewed: number;
  };
  next_quiz?: {
    title: string;
    topic_id?: number | null;
    score?: number | null;
    total?: number | null;
  } | null;
  study_plan?: {
    id?: number | null;
    exam_date?: string | null;
    days_to_exam?: number | null;
    status?: string | null;
  } | null;
  notifications: {
    unread_count: number;
  };
  quick_tools: Array<{ label: string; route: string }>;
  data_quality: {
    has_curriculum_data: boolean;
    has_lesson_progress: boolean;
    has_active_study_plan: boolean;
    has_plan_items: boolean;
    has_quiz_evidence: boolean;
    has_weak_topic_evidence: boolean;
    weak_topic_answer_count: number;
    weekly_xp_available: boolean;
  };
  // Deprecated compatibility projections. New UI must not consume these.
  overall_progress?: number | null;
  today_mission?: string;
  current_streak?: number;
  lesson_progress_percentage?: number | null;
  flashcards_due_count?: number;
  weekly_xp?: number | null;
}

export const dashboardApi = {
  async getDashboard(): Promise<DashboardResponse> {
    const { data } = await api.get<DashboardResponse>('/dashboard');
    return data;
  },
};
