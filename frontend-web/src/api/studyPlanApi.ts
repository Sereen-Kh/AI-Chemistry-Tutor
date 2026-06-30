import axios from 'axios';
import { api } from './http';
import { fallbackCurriculumUnits } from './curriculumApi';
import { mockStudyPlan } from './mockData';
import type {
  ChapterPlan,
  ExamPlanConfig,
  LessonItem,
  SemesterPlanConfig,
  StudyPlan,
  StudyPlanProgress,
  StudyPlanProgressStatus,
  StudyPlanScheduledLessonProgress,
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

// In-memory active plan simulation
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

const mapBackendStudyPlan = (response: BackendStudyPlanResponse, fallback: StudyPlan): StudyPlan => {
  const payload = response.plan_json || {};
  const chapters = Array.isArray(payload.chapters) && payload.chapters.length ? payload.chapters : fallback.chapters;
  const currentLesson = (payload.currentLesson || chapters[0]?.lessons[0] || fallback.currentLesson) as LessonItem;
  return {
    id: String(response.id),
    chapters,
    weakTopics: Array.isArray(payload.weakTopics) ? payload.weakTopics : fallback.weakTopics,
    currentLesson,
    schedule: Array.isArray(payload.schedule) ? payload.schedule : fallback.schedule,
    summary: typeof payload.summary === 'object' && payload.summary ? payload.summary as StudyPlanSummary : fallback.summary,
    config: {
      ...(typeof payload.config === 'object' && payload.config ? payload.config : {}),
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
    currentLesson: allLessons.find((lesson) => lesson.status === 'current') ?? allLessons[0] ?? mockStudyPlan.currentLesson,
  };
};

const toDateKey = (value?: string | null): string | null => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toISOString().slice(0, 10);
};

const expectedPercentFromPlan = (plan: StudyPlan): number => {
  const startKey = plan.summary?.start_date ?? plan.config?.startDate;
  const endKey = plan.summary?.end_date ?? plan.config?.endDate ?? plan.config?.examDate;
  if (!startKey || !endKey) return 0;
  const start = new Date(String(startKey));
  const end = new Date(String(endKey));
  const today = new Date();
  start.setHours(0, 0, 0, 0);
  end.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) return 0;
  if (today <= start) return 0;
  if (today >= end) return 100;
  return Math.round(((today.getTime() - start.getTime()) / (end.getTime() - start.getTime())) * 1000) / 10;
};

const trackStatusFromProgress = (actual: number, expected: number): StudyPlanProgress['track_status'] => {
  if (actual >= expected + 10) return 'ahead';
  if (actual >= expected - 10) return 'on_track';
  return 'behind';
};

type LocalScheduledLessonProgress = StudyPlanScheduledLessonProgress & { unit_key: string };

