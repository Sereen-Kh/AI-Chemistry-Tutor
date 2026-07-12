import axios from 'axios';
import { api } from './http';
import { fallbackCurriculumUnits } from './curriculumApi';
import { allowDemoFallbacks, demoFallbackDisabledMessage } from '../config/demoFallbacks';
import type {
  ChapterPlan,
  ExamPlanConfig,
  LessonItem,
  SemesterPlanConfig,
  StudyPlan,
  StudyPlanProgress,
  StudyPlanSummary,
  StudyScheduleEntry,
  UnitCatalogItem,
} from '../types';

interface BackendStudyPlanResponse {
  id: number;
  exam_date?: string | null;
  plan_json?: {
    chapters?: ChapterPlan[];
    weakTopics?: string[];
    currentLesson?: LessonPlanLike | null;
    schedule?: StudyScheduleEntry[];
    summary?: StudyPlanSummary;
    config?: Record<string, unknown>;
    [key: string]: unknown;
  } | null;
  status: string;
}

type LessonPlanLike = {
  id: number;
  title: string;
  duration: number;
  status: ChapterPlan['lessons'][number]['status'];
};

const colors: ChapterPlan['color'][] = ['blue', 'teal', 'gold', 'purple', 'coral'];

type StudyPlanGenerationConfig = SemesterPlanConfig | ExamPlanConfig;
type StudyPlanUpdate = Partial<StudyPlan> & Record<string, unknown>;

// Small client-side cache for the last backend plan response.
let activePlan: StudyPlan | null = null;

const validationMessageFrom422 = (error: unknown): string => {
  if (!axios.isAxiosError(error)) return 'فشل في إنشاء خطة الدراسة.';
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg ?? JSON.stringify(item)).join('، ');
  }
  return 'تعذر إنشاء الخطة بسبب بيانات غير صحيحة.';
};

const normalizeGenerationConfig = (config: StudyPlanGenerationConfig): StudyPlanGenerationConfig => {
  const lessonIds = (config.lessonIds ?? []).filter((id) => String(id).trim().length > 0);
  if (lessonIds.length === 0) {
    throw new Error('يجب اختيار درس واحد على الأقل لإنشاء خطة الدراسة.');
  }
  return {
    ...config,
    lessonIds,
  };
};

const firstScheduledLesson = (schedule: StudyScheduleEntry[] = []): LessonItem | null => {
  for (const entry of schedule) {
    const session = entry.sessions.find((item) => item.type === 'lesson' && item.lesson_id);
    if (session?.lesson_id) {
      return {
        id: session.lesson_id,
        title: session.title,
        duration: session.minutes || 45,
        status: session.completed || session.status === 'completed' ? 'completed' : 'current',
      };
    }
  }
  return null;
};

const mapBackendStudyPlan = (response: BackendStudyPlanResponse, fallback?: StudyPlan): StudyPlan => {
  const payload = response.plan_json || {};
  const schedule = Array.isArray(payload.schedule) ? payload.schedule : fallback?.schedule;
  const chapters = Array.isArray(payload.chapters) && payload.chapters.length ? payload.chapters : fallback?.chapters ?? [];
  const currentLesson = (payload.currentLesson || chapters[0]?.lessons[0] || firstScheduledLesson(schedule) || {
    id: 0,
    title: 'لا يوجد درس محدد',
    duration: 0,
    status: 'locked',
  }) as LessonItem;
  return {
    id: String(response.id),
    chapters,
    weakTopics: Array.isArray(payload.weakTopics) ? payload.weakTopics : fallback?.weakTopics ?? [],
    currentLesson,
    schedule,
    summary: typeof payload.summary === 'object' && payload.summary ? payload.summary as StudyPlanSummary : fallback?.summary,
    config: {
      ...(typeof payload.config === 'object' && payload.config ? payload.config : {}),
      title: typeof payload.title === 'string' ? payload.title : fallback?.config?.title,
      examDate: response.exam_date || undefined,
      status: response.status,
    },
  };
};

const mapUnitsToStudyPlan = (units: UnitCatalogItem[]): StudyPlan => {
  let lessonCursor = 0;
  const chapters: ChapterPlan[] = units.flatMap((unit, unitIndex) =>
    unit.chapters.map((chapter, chapterIndex) => {
      const lessons: LessonItem[] = chapter.lessons.map((lesson) => {
        lessonCursor += 1;
        return {
          id: lesson.id,
          title: lesson.title_ar,
          duration: lesson.duration_min || 45,
          status: lessonCursor <= 3 ? 'completed' : lessonCursor === 4 ? 'current' : lesson.difficulty >= 3 ? 'weak' : 'locked',
        };
      });
      const completedCount = lessons.filter((lesson) => lesson.status === 'completed').length;
      return {
        id: chapter.id,
        title: chapter.title_ar,
        subtitle: `الوحدة ${unit.unit_number} · ${unit.semester === 1 ? 'الفصل الأول' : 'الفصل الثاني'} · ${lessons.length} دروس`,
        progress: lessons.length ? Math.round((completedCount / lessons.length) * 100) : 0,
        color: colors[(unitIndex + chapterIndex) % colors.length],
        lessons,
      };
    }),
  );
  const allLessons = chapters.flatMap((chapter) => chapter.lessons);
  return {
    chapters,
    weakTopics: allLessons.filter((lesson) => lesson.status === 'weak').slice(0, 3).map((lesson) => lesson.title),
    currentLesson: allLessons.find((lesson) => lesson.status === 'current') ?? allLessons[0] ?? {
      id: 0,
      title: 'لا يوجد درس محدد',
      duration: 0,
      status: 'locked',
    },
  };
};

