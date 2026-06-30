import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, StatusPill } from '../../../components/DesignSystem';
import { interactiveSolverApi } from '../api/interactiveSolverApi';
import { ProblemInputCard } from '../components/ProblemInputCard';
import { hclConcentrationProblem } from '../mockData';
import type { InteractiveSession } from '../types';

export const GuidedLabPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [problemText, setProblemText] = useState(searchParams.get('problem') || hclConcentrationProblem);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Active sessions state for resume support
  const [activeSessions, setActiveSessions] = useState<InteractiveSession[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  // Load active sessions on mount for resume support
  useEffect(() => {
    let cancelled = false;
    const loadActive = async () => {
      setLoadingSessions(true);
      try {
        const sessions = await interactiveSolverApi.listActiveSessions();
        if (!cancelled) setActiveSessions(sessions);
      } catch {
        // Non-critical — just don't show resume cards
      } finally {
        if (!cancelled) setLoadingSessions(false);
      }
    };
    void loadActive();
    return () => { cancelled = true; };
  }, []);

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

      {/* Active Sessions — Resume Support */}
      {loadingSessions ? (
        <LoadingSkeleton rows={1} />
      ) : activeSessions.length > 0 && (
        <section className="guided-hero">
          <Card className="guided-hero-card">
            <StatusPill tone="gold">جلسات نشطة</StatusPill>
            <h2>لديك {activeSessions.length === 1 ? 'جلسة نشطة' : `${activeSessions.length} جلسات نشطة`}.</h2>
            <p>يمكنك متابعة الحل من حيث توقفت.</p>
            <div className="guided-card-actions">
              {activeSessions.slice(0, 3).map((session) => (
                <Button
                  key={session.session_id}
                  variant="secondary"
                  onClick={() => navigate(`/guided-lab/session/${session.session_id}`)}
                >
                  متابعة: {session.problem_text.slice(0, 40)}…
                </Button>
              ))}
            </div>
          </Card>
        </section>
      )}

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

      {error && <ErrorBanner message={error} onRetry={startSession} />}

      <ProblemInputCard
        value={problemText}
        loading={loading}
        error=""
        onChange={setProblemText}
        onStart={startSession}
      />
    </div>
  );
};
