import { Link } from 'react-router-dom';
import { Card, FormattedText, StatusPill } from '../../../components/DesignSystem';
import type { InteractiveSession } from '../types';

export const FinalSummaryCard = ({ session }: { session: InteractiveSession }) => {
  const completedSteps = session.steps.filter((step) => step.status === 'correct');
  const askAiQuery = encodeURIComponent(`اشرح لي هذه المسألة خطوة بخطوة: ${session.problem_text}`);

  return (
    <Card className="final-summary-card">
      <div className="solver-feedback-head">
        <StatusPill tone="teal">اكتمل الحل</StatusPill>
        <span>{completedSteps.length} خطوات مكتملة</span>
      </div>
      <h2>ملخص الحل</h2>
      <p className="final-answer"><FormattedText text={session.final_answer ?? 'Cg = 36.5 g/L، C = 1 mol/L'} /></p>
      <div className="solver-summary-steps">
        {completedSteps.map((step) => (
          <article key={step.step_id}>
            <strong>{step.step_index + 1}. {step.prompt}</strong>
            {step.explanation && <span>{step.explanation}</span>}
          </article>
        ))}
      </div>
      <div className="guided-card-actions">
        <Link className="ed-btn ed-btn-primary" to="/quiz">أنشئ اختباراً قصيراً</Link>
        <Link className="ed-btn ed-btn-secondary" to="/flashcards">أنشئ بطاقات مراجعة</Link>
        <Link className="ed-btn ed-btn-ghost" to={`/ask-ai?question=${askAiQuery}`}>اسأل الذكاء عن المسألة</Link>
        <Link className="ed-btn ed-btn-ghost" to="/lab">العودة إلى المختبر</Link>
      </div>
    </Card>
  );
};