const calculateStudyPlanProgress = (plan: StudyPlan): StudyPlanProgress => {
  const lessonLookup = new Map<number, { title: string; chapterTitle: string; unitTitle: string }>();
  plan.chapters.forEach((chapter) => {
    chapter.lessons.forEach((lesson) => {
      lessonLookup.set(lesson.id, {
        title: lesson.title,
        chapterTitle: chapter.title,
        unitTitle: chapter.subtitle?.split('·')[0]?.trim() || chapter.title,
      });
    });
  });

  const todayKey = new Date().toISOString().slice(0, 10);
  const records = new Map<number, {
    lesson_id: number;
    lesson_title_ar: string;
    unit_title_ar: string;
    chapter_title_ar: string;
    scheduled_date: string | null;
    estimated_minutes: number;
    completed_minutes: number;
    session_count: number;
    completed_session_count: number;
    unit_key: string;
  }>();

  (plan.schedule ?? []).forEach((entry) => {
    entry.sessions.forEach((session) => {
      if (session.type !== 'lesson' || !session.lesson_id) return;
      const lessonInfo = lessonLookup.get(session.lesson_id);
      const unitTitle = session.unit_number ? `الوحدة ${session.unit_number}` : lessonInfo?.unitTitle ?? 'بدون وحدة';
      const record = records.get(session.lesson_id) ?? {
        lesson_id: session.lesson_id,
        lesson_title_ar: lessonInfo?.title ?? session.title,
        unit_title_ar: unitTitle,
        chapter_title_ar: lessonInfo?.chapterTitle ?? '',
        scheduled_date: toDateKey(entry.date),
        estimated_minutes: 0,
        completed_minutes: 0,
        session_count: 0,
        completed_session_count: 0,
        unit_key: String(session.unit_id ?? unitTitle),
      };
      const dateKey = toDateKey(entry.date);
      if (dateKey && (!record.scheduled_date || dateKey < record.scheduled_date)) {
        record.scheduled_date = dateKey;
      }
      record.estimated_minutes += session.minutes || 0;
      record.session_count += 1;
      if (session.completed || session.status === 'completed') {
        record.completed_session_count += 1;
        record.completed_minutes += session.minutes || 0;
      }
      records.set(session.lesson_id, record);
    });
  });

  const scheduled_lessons: LocalScheduledLessonProgress[] = Array.from(records.values())
    .sort((a, b) => (a.scheduled_date || '9999-12-31').localeCompare(b.scheduled_date || '9999-12-31'))
    .map((record, index) => {
      const completed = record.session_count > 0 && record.completed_session_count === record.session_count;
      const percent = completed
        ? 100
        : record.estimated_minutes > 0
          ? Math.round((record.completed_minutes / record.estimated_minutes) * 100)
          : 0;
      const status: StudyPlanProgressStatus = completed
        ? 'completed'
        : record.scheduled_date && record.scheduled_date < todayKey
          ? 'overdue'
          : percent > 0
            ? 'in_progress'
            : 'not_started';
      return {
        study_plan_item_id: index + 1,
        lesson_id: record.lesson_id,
        lesson_title_ar: record.lesson_title_ar,
        unit_title_ar: record.unit_title_ar,
        chapter_title_ar: record.chapter_title_ar,
        scheduled_date: record.scheduled_date,
        status,
        completion_percent: percent,
        estimated_minutes: record.estimated_minutes,
        unit_key: record.unit_key,
      };
    });

  const total = scheduled_lessons.length;
  const completed = scheduled_lessons.filter((lesson) => lesson.status === 'completed').length;
  const expected = expectedPercentFromPlan(plan);
  const completion = total ? Math.round((completed / total) * 1000) / 10 : 0;
  const unitMap = new Map<string, { unit_title_ar: string; total_lessons: number; completed_lessons: number }>();
  scheduled_lessons.forEach((lesson) => {
    const key = lesson.unit_key;
    const unit = unitMap.get(key) ?? {
      unit_title_ar: lesson.unit_title_ar || 'بدون وحدة',
      total_lessons: 0,
      completed_lessons: 0,
    };
    unit.total_lessons += 1;
    if (lesson.status === 'completed') unit.completed_lessons += 1;
    unitMap.set(key, unit);
  });

  const nextLesson = scheduled_lessons.find((lesson) => lesson.status !== 'completed' && lesson.status !== 'skipped');

  return {
    plan_id: plan.id ?? 'local-plan',
    plan_title: String(plan.config?.title ?? 'خطة الكيمياء'),
    total_scheduled_lessons: total,
    completed_lessons: completed,
    in_progress_lessons: scheduled_lessons.filter((lesson) => lesson.status === 'in_progress').length,
    not_started_lessons: scheduled_lessons.filter((lesson) => lesson.status === 'not_started').length,
    overdue_lessons: scheduled_lessons.filter((lesson) => lesson.status === 'overdue').length,
    skipped_lessons: scheduled_lessons.filter((lesson) => lesson.status === 'skipped').length,
    completion_percent: completion,
    expected_percent: expected,
    track_status: trackStatusFromProgress(completion, expected),
    next_lesson: nextLesson
      ? {
          id: nextLesson.lesson_id,
          title_ar: nextLesson.lesson_title_ar,
          scheduled_date: nextLesson.scheduled_date,
          status: nextLesson.status,
        }
      : null,
    unit_progress: Array.from(unitMap.values()).map((unit) => ({
      unit_id: null,
      unit_title_ar: unit.unit_title_ar,
      total_lessons: unit.total_lessons,
      completed_lessons: unit.completed_lessons,
      completion_percent: unit.total_lessons ? Math.round((unit.completed_lessons / unit.total_lessons) * 1000) / 10 : 0,
    })),
    scheduled_lessons: scheduled_lessons.map(({ unit_key: _unitKey, ...lesson }) => lesson),
  };
};

