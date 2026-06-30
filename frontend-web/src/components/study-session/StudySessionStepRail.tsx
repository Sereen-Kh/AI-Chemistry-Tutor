const steps = [
  { id: 'summary', label: 'اقرأ الملخص' },
  { id: 'ai', label: 'اسأل AI' },
  { id: 'practice', label: 'تدرب باختبار قصير' },
  { id: 'flashcards', label: 'راجع بالبطاقات' },
  { id: 'complete', label: 'أكمل الدرس' },
];

export const StudySessionStepRail = ({ activeStep = 'summary' }: { activeStep?: string }) => (
  <nav className="study-session-step-rail" aria-label="خطوات جلسة الدراسة">
    {steps.map((step, index) => (
      <a
        key={step.id}
        href={`#session-${step.id}`}
        className={`study-session-step ${activeStep === step.id ? 'active' : ''}`}
      >
        <span>{index + 1}</span>
        <strong>{step.label}</strong>
      </a>
    ))}
  </nav>
);
