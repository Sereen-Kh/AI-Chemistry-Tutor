import { api } from './http';
import { fallbackCurriculumUnits } from './curriculumApi';
import { mockStudyPlan } from './mockData';
import type { ChapterPlan, LessonItem, StudyPlan, SemesterPlanConfig, ExamPlanConfig, UnitCatalogItem } from '../types';

interface BackendStudyPlanResponse {
  id: number;
  exam_date?: string | null;
  plan_json?: {
    chapters?: ChapterPlan[];
    weakTopics?: string[];
    currentLesson?: LessonPlanLike | null;
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

const mapBackendStudyPlan = (response: BackendStudyPlanResponse, fallback: StudyPlan): StudyPlan => {
  const payload = response.plan_json || {};
  const chapters = Array.isArray(payload.chapters) && payload.chapters.length ? payload.chapters : fallback.chapters;
  const currentLesson = (payload.currentLesson || chapters[0]?.lessons[0] || fallback.currentLesson) as LessonItem;
  return {
    id: String(response.id),
    chapters,
    weakTopics: Array.isArray(payload.weakTopics) ? payload.weakTopics : fallback.weakTopics,
    currentLesson,
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

export const studyPlanApi = {
  async getStudyPlan(): Promise<StudyPlan> {
    if (activePlan) return activePlan;

    try {
      const { data: units } = await api.get<UnitCatalogItem[]>('/units');
      activePlan = mapUnitsToStudyPlan(units.length ? units : fallbackCurriculumUnits);
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

  async generatePlan(config: StudyPlanGenerationConfig): Promise<StudyPlan> {
    try {
      const [basePlan, response] = await Promise.all([
        this.getStudyPlan(),
        api.post<BackendStudyPlanResponse>('/study-plans/generate', config),
      ]);
      activePlan = mapBackendStudyPlan(response.data, basePlan);
      return activePlan;
    } catch {
      // Offline/Local Simulation fallback
      // Load current full chapters/lessons to reconstruct
      const basePlan = await this.getStudyPlan();
      
      // Filter chapters & lessons by selected config.lessonIds
      const filteredChapters: ChapterPlan[] = basePlan.chapters.map(chapter => {
        const matchingLessons = chapter.lessons.filter(l => 
          config.lessonIds.some((id) => String(id) === String(l.id))
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

      const isExamConfig = 'priority' in config;

      activePlan = {
        id: 'plan-' + Date.now(),
        chapters: filteredChapters,
        weakTopics: isExamConfig && config.priority === 'weak' ? ['موازنة المعادلات', 'قوى فان دير فالز'] : [],
        currentLesson: filteredChapters[0]?.lessons[0] || basePlan.currentLesson,
        // Save config inside metadata for display/editing
        config: { ...config }
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
          currentLesson: updatedCurrentLesson
        };
      }
      return activePlan || mockStudyPlan;
    }
  },

  async completeStudyPlanLesson(planId: string, lessonId: number | string): Promise<StudyPlan> {
    return this.completeLesson(planId, lessonId);
  }
};