export const studyPlanApi = {
  async getActiveStudyPlan(): Promise<StudyPlan | null> {
    const { data: backendPlans } = await api.get<BackendStudyPlanResponse[]>('/study-plans');
    const activeBackendPlan = backendPlans.find((plan) => plan.status === 'active') ?? backendPlans[0] ?? null;
    if (!activeBackendPlan) {
      activePlan = null;
      return null;
    }
    const basePlan = await this.getCurriculumBackedPlanOrNull();
    activePlan = mapBackendStudyPlan(activeBackendPlan, basePlan ?? undefined);
    return activePlan;
  },

  async getCurriculumBackedPlan(): Promise<StudyPlan> {
    try {
      const { data: units } = await api.get<UnitCatalogItem[]>('/units');
      if (units.length) return mapUnitsToStudyPlan(units);
      if (allowDemoFallbacks) return mapUnitsToStudyPlan(fallbackCurriculumUnits);
      throw new Error('لا توجد بيانات منهج متاحة من الخادم.');
    } catch (error) {
      if (allowDemoFallbacks) return mapUnitsToStudyPlan(fallbackCurriculumUnits);
      if (error instanceof Error && error.message === 'لا توجد بيانات منهج متاحة من الخادم.') throw error;
      throw new Error(demoFallbackDisabledMessage, { cause: error });
    }
  },

  async getCurriculumBackedPlanOrNull(): Promise<StudyPlan | null> {
    try {
      return await this.getCurriculumBackedPlan();
    } catch {
      return null;
    }
  },

  async getStudyPlanProgress(planId: string | number, planFallback?: StudyPlan): Promise<StudyPlanProgress> {
    try {
      const { data } = await api.get<StudyPlanProgress>(`/study-plans/${planId}/progress`);
      return data;
    } catch (error) {
      if (allowDemoFallbacks && planFallback) {
        const lessons = planFallback.chapters.flatMap((chapter) => chapter.lessons);
        const completed = lessons.filter((lesson) => lesson.status === 'completed').length;
        return {
          plan_id: Number(planId),
          plan_title: planFallback.config?.title || 'خطة الدراسة',
          total_scheduled_lessons: lessons.length,
          completed_lessons: completed,
          in_progress_lessons: lessons.filter((lesson) => lesson.status === 'current').length,
          not_started_lessons: lessons.filter((lesson) => lesson.status === 'locked').length,
          overdue_lessons: 0,
          completion_percent: lessons.length ? Math.round((completed / lessons.length) * 100) : 0,
          expected_percent: 0,
          track_status: 'on_track',
          next_lesson: null,
          unit_progress: [],
          scheduled_lessons: [],
        };
      }
      throw new Error('تعذر تحميل تقدّم خطة الدراسة من الخادم.', { cause: error });
    }
  },

  async getStudyPlan(): Promise<StudyPlan> {
    if (activePlan) return activePlan;

    const plan = await this.getActiveStudyPlan();
    if (!plan) throw new Error('لا توجد خطة دراسة نشطة.');
    return plan;
  },

  async getStudyPlans(): Promise<StudyPlan[]> {
    const [{ data: backendPlans }, basePlan] = await Promise.all([
      api.get<BackendStudyPlanResponse[]>('/study-plans'),
      this.getCurriculumBackedPlanOrNull(),
    ]);
    return backendPlans.map((plan) => mapBackendStudyPlan(plan, basePlan ?? undefined));
  },

  async generatePlan(config: StudyPlanGenerationConfig): Promise<StudyPlan> {
    const normalizedConfig = normalizeGenerationConfig(config);
    try {
      const [basePlan, response] = await Promise.all([
        this.getCurriculumBackedPlanOrNull(),
        api.post<BackendStudyPlanResponse>('/study-plans/generate', normalizedConfig),
      ]);
      activePlan = mapBackendStudyPlan(response.data, basePlan ?? undefined);
      return activePlan;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 422) {
        throw new Error(validationMessageFrom422(error), { cause: error });
      }
      throw new Error('تعذر إنشاء خطة الدراسة من الخادم. تحقق من الاتصال وحاول مرة أخرى.', { cause: error });
    }
  },

  async generateStudyPlan(config: StudyPlanGenerationConfig): Promise<StudyPlan> {
    return this.generatePlan(config);
  },

  async updateStudyPlan(id: string, updates: StudyPlanUpdate): Promise<StudyPlan> {
    const { data } = await api.put<BackendStudyPlanResponse>(`/study-plans/${id}`, {
      plan_json: updates,
    });
    activePlan = mapBackendStudyPlan(data, activePlan ?? undefined);
    return activePlan;
  },

  async patchStudyPlan(id: string, updates: StudyPlanUpdate): Promise<StudyPlan> {
    return this.updateStudyPlan(id, updates);
  },

  async completeLesson(planId: string, lessonId: number | string): Promise<StudyPlan> {
    const { data } = await api.post<BackendStudyPlanResponse>(`/study-plans/${planId}/lessons/${lessonId}/complete`);
    activePlan = mapBackendStudyPlan(data, activePlan ?? undefined);
    return activePlan;
  },

  async completeStudyPlanLesson(planId: string, lessonId: number | string): Promise<StudyPlan> {
    return this.completeLesson(planId, lessonId);
  }
};
