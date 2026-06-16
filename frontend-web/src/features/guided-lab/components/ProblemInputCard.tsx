import { Button, Card } from '../../../components/DesignSystem';
import { ExampleProblemCards } from './ExampleProblemCards';

interface ProblemInputCardProps {
  value: string;
  loading: boolean;
  error?: string;
  onChange: (value: string) => void;
  onStart: () => void;
}

export const ProblemInputCard = ({
  value,
  loading,
  error,
  onChange,
  onStart,
}: ProblemInputCardProps) => {
  const trimmed = value.trim();
  const tooShort = trimmed.length > 0 && trimmed.length < 20;

  return (
    <Card className="guided-problem-card">
      <div className="section-title">
        <h2>أدخل المسألة</h2>
        <span>سيطلب منك المختبر حلها خطوة بخطوة.</span>
      </div>
      <label htmlFor="guided-problem-input">
        نص المسألة
        <textarea
          id="guided-problem-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={6}
          placeholder="محلول HCl حجمه 100 mL ويحتوي 3.65 g من الحمض. احسب التركيز الغرامي والمولي."
          aria-describedby={tooShort ? 'guided-problem-validation' : undefined}
        />
      </label>
      {tooShort && <p id="guided-problem-validation" className="guided-validation">اكتب تفاصيل المسألة مثل المادة، الحجم، الكتلة أو المطلوب حسابه.</p>}
      {error && <p className="guided-error" role="alert">{error}</p>}
      <div className="guided-card-actions">
        <Button onClick={onStart} disabled={!trimmed || tooShort || loading}>
          {loading ? 'جار بدء الجلسة...' : 'ابدأ خطوة بخطوة'}
        </Button>
      </div>
      <div className="guided-examples-block">
        <h3>أمثلة جاهزة</h3>
        <ExampleProblemCards onSelect={onChange} />
      </div>
    </Card>
  );
};