export const studyPlanApi = {
  async getActiveStudyPlan(): Promise<StudyPlan | null> {
    try {
      const [{ data: backendPlans }, basePlan] = await Promise.all([
        api.get<BackendStudyPlanResponse[]>('/study-plans'),
        this.getCurriculumBackedPlan(),
      ]);
      const activeBackendPlan = backendPlans.find((plan) => plan.status === 'active') ?? backendPlans[0] ?? null;
      if (!activeBackendPlan) {
        activePlan = null;
        return null;
      }
      activePlan = mapBackendStudyPlan(activeBackendPlan, basePlan);
      return activePlan;
    } catch {
      activePlan = null;
      return null;
    }
  },

  async getCurriculumBackedPlan(): Promise<StudyPlan> {
    try {
      const { data: units } = await api.get<UnitCatalogItem[]>('/units');
      return mapUnitsToStudyPlan(units.length ? units : fallbackCurriculumUnits);
    } catch {
      return mapUnitsToStudyPlan(fallbackCurriculumUnits);
    }
  },

  async getStudyPlan(): Promise<StudyPlan> {
    if (activePlan) return activePlan;

    try {
      const { data: units } = await api.get<UnitCatalogItem[]>('/units');
      const basePlan = mapUnitsToStudyPlan(units.length ? units : fallbackCurriculumUnits);
      try {
        const { data: backendPlans } = await api.get<BackendStudyPlanResponse[]>('/study-plans');
        activePlan = backendPlans.length ? mapBackendStudyPlan(backendPlans[0], basePlan) : basePlan;
      } catch {
        activePlan = basePlan;
      }
      return activePlan;
    } catch {
      activePlan = mapUnitsToStudyPlan(fallbackCurriculumUnits);
      return activePlan;
    }
  },

  async getStudyPlans(): Promise<StudyPlan[]> {
    const plan = await this.getStudyPlan();
    return [plan];
  },

  async getStudyPlanProgress(planId: string | number, planFallback?: StudyPlan): Promise<StudyPlanProgress> {
    try {
      const { data } = await api.get<StudyPlanProgress>(`/study-plans/${planId}/progress`);
      return data;
    } catch {
      const plan = planFallback ?? activePlan ?? mockStudyPlan;
      return calculateStudyPlanProgress(plan);
    }
  },

  async generatePlan(config: StudyPlanGenerationConfig): Promise<StudyPlan> {
    const normalizedConfig = normalizeGenerationConfig(config);
    try {
      const [basePlan, response] = await Promise.all([
        this.getStudyPlan(),
        api.post<BackendStudyPlanResponse>('/study-plans/generate', normalizedConfig),
      ]);
      activePlan = mapBackendStudyPlan(response.data, basePlan);
      return activePlan;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 422) {
        throw new Error(validationMessageFrom422(error));
      }
      // Offline/Local Simulation fallback
      // Load current full chapters/lessons to reconstruct
      const basePlan = await this.getStudyPlan();
      
      // Filter chapters & lessons by selected config.lessonIds
      const filteredChapters: ChapterPlan[] = basePlan.chapters.map(chapter => {
        const matchingLessons = chapter.lessons.filter(l => 
          normalizedConfig.lessonIds.some((id) => String(id) === String(l.id))
        );
        if (matchingLessons.length === 0) return null;
        
        // Map lessons to have updated states
        const updatedLessons = matchingLessons.map((l, index) => ({
          ...l,
          status: index === 0 ? 'current' : 'locked' as const
        }));

        return {
          ...chapter,
          lessons: updatedLessons,
          progress: 0
        };
      }).filter(Boolean) as ChapterPlan[];

      if (filteredChapters.length === 0) {
        throw new Error('لم يتم العثور على الدروس المحددة داخل فهرس المنهج الحالي.');
      }

      const isExamConfig = 'priority' in normalizedConfig;

      activePlan = {
        id: 'plan-' + Date.now(),
        chapters: filteredChapters,
        weakTopics: isExamConfig && normalizedConfig.priority === 'weak' ? ['موازنة المعادلات', 'قوى فان دير فالز'] : [],
        currentLesson: filteredChapters[0]?.lessons[0] || basePlan.currentLesson,
        // Save config inside metadata for display/editing
        config: { ...normalizedConfig }
      };

      return activePlan!;
    }
  },

  async generateStudyPlan(config: StudyPlanGenerationConfig): Promise<StudyPlan> {
    return this.generatePlan(config);
  },

  async updateStudyPlan(id: string, updates: StudyPlanUpdate): Promise<StudyPlan> {
    try {
      const { data } = await api.put<BackendStudyPlanResponse>(`/study-plans/${id}`, {
        plan_json: updates,
      });
      activePlan = mapBackendStudyPlan(data, activePlan || mockStudyPlan);
      return activePlan;
    } catch {
      if (activePlan) {
        activePlan = {
          ...activePlan,
          ...updates
        };
      }
      return activePlan || mockStudyPlan;
    }
  },

  async patchStudyPlan(id: string, updates: StudyPlanUpdate): Promise<StudyPlan> {
    return this.updateStudyPlan(id, updates);
  },

  async completeLesson(planId: string, lessonId: number | string): Promise<StudyPlan> {
    try {
      const { data } = await api.post<BackendStudyPlanResponse>(`/study-plans/${planId}/lessons/${lessonId}/complete`);
      activePlan = mapBackendStudyPlan(data, activePlan || mockStudyPlan);
      return activePlan;
    } catch {
      if (activePlan) {
        let updatedCurrentLesson = activePlan.currentLesson;
        const updatedChapters = activePlan.chapters.map(chapter => {
          const updatedLessons = chapter.lessons.map(lesson => {
            if (String(lesson.id) === String(lessonId)) {
              return { ...lesson, status: 'completed' as const };
            }
            return lesson;
          });

          // Check if we can unlock the next lesson
          let foundCompleted = false;
          const newLessons = updatedLessons.map((l) => {
            if (l.status === 'completed') return l;
            // First uncompleted lesson after a completed one or starting lesson
            if (!foundCompleted) {
              foundCompleted = true;
              updatedCurrentLesson = l;
              return { ...l, status: 'current' as const };
            }
            return l;
          });

          // Recalculate progress
          const completedCount = newLessons.filter(l => l.status === 'completed').length;
          const progress = Math.round((completedCount / newLessons.length) * 100) || 0;

          return {
            ...chapter,
            lessons: newLessons,
            progress
          };
        });

        activePlan = {
          ...activePlan,
          chapters: updatedChapters,
          currentLesson: updatedCurrentLesson,
          schedule: activePlan.schedule?.map((entry) => ({
            ...entry,
            sessions: entry.sessions.map((session) => (
              String(session.lesson_id) === String(lessonId)
                ? { ...session, status: 'completed' as const, completed: true }
                : session
            )),
          })),
        };
      }
      return activePlan || mockStudyPlan;
    }
  },

  async completeStudyPlanLesson(planId: string, lessonId: number | string): Promise<StudyPlan> {
    return this.completeLesson(planId, lessonId);
  }
};
