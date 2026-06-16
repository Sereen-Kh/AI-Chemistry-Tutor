import type { InteractiveStep } from '../types';

export const StepProgressBar = ({
  steps,
  currentStepIndex,
}: {
  steps: InteractiveStep[];
  currentStepIndex: number;
}) => {
  const completedCount = steps.filter((step) => step.status === 'correct').length;
  const percent = steps.length ? Math.round((completedCount / steps.length) * 100) : 0;
  const statusLabel = (status: InteractiveStep['status']): string =>
    ({
      pending: 'بانتظار الإجابة',
      correct: 'صحيحة',
      incorrect: 'تحتاج مراجعة',
      skipped: 'متخطاة',
    })[status];

  return (
    <section className="solver-progress" aria-label="تقدم خطوات الحل">
      <div className="solver-progress-header">
        <strong>الخطوة {Math.min(currentStepIndex + 1, steps.length)} من {steps.length}</strong>
        <span>{percent}% مكتمل</span>
      </div>
      <div className="solver-progress-track" role="progressbar" aria-label={`اكتمل ${percent}% من خطوات الحل`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="solver-step-dots" role="list" aria-label="حالة كل خطوة">
        {steps.map((step) => (
          <span
            key={step.step_id}
            className={`solver-step-dot ${step.status} ${step.step_index === currentStepIndex ? 'current' : ''}`}
            title={`الخطوة ${step.step_index + 1}`}
            role="listitem"
            aria-current={step.step_index === currentStepIndex ? 'step' : undefined}
            aria-label={`الخطوة ${step.step_index + 1}: ${statusLabel(step.status)}`}
          >
            {step.step_index + 1}
            <span className="sr-only">، {statusLabel(step.status)}</span>
          </span>
        ))}
      </div>
    </section>
  );
};
