import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card, PageHeader, StatusPill } from '../../../components/DesignSystem';
import { interactiveSolverApi } from '../api/interactiveSolverApi';
import { ProblemInputCard } from '../components/ProblemInputCard';
import { hclConcentrationProblem } from '../mockData';

export const GuidedLabPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [problemText, setProblemText] = useState(searchParams.get('problem') || hclConcentrationProblem);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const startSession = async () => {
    const trimmed = problemText.trim();
    if (!trimmed || trimmed.length < 20) return;
    setLoading(true);
    setError('');
    try {
      const session = await interactiveSolverApi.startInteractiveSession({
        problem_text: trimmed,
        mode: 'guided',
      });
      navigate(`/guided-lab/session/${session.session_id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر بدء جلسة الحل.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="guided-lab-page page-stack">
      <PageHeader
        eyebrow="مختبر تفاعلي"
        title="حل مسائل الكيمياء الموجه"
        subtitle="حل المسألة خطوة بخطوة مع تغذية راجعة وتلميحات قبل عرض الملخص النهائي."
        action={<Button variant="secondary" onClick={() => navigate('/lab')}>العودة إلى المختبر</Button>}
      />
      <section className="guided-hero">
        <Card className="guided-hero-card">
          <StatusPill tone="purple">تفاعلي</StatusPill>
          <h2>لا يعطيك الجواب مباشرة.</h2>
          <p>
            يطلب منك كل خطوة، يفحص إجابتك، يقدم تلميحاً عند الحاجة، ثم يعرض ملخصاً نهائياً مع مصادر الكتاب.
          </p>
        </Card>
        <Card className="guided-hero-card">
          <StatusPill tone="teal">الإصدار الأول</StatusPill>
          <h2>يدعم مسائل التركيز أولاً.</h2>
          <p>التركيز الغرامي، التركيز المولي، عدد المولات، والتمديد ستكون أول أنواع المسائل المدعومة.</p>
        </Card>
      </section>
      <ProblemInputCard
        value={problemText}
        loading={loading}
        error={error}
        onChange={setProblemText}
        onStart={startSession}
      />
    </div>
  );
};
