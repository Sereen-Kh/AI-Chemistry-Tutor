import type { FormEvent } from 'react';
import { Button, Card, StatusPill } from '../../../components/DesignSystem';
import type { InteractiveStep } from '../types';

interface SolverStepCardProps {
  step: InteractiveStep;
  answer: string;
  submitting: boolean;
  hintLoading: boolean;
  onAnswerChange: (answer: string) => void;
  onSubmit: () => void;
  onHint: () => void;
  onExplainDifferently: () => void;
}

const stepTypeLabel = (type: string): string =>
  ({
    formula: 'اختيار القانون',
    unit_conversion: 'تحويل وحدة',
    calculation: 'حساب عددي',
    molar_mass: 'كتلة مولية',
    final_answer: 'الجواب النهائي',
    guided_step: 'خطوة موجهة',
  })[type] ?? type;

export const SolverStepCard = ({
  step,
  answer,
  submitting,
  hintLoading,
  onAnswerChange,
  onSubmit,
  onHint,
  onExplainDifferently,
}: SolverStepCardProps) => {
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <Card className="solver-step-card">
      <div className="solver-step-meta">
        <StatusPill tone="purple">الخطوة {step.step_index + 1}</StatusPill>
        <span>{stepTypeLabel(step.step_type)}</span>
      </div>
      <h2>{step.prompt}</h2>
      {step.hint && <p className="solver-muted">يمكنك طلب تلميح إذا احتجت دفعة صغيرة.</p>}
      <form onSubmit={submit} className="solver-answer-form">
        <label htmlFor={`solver-answer-${step.step_id}`}>
          إجابتك
          <textarea
            id={`solver-answer-${step.step_id}`}
            value={answer}
            onChange={(event) => onAnswerChange(event.target.value)}
            rows={4}
            placeholder="اكتب القانون أو الناتج مع الوحدة..."
          />
        </label>
        <div className="guided-card-actions">
          <Button type="submit" disabled={submitting || !answer.trim()}>
            {submitting ? 'جار الفحص...' : 'إرسال الإجابة'}
          </Button>
          <Button variant="secondary" onClick={onHint} disabled={hintLoading}>
            {hintLoading ? 'جار عرض التلميح...' : 'أظهر تلميحاً'}
          </Button>
          <Button variant="ghost" onClick={onExplainDifferently}>اشرح بطريقة أخرى</Button>
        </div>
      </form>
    </Card>
  );
};
