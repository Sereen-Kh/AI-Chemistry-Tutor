import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { curriculumApi, fallbackCurriculumUnits } from '../../api';
import type { ChapterCatalogItem, LessonCatalogItem, UnitCatalogItem } from '../../types';
import type { LearningContext, LearningPage } from './types';

const semesterStorageKey = 'edumind.activeSemester';

const pageFromPath = (pathname: string): LearningPage => {
  if (pathname === '/dashboard' || pathname === '/') return 'home';
  if (pathname === '/lessons') return 'lessons';
  if (pathname.startsWith('/lessons/')) return 'lesson_detail';
  if (pathname.startsWith('/study-plan')) return 'study_plan';
  if (pathname.startsWith('/book-search') || pathname.startsWith('/rag-search')) return 'book_search';
  if (pathname.startsWith('/quiz') || pathname.startsWith('/quizzes')) return 'quiz';
  if (pathname.startsWith('/flashcards')) return 'flashcards';
  if (pathname.startsWith('/ask-ai')) return 'ask_ai';
  if (pathname.startsWith('/lab') || pathname.startsWith('/guided-lab')) return 'lab';
  if (pathname.startsWith('/homework')) return 'homework';
  if (pathname.startsWith('/notifications')) return 'notifications';
  if (pathname.startsWith('/profile')) return 'profile';
  if (pathname.startsWith('/admin')) return 'admin';
  return 'unknown';
};

const activeSemester = (): 1 | 2 => {
  const raw = Number(localStorage.getItem(semesterStorageKey));
  return raw === 2 ? 2 : 1;
};

const findLessonContext = (
  units: UnitCatalogItem[],
  lessonId?: number,
): {
  unit?: UnitCatalogItem;
  chapter?: ChapterCatalogItem;
  lesson?: LessonCatalogItem;
} => {
  if (!lessonId) return {};
  for (const unit of units) {
    for (const chapter of unit.chapters) {
      const lesson = chapter.lessons.find((item) => item.id === lessonId);
      if (lesson) return { unit, chapter, lesson };
    }
  }
  return {};
};

type CurriculumContext = {
  unit?: UnitCatalogItem;
  chapter?: ChapterCatalogItem;
  lesson?: LessonCatalogItem;
};

const firstContextForSemester = (units: UnitCatalogItem[], semester: 1 | 2): CurriculumContext => {
  const unit = units.find((item) => item.semester === semester) || units[0];
  const chapter = unit?.chapters[0];
  const lesson = chapter?.lessons[0];
  return { unit, chapter, lesson };
};

const routeLessonId = (pathname: string, search: string): number | undefined => {
  const detailMatch = pathname.match(/^\/lessons\/(\d+)/);
  if (detailMatch?.[1]) return Number(detailMatch[1]);
  const params = new URLSearchParams(search);
  const fromQuery = Number(params.get('lessonId'));
  return Number.isFinite(fromQuery) && fromQuery > 0 ? fromQuery : undefined;
};

const nextExamDate = () => {
  const date = new Date();
  date.setDate(date.getDate() + 13);
  return date.toISOString().slice(0, 10);
};

export const useLearningContext = (): LearningContext => {
  const location = useLocation();
  const [units, setUnits] = useState<UnitCatalogItem[]>(fallbackCurriculumUnits);
  const [scrollSection, setScrollSection] = useState<string | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    curriculumApi.getUnits()
      .then((data) => {
        if (!cancelled && data.length) setUnits(data);
      })
      .catch(() => {
        if (!cancelled) setUnits(fallbackCurriculumUnits);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return undefined;
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-rail-section], [data-companion-section]'));
    if (!nodes.length) {
      queueMicrotask(() => setScrollSection(undefined));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
        if (!visible) return;
        const section = visible.target.getAttribute('data-rail-section') || visible.target.getAttribute('data-companion-section') || undefined;
        setScrollSection(section);
      },
      { threshold: [0.25, 0.5], rootMargin: '-18% 0px -52% 0px' },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [location.pathname, location.search]);

  return useMemo(() => {
    const currentPage = pageFromPath(location.pathname);
    const semester = activeSemester();
    const lessonId = routeLessonId(location.pathname, location.search);
    const lessonContext = findLessonContext(units, lessonId);
    const fallbackContext: CurriculumContext = currentPage === 'lessons' || currentPage === 'study_plan'
      ? firstContextForSemester(units, semester)
      : {};
    const unit = lessonContext.unit || fallbackContext.unit;
    const chapter = lessonContext.chapter || fallbackContext.chapter;
    const lesson = lessonContext.lesson || fallbackContext.lesson;
    const weakTopics = units
      .flatMap((item) => item.chapters)
      .flatMap((item) => item.lessons)
      .filter((item) => item.difficulty >= 3)
      .slice(0, 3)
      .flatMap((item) => item.topics.slice(0, 1).map((topic) => ({
        topicId: topic.id,
        titleAr: topic.title_ar,
        scorePercent: 62,
      })));

    return {
      currentPage,
      currentRoute: `${location.pathname}${location.search}`,
      activeSemester: semester,
      activeUnitId: unit?.id,
      activeChapterId: chapter?.id,
      activeLessonId: lesson?.id,
      activeTopicId: lesson?.topics[0]?.id,
      activeUnitTitleAr: unit?.title_ar,
      activeChapterTitleAr: chapter?.title_ar,
      activeLessonTitleAr: lesson?.title_ar,
      activeTopicTitleAr: lesson?.topics[0]?.title_ar,
      progressPercent: currentPage === 'study_plan' ? 62 : undefined,
      dailyMission: lesson ? {
        titleAr: `تابع درس ${lesson.title_ar}`,
        lessonId: lesson.id,
        topicId: lesson.topics[0]?.id,
        estimatedMinutes: lesson.duration_min,
      } : undefined,
      weakTopics,
      nextExamDate: nextExamDate(),
      scrollSection,
    };
  }, [location.pathname, location.search, scrollSection, units]);
};
