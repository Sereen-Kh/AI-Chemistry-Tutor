import { Link } from 'react-router-dom';
import type { CSSProperties } from 'react';
import { Button, Card, ProgressBar, StatusPill } from '../DesignSystem';
import type { StudyPlanProgress, StudyPlanProgressStatus, StudyPlanTrackStatus } from '../../types';

const statusLabels: Record<StudyPlanProgressStatus, string> = {
  completed: 'مكتمل',
  in_progress: 'قيد الدراسة',
  not_started: 'لم يبدأ',
  skipped: 'متجاوز',
  overdue: 'متأخر',
};

const statusTones: Record<StudyPlanProgressStatus, 'teal' | 'blue' | 'gold' | 'coral' | 'ghost'> = {
  completed: 'teal',
  in_progress: 'blue',
  not_started: 'ghost',
  skipped: 'gold',
  overdue: 'coral',
};

const trackLabels: Record<StudyPlanTrackStatus, string> = {
  on_track: 'أنت على المسار',
  behind: 'تحتاج إلى تعويض',
  ahead: 'متقدم على الخطة',
};

const trackTones: Record<StudyPlanTrackStatus, 'teal' | 'blue' | 'coral'> = {
  on_track: 'teal',
  behind: 'coral',
  ahead: 'blue',
};

const formatDate = (value?: string | null) => {
  if (!value) return 'غير محدد';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ar', { weekday: 'long', day: 'numeric', month: 'long' }).format(date);
};

const roundPercent = (value: number) => Math.round(value);

