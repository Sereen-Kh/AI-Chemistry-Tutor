import { Link } from 'react-router-dom';
import { Card, StatusPill } from '../DesignSystem';
import type { LessonCatalogItem } from '../../types';

const formatPages = (start?: number | null, end?: number | null) => {
  if (!start) return 'غير محددة';
  return end && end !== start ? `${start}-${end}` : String(start);
};

export const StudySessionLessonSummary = ({ lesson }: { lesson: LessonCatalogItem }) => (
  <section id="session-summary" className="study-session-anchor">
    <Card className="study-session-card">
    <div className="study-section-head">
      <strong>اقرأ الملخص</strong>
      <StatusPill tone={lesson.difficulty >= 3 ? 'gold' : 'teal'}>مستوى {lesson.difficulty}</StatusPill>
    </div>

    <div className="study-session-summary-body">
      <p>
        ابدأ بقراءة هذا الدرس من الكتاب، ثم استخدم الذكاء الاصطناعي لتفسير أي نقطة غير واضحة قبل الانتقال للتدريب.
      </p>
      {lesson.content_ar && (
        <div className="study-session-note">
          <strong>محتوى الدرس</strong>
          <span>{lesson.content_ar}</span>
        </div>
      )}
    </div>

    <div className="study-session-facts">
      <article>
        <span>صفحات الكتاب</span>
        <strong>{formatPages(lesson.page_start, lesson.page_end)}</strong>
      </article>
      <article>
        <span>المدة المقترحة</span>
        <strong>{lesson.duration_min || 45} دقيقة</strong>
      </article>
      <article>
        <span>عدد المفاهيم</span>
        <strong>{lesson.topics?.length ?? 0}</strong>
      </article>
    </div>

    {lesson.topics?.length > 0 && (
      <div className="study-session-topic-list" aria-label="مفاهيم الدرس">
        {lesson.topics.map((topic) => (
          <span key={topic.id}>{topic.title_ar}</span>
        ))}
      </div>
    )}

    <div className="study-session-actions-row">
      <Link to={`/lessons/${lesson.id}`} className="ed-btn ed-btn-secondary ed-btn-xs">
        افتح صفحة الدرس
      </Link>
      <Link to={`/book-search?q=${encodeURIComponent(lesson.title_ar)}`} className="ed-btn ed-btn-ghost ed-btn-xs">
        ابحث في الكتاب
      </Link>
    </div>
    </Card>
  </section>
);
