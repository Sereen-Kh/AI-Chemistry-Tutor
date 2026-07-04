import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { curriculumApi, fallbackCurriculumUnits, studyPlanApi } from '../api';
import { ErrorBanner, LoadingSkeleton, PageHeader } from '../components/DesignSystem';
import { StudySessionAiBox } from '../components/study-session/StudySessionAiBox';
import { StudySessionCompletionCard } from '../components/study-session/StudySessionCompletionCard';
import { StudySessionFlashcardsCard } from '../components/study-session/StudySessionFlashcardsCard';
import { StudySessionHeader } from '../components/study-session/StudySessionHeader';
import { StudySessionLessonSummary } from '../components/study-session/StudySessionLessonSummary';
import { StudySessionPracticeCard } from '../components/study-session/StudySessionPracticeCard';
import { StudySessionStepRail } from '../components/study-session/StudySessionStepRail';
import type { LessonCatalogItem, StudyPlan, StudyPlanProgress, UserPreferences } from '../types';

const findFallbackLesson = (id: number): LessonCatalogItem | null => {
  for (const unit of fallbackCurriculumUnits) {
    for (const chapter of unit.chapters) {
      const lesson = chapter.lessons.find((item) => item.id === id);
      if (lesson) return lesson;
    }
  }
  return null;
};

export const StudySessionPage = ({ preferences }: { preferences?: UserPreferences }) => {
  const { lessonId } = useParams<{ lessonId: string }>();
  const numericLessonId = Number(lessonId);

  const [lesson, setLesson] = useState<LessonCatalogItem | null>(null);
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [progress, setProgress] = useState<StudyPlanProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!Number.isFinite(numericLessonId) || numericLessonId <= 0) {
        setError('رابط جلسة الدراسة غير صحيح.');
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');
      try {
        const lessonPromise = curriculumApi.getLesson(numericLessonId).catch(() => findFallbackLesson(numericLessonId));
        const activePlan = await studyPlanApi.getStudyPlan();
        if (!activePlan.id) {
          setError('لا توجد خطة دراسة محفوظة لهذه الجلسة.');
          return;
        }
        const [lessonData, progressData] = await Promise.all([
          lessonPromise,
          studyPlanApi.getStudyPlanProgress(activePlan.id, activePlan),
        ]);

        if (cancelled) return;
        if (!lessonData) {
          setError('لم نتمكن من العثور على هذا الدرس داخل المنهج.');
          return;
        }

        setLesson(lessonData);
        setPlan(activePlan);
        setProgress(progressData);
      } catch {
        if (!cancelled) setError('تعذر تحميل جلسة الدراسة. تحقق من اتصال الخادم ثم أعد المحاولة.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [numericLessonId]);

  const scheduledLesson = useMemo(
    () => progress?.scheduled_lessons.find((item) => item.lesson_id === numericLessonId),
    [numericLessonId, progress],
  );

  const completed = scheduledLesson?.status === 'completed' || Boolean(success);
  const nextLesson = useMemo(
    () => progress?.scheduled_lessons.find((item) => item.status !== 'completed' && item.status !== 'skipped' && item.lesson_id !== numericLessonId),
    [numericLessonId, progress],
  );

  const completeLesson = async () => {
    if (!lesson || completing) return;
    if (!plan?.id) {
      setError('لا توجد خطة دراسة محفوظة لتحديث هذا الدرس.');
      return;
    }
    setCompleting(true);
    setError('');
    try {
      const updatedPlan = await studyPlanApi.completeLesson(plan.id, lesson.id);
      const updatedProgress = await studyPlanApi.getStudyPlanProgress(updatedPlan.id ?? plan.id, updatedPlan);
      setPlan(updatedPlan);
      setProgress(updatedProgress);
      setSuccess('تم تحديث خطة الدراسة. هذا الدرس أصبح مكتملًا الآن.');
    } catch {
      setError('تعذر تحديث تقدم الدرس الآن.');
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-stack study-session-page" dir="rtl">
        <PageHeader eyebrow="جلسة دراسة" title="جار تحميل جلسة اليوم..." subtitle="نجهز الدرس وخطة التقدم والأدوات المرتبطة به." />
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  if (error && !lesson) {
    return (
      <div className="page-stack study-session-page" dir="rtl">
        <ErrorBanner message={error} />
        <Link to="/study-plan" className="ed-btn ed-btn-primary">العودة إلى خطة الدراسة</Link>
      </div>
    );
  }

  if (!lesson) return null;

  return (
    <div className="page-stack study-session-page" dir="rtl">
      {error && <ErrorBanner message={error} />}
      {success && <div className="toast-success" role="status">{success}</div>}

      <StudySessionHeader lesson={lesson} planProgress={progress} scheduledLesson={scheduledLesson} />

      <div className="study-session-layout">
        <aside className="study-session-sidebar">
          <StudySessionStepRail />
          <div className="study-session-plan-card">
            <span>تقدم الخطة</span>
            <strong>{Math.round(progress?.completion_percent ?? 0)}%</strong>
            <p>
              {progress
                ? `${progress.completed_lessons} من ${progress.total_scheduled_lessons} دروس مكتملة`
                : 'لا توجد خطة متصلة بهذه الجلسة.'}
            </p>
          </div>
        </aside>

        <main className="study-session-main">
          <StudySessionLessonSummary lesson={lesson} />
          <StudySessionAiBox
            lesson={lesson}
            scheduledLesson={scheduledLesson}
            planProgress={progress}
            preferences={preferences}
          />
          <StudySessionPracticeCard lesson={lesson} />
          <StudySessionFlashcardsCard lesson={lesson} />
          <StudySessionCompletionCard
            completed={completed}
            completing={completing}
            onComplete={() => void completeLesson()}
            nextLesson={nextLesson ? {
              id: nextLesson.lesson_id,
              title_ar: nextLesson.lesson_title_ar,
              scheduled_date: nextLesson.scheduled_date,
              status: nextLesson.status,
            } : null}
          />
        </main>
      </div>
    </div>
  );
};
