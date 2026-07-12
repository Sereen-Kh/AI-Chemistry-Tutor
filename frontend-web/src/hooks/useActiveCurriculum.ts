import { useCallback, useEffect, useMemo, useState } from 'react';
import { curriculumApi, fallbackCurriculumUnits } from '../api';
import { allowDemoFallbacks } from '../config/demoFallbacks';
import type { ChapterCatalogItem, LessonCatalogItem, UnitCatalogItem } from '../types';

export type CurriculumLessonOption = LessonCatalogItem & {
  unit: UnitCatalogItem;
  chapter: ChapterCatalogItem;
};

export type CurriculumLessonQuality = {
  lessonId: string;
  status: 'ready' | 'needs_review' | 'blocked';
  score: number;
  issues: string[];
};

const fallbackBySemester = (semester?: number) => {
  if (!semester) return fallbackCurriculumUnits;
  return fallbackCurriculumUnits.filter((unit) => unit.semester === semester);
};

export const lessonPageRange = (lesson: Pick<LessonCatalogItem, 'page_start' | 'page_end'>) => {
  if (!lesson.page_start) return 'صفحات غير محددة';
  if (lesson.page_end && lesson.page_end !== lesson.page_start) return `صفحات ${lesson.page_start} - ${lesson.page_end}`;
  return `صفحة ${lesson.page_start}`;
};

export const getCurriculumLessonQuality = (lesson: LessonCatalogItem): CurriculumLessonQuality => {
  const issues: string[] = [];
  let score = 100;

  if (!lesson.title_ar) {
    issues.push('عنوان الدرس غير متوفر');
    score -= 30;
  }
  if (!lesson.page_start) {
    issues.push('صفحات الكتاب غير محددة');
    score -= 18;
  }
  if (!lesson.topics.length) {
    issues.push('لا توجد موضوعات مرتبطة بالدرس');
    score -= 18;
  }
  if ((lesson.duration_min || 0) < 20) {
    issues.push('مدة الدرس تحتاج مراجعة');
    score -= 8;
  }
  if (lesson.difficulty >= 4) {
    issues.push('درس عالي الصعوبة، يفضل توليد تدريب تدريجي');
    score -= 6;
  }

  const normalized = Math.max(45, Math.min(100, score));
  const status: CurriculumLessonQuality['status'] = normalized >= 80 ? 'ready' : normalized >= 60 ? 'needs_review' : 'blocked';

  return {
    lessonId: String(lesson.id),
    status,
    score: normalized,
    issues,
  };
};

export const useActiveCurriculum = (semester?: number) => {
  const [units, setUnits] = useState<UnitCatalogItem[]>(() => (
    allowDemoFallbacks ? fallbackBySemester(semester) : []
  ));
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [error, setError] = useState('');
  const [reloadToken, setReloadToken] = useState(0);
  const reload = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setLoading(true);
      setUsingFallback(false);
      setError('');
    });

    curriculumApi.getUnits(semester)
      .then((data) => {
        if (cancelled) return;
        if (data.length > 0) {
          setUnits(data);
          return;
        }
        if (allowDemoFallbacks) {
          setUnits(fallbackBySemester(semester));
          setUsingFallback(true);
          return;
        }
        setUnits([]);
        setError('لا توجد بيانات منهج مستوردة. يجب استيراد المنهج المُراجع قبل استخدام أدوات التعلم.');
      })
      .catch(() => {
        if (cancelled) return;
        if (allowDemoFallbacks) {
          setUnits(fallbackBySemester(semester));
          setUsingFallback(true);
          return;
        }
        setUnits([]);
        setError('تعذر تحميل المنهج من الخادم. تحقق من الاتصال ثم حاول مرة أخرى.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [semester, reloadToken]);

  const allLessons = useMemo<CurriculumLessonOption[]>(
    () => units.flatMap((unit) => (
      unit.chapters.flatMap((chapter) => (
        chapter.lessons.map((lesson) => ({ ...lesson, unit, chapter }))
      ))
    )),
    [units],
  );

  const chapters = useMemo(
    () => units.flatMap((unit) => unit.chapters.map((chapter) => ({ ...chapter, unit }))),
    [units],
  );

  return {
    units,
    chapters,
    allLessons,
    loading,
    usingFallback,
    error,
    reload,
  };
};
