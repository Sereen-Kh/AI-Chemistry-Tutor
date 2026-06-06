import { api } from './http';
import { mockStudyPlan } from './mockData';
import type { ChapterPlan, StudyPlan } from '../types';

interface ChapterResponse {
  id: number;
  title_ar: string;
  title_en?: string | null;
  description_ar?: string | null;
  difficulty: number;
}

interface LessonResponse {
  id: number;
  chapter_id: number;
  title_ar: string;
  duration_min: number;
}

const colors: ChapterPlan['color'][] = ['blue', 'teal', 'gold', 'purple', 'coral'];

export const studyPlanApi = {
  async getStudyPlan(): Promise<StudyPlan> {
    try {
      const [{ data: chapters }, { data: lessons }] = await Promise.all([
        api.get<ChapterResponse[]>('/chapters'),
        api.get<LessonResponse[]>('/lessons'),
      ]);

      if (!chapters.length) return mockStudyPlan;

      const mapped: ChapterPlan[] = chapters.map((chapter, index) => {
        const chapterLessons = lessons.filter((lesson) => lesson.chapter_id === chapter.id);
        return {
          id: chapter.id,
          title: chapter.title_ar,
          subtitle: chapter.description_ar || `${chapterLessons.length} lessons`,
          progress: index === 0 ? 62 : Math.max(12, 45 - index * 12),
          color: colors[index % colors.length],
          lessons: chapterLessons.map((lesson, lessonIndex) => ({
            id: lesson.id,
            title: lesson.title_ar,
            duration: lesson.duration_min,
            status: lessonIndex === 0 && index === 0 ? 'current' : lessonIndex < 1 ? 'completed' : 'locked',
          })),
        };
      });

      return {
        chapters: mapped,
        weakTopics: mockStudyPlan.weakTopics,
        currentLesson: mapped[0]?.lessons[0] ?? mockStudyPlan.currentLesson,
      };
    } catch {
      return mockStudyPlan;
    }
  },
};
