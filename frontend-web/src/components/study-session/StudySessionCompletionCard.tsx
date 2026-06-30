import { Link } from 'react-router-dom';
import { Button, Card, StatusPill } from '../DesignSystem';
import type { StudyPlanProgressNextLesson } from '../../types';

export const StudySessionCompletionCard = ({
  completed,
  completing,
  onComplete,
  nextLesson,
}: {
  completed: boolean;
  completing: boolean;
  onComplete: () => void | Promise<void>;
  nextLesson?: StudyPlanProgressNextLesson | null;
}) => (
  <section id="session-complete" className="study-session-anchor">
    <Card className="study-session-card study-session-completion-card">
    <div className="study-section-head">
      <strong>أكمل الدرس</strong>
      <StatusPill tone={completed ? 'teal' : 'blue'}>{completed ? 'تم الإنجاز' : 'آخر خطوة'}</StatusPill>
    </div>

    <p className="study-session-muted">
      بعد قراءة الملخص، سؤال الذكاء، والتدريب السريع، حدّد الدرس كمكتمل لتحديث خطة الدراسة ونسبة التقدم.
    </p>

    <div className="study-session-complete-actions">
      <Button onClick={onComplete} disabled={completed || completing}>
        {completed ? 'تم إكمال الدرس' : completing ? 'جار تحديث التقدم...' : 'أكملت الدرس'}
      </Button>
      <Link to="/study-plan" className="ed-btn ed-btn-secondary">
        العودة إلى خطة الدراسة
      </Link>
      {completed && nextLesson && (
        <Link to={`/study-session/${nextLesson.id}`} className="ed-btn ed-btn-ghost">
          الجلسة التالية: {nextLesson.title_ar}
        </Link>
      )}
    </div>
    </Card>
  </section>
);