export const StudyPlanProgressCard = ({
  progress,
  loading,
  onMarkComplete,
}: {
  progress: StudyPlanProgress | null;
  loading?: boolean;
  onMarkComplete: (lessonId: number) => void | Promise<void>;
}) => {
  if (!progress || progress.total_scheduled_lessons <= 0) {
    return (
      <Card className="study-progress-dashboard">
        <div className="study-progress-empty">
          <strong>تقدّم الخطة</strong>
          <span>{loading ? 'جار تحميل تقدّم الخطة...' : 'لا توجد دروس مجدولة داخل هذه الخطة بعد.'}</span>
        </div>
      </Card>
    );
  }

  const percent = roundPercent(progress.completion_percent);
  const statCards = [
    { label: 'مكتملة', value: progress.completed_lessons, tone: 'teal' },
    { label: 'قيد الدراسة', value: progress.in_progress_lessons, tone: 'blue' },
    { label: 'لم تبدأ', value: progress.not_started_lessons, tone: 'ghost' },
    { label: 'متأخرة', value: progress.overdue_lessons, tone: 'coral' },
  ] as const;

  return (
    <section className="study-progress-dashboard" aria-label="تقدّم الخطة">
      <Card className="study-progress-main-card">
        <div className="study-progress-main">
          <div
            className="study-progress-ring"
            style={{ '--progress-value': `${Math.min(100, Math.max(0, percent))}%` } as CSSProperties}
            role="progressbar"
            aria-label={`نسبة إنجاز خطة الدراسة ${percent} بالمئة`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
          >
            <strong>{percent}%</strong>
            <span>نسبة الإنجاز</span>
          </div>

          <div className="study-progress-copy">
            <div className="study-section-head">
              <strong>تقدّم الخطة</strong>
              <StatusPill tone={trackTones[progress.track_status]}>{trackLabels[progress.track_status]}</StatusPill>
            </div>
            <h3>{progress.completed_lessons} من {progress.total_scheduled_lessons} دروس مكتملة</h3>
            <p>
              يتم حساب التقدّم من الدروس المجدولة داخل هذه الخطة فقط. المتوقع حتى الآن:
              {' '}
              {roundPercent(progress.expected_percent)}%.
            </p>
            <ProgressBar value={percent} tone={trackTones[progress.track_status]} />
          </div>
        </div>

        <div className="study-progress-stats-grid">
          {statCards.map((stat) => (
            <div key={stat.label} className={`study-progress-stat tone-${stat.tone}`}>
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
            </div>
          ))}
        </div>
      </Card>

      <Card className="study-next-lesson-card">
        <div className="study-section-head">
          <strong>الدرس التالي</strong>
          {progress.next_lesson && (
            <StatusPill tone={statusTones[progress.next_lesson.status]}>
              {statusLabels[progress.next_lesson.status]}
            </StatusPill>
          )}
        </div>
        {progress.next_lesson ? (
          <>
            <h3>{progress.next_lesson.title_ar}</h3>
            <span className="study-progress-muted">{formatDate(progress.next_lesson.scheduled_date)}</span>
            <div className="study-progress-actions">
              <Link to={`/study-session/${progress.next_lesson.id}`} className="ed-btn ed-btn-primary ed-btn-xs">
                ابدأ جلسة اليوم
              </Link>
              <Link to={`/lessons/${progress.next_lesson.id}`} className="ed-btn ed-btn-ghost ed-btn-xs">
                افتح الدرس فقط
              </Link>
              <Button variant="secondary" className="ed-btn-xs" onClick={() => onMarkComplete(progress.next_lesson!.id)}>
                تحديد كمكتمل
              </Button>
            </div>
          </>
        ) : (
          <p className="study-progress-muted">كل الدروس المجدولة مكتملة في هذه الخطة.</p>
        )}
      </Card>

      <Card className="study-unit-breakdown-card">
        <div className="study-section-head">
          <strong>تقدّم الوحدات</strong>
          <StatusPill tone="blue">حسب الخطة</StatusPill>
        </div>
        <div className="study-unit-breakdown-list">
          {progress.unit_progress.length ? progress.unit_progress.map((unit) => (
            <article key={`${unit.unit_id ?? unit.unit_title_ar}`}>
              <div>
                <strong>{unit.unit_title_ar}</strong>
                <span>{unit.completed_lessons}/{unit.total_lessons} دروس</span>
              </div>
              <ProgressBar value={unit.completion_percent} tone="teal" />
            </article>
          )) : (
            <span className="study-progress-muted">لا توجد وحدات مجدولة بعد.</span>
          )}
        </div>
      </Card>

      <Card className="study-scheduled-lessons-card">
        <div className="study-section-head">
          <strong>الدروس المجدولة</strong>
          <StatusPill tone="ghost">{progress.total_scheduled_lessons} من الدروس المجدولة</StatusPill>
        </div>
        <div className="study-scheduled-lessons-list">
          {progress.scheduled_lessons.length ? progress.scheduled_lessons.map((lesson) => (
            <article key={`${lesson.study_plan_item_id ?? lesson.lesson_id}-${lesson.lesson_id}`} className={`study-scheduled-lesson status-${lesson.status}`}>
              <div className="study-scheduled-lesson-main">
                <strong>{lesson.lesson_title_ar}</strong>
                <span>
                  {lesson.unit_title_ar || 'بدون وحدة'}
                  {lesson.chapter_title_ar ? ` · ${lesson.chapter_title_ar}` : ''}
                </span>
              </div>
              <div className="study-scheduled-lesson-meta">
                <span>{formatDate(lesson.scheduled_date)}</span>
                <StatusPill tone={statusTones[lesson.status]}>{statusLabels[lesson.status]}</StatusPill>
                <span>{roundPercent(lesson.completion_percent)}%</span>
              </div>
              <div className="study-scheduled-lesson-progress">
                <ProgressBar value={lesson.completion_percent} tone={statusTones[lesson.status] === 'ghost' ? 'blue' : statusTones[lesson.status]} />
              </div>
              {lesson.status !== 'completed' && lesson.status !== 'skipped' && (
                <div className="study-scheduled-lesson-actions">
                  <Link to={`/study-session/${lesson.lesson_id}`} className="ed-btn ed-btn-primary ed-btn-xs">
                    ابدأ الجلسة
                  </Link>
                  <Button variant="secondary" className="ed-btn-xs" onClick={() => onMarkComplete(lesson.lesson_id)}>
                    مكتمل
                  </Button>
                </div>
              )}
            </article>
          )) : (
            <span className="study-progress-muted">لا توجد دروس مجدولة في هذه الخطة.</span>
          )}
        </div>
      </Card>
    </section>
  );
};
