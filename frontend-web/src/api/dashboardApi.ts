import { api } from './http';

export interface DashboardResponse {
  student_name: string;
  xp: number;
  level: number;
  streak_days: number;
  overall_progress: number;
  today_mission: string;
  continue_lesson?: {
    id?: number | null;
    title_ar: string;
    progress: number;
    duration_min: number;
    status: string;
  } | null;
  weak_topics: Array<{
    topic_id?: number | null;
    title_ar: string;
    best_quiz_score: number;
    reason: string;
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
    days_to_exam?: number | null;
    status?: string | null;
  } | null;
  notifications: {
    unread_count: number;
  };
  quick_tools: Array<{ label: string; route: string }>;
  data_quality: Record<string, unknown>;
  // Flat accessors for frontend parity.
  current_streak: number;
  lesson_progress_percentage: number;
  flashcards_due_count: number;
  weekly_xp: number;
}

export const dashboardApi = {
  async getDashboard(): Promise<DashboardResponse> {
    const { data } = await api.get<DashboardResponse>('/dashboard');
    return data;
  },
};
