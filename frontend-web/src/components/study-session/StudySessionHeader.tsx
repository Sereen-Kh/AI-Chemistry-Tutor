import { Link } from 'react-router-dom';
import { Card, ProgressBar, StatusPill } from '../DesignSystem';
import type { LessonCatalogItem, StudyPlanProgress, StudyPlanScheduledLessonProgress } from '../../types';

const formatDate = (value?: string | null) => {
  if (!value) return 'غير مجدول';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ar', { weekday: 'long', day: 'numeric', month: 'long' }).format(date);
};

const trackLabels: Record<StudyPlanProgress['track_status'], string> = {
  ahead: 'متقدم على الخطة',
  on_track: 'أنت على المسار',
  behind: 'تحتاج إلى تعويض',
};

const statusLabels: Record<StudyPlanScheduledLessonProgress['status'], string> = {
  completed: 'مكتمل',
  in_progress: 'قيد الدراسة',
  not_started: 'لم يبدأ',
  overdue: 'متأخر',
  skipped: 'متجاوز',
};

export const StudySessionHeader = ({
  lesson,
  planProgress,
  scheduledLesson,
}: {
  lesson: LessonCatalogItem;
  planProgress: StudyPlanProgress | null;
  scheduledLesson?: StudyPlanScheduledLessonProgress;
}) => {
  const planPercent = Math.round(planProgress?.completion_percent ?? 0);

  return (
    <Card className="study-session-header">
      <div className="study-session-header-main">
        <div>
          <span className="study-session-eyebrow">جلسة دراسة موجهة</span>
          <h1>{lesson.title_ar}</h1>
          <p>
            {scheduledLesson?.unit_title_ar || 'خطة الكيمياء'}
            {scheduledLesson?.chapter_title_ar ? ` · ${scheduledLesson.chapter_title_ar}` : ''}
            {' · '}
            الصفحات {lesson.page_start || '؟'}{lesson.page_end && lesson.page_end !== lesson.page_start ? `-${lesson.page_end}` : ''}
          </p>
        </div>
        <div className="study-session-header-actions">
          <StatusPill tone={scheduledLesson?.status === 'overdue' ? 'coral' : scheduledLesson?.status === 'completed' ? 'teal' : 'blue'}>
            {scheduledLesson ? statusLabels[scheduledLesson.status] : 'جلسة حرة'}
          </StatusPill>
          <Link to="/study-plan" className="ed-btn ed-btn-ghost ed-btn-xs">العودة للخطة</Link>
        </div>
      </div>

      <div className="study-session-meta-grid">
        <div>
          <span>موعد الجلسة</span>
          <strong>{formatDate(scheduledLesson?.scheduled_date)}</strong>
        </div>
        <div>
          <span>مدة الدرس</span>
          <strong>{lesson.duration_min || scheduledLesson?.estimated_minutes || 45} دقيقة</strong>
        </div>
        <div>
          <span>حالة الخطة</span>
          <strong>{planProgress ? trackLabels[planProgress.track_status] : 'غير متصلة'}</strong>
        </div>
        <div>
          <span>تقدّم الخطة</span>
          <strong>{planPercent}%</strong>
          <ProgressBar value={planPercent} tone={planProgress?.track_status === 'behind' ? 'coral' : 'teal'} />
        </div>
      </div>
    </Card>
  );
};
