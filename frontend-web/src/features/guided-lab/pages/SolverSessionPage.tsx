import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Card,
  ErrorBanner,
  LoadingSkeleton,
  PageHeader,
  StatusPill,
} from '../../../components/DesignSystem';
import { interactiveSolverApi } from '../api/interactiveSolverApi';
import { FinalSummaryCard } from '../components/FinalSummaryCard';
import { FormulaPad } from '../components/FormulaPad';
import { SolverFeedbackCard } from '../components/SolverFeedbackCard';
import { SolverStepCard } from '../components/SolverStepCard';
import { SourceCitationPanel } from '../components/SourceCitationPanel';
import { StepProgressBar } from '../components/StepProgressBar';
import type { InteractiveSession, SubmitStepAnswerResponse } from '../types';

export const SolverSessionPage = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const numericSessionId = Number(sessionId);
  const [session, setSession] = useState<InteractiveSession | null>(null);
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState<SubmitStepAnswerResponse | null>(null);
  const [hint, setHint] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [hintLoading, setHintLoading] = useState(false);
  const [error, setError] = useState('');

  const activeStep = session?.current_step;
  const canShowStepInput = !!activeStep && session?.status !== 'completed' && !feedback?.is_correct;

  const completedCount = useMemo(
    () => session?.steps.filter((step) => step.status === 'correct').length ?? 0,
    [session?.steps],
  );

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!Number.isFinite(numericSessionId)) {
        setError('رقم الجلسة غير صالح.');
        setLoading(false);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const nextSession = await interactiveSolverApi.getInteractiveSession(numericSessionId);
        if (!cancelled) setSession(nextSession);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'تعذر تحميل جلسة الحل.';
        if (!cancelled) setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [numericSessionId]);

  const refreshSession = async () => {
    const nextSession = await interactiveSolverApi.getInteractiveSession(numericSessionId);
    setSession(nextSession);
    return nextSession;
  };

  const submitAnswer = async () => {
    if (!session?.current_step || !answer.trim()) return;
    setSubmitting(true);
    setError('');
    try {
      const response = await interactiveSolverApi.submitStepAnswer(numericSessionId, {
        step_id: session.current_step.step_id,
        answer_text: answer,
      });
      setFeedback(response);
      await refreshSession();
      if (response.is_correct) {
        setAnswer('');
        setHint('');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر فحص الإجابة.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const requestHint = async () => {
    if (!session?.current_step) return;
    setHintLoading(true);
    setError('');
    try {
      const response = await interactiveSolverApi.requestStepHint(numericSessionId, session.current_step.step_id);
      setHint(response.hint);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر عرض التلميح.';
      setError(message);
    } finally {
      setHintLoading(false);
    }
  };

  const finishSession = async () => {
    setSubmitting(true);
    setError('');
    try {
      const nextSession = await interactiveSolverApi.finishInteractiveSession(numericSessionId);
      setSession(nextSession);
      setFeedback(null);
      setHint('');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر إنهاء الجلسة.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const moveNext = () => {
    if (feedback?.session_status === 'completed') {
      void finishSession();
      return;
    }
    setFeedback(null);
    setHint('');
  };

  const insertFormula = (formula: string) => {
    setAnswer((current) => (current.trim() ? `${current} ${formula}` : formula));
  };

  if (loading) {
    return (
      <main className="page-stack">
        <LoadingSkeleton rows={5} />
      </main>
    );
  }

  if (!session) {
    return (
      <main className="page-stack">
        <ErrorBanner message={error || 'لم يتم العثور على الجلسة.'} onRetry={() => navigate('/guided-lab')} />
      </main>
    );
  }

  return (
    <div className="solver-session-page page-stack">
      <PageHeader
        eyebrow="مختبر حل المسائل"
        title="جلسة حل موجهة"
        subtitle="أجب عن كل خطوة، واحصل على تغذية راجعة قبل الانتقال."
        action={<Link className="ed-btn ed-btn-secondary" to="/guided-lab">مسألة جديدة</Link>}
      />

      {session.mock_mode && import.meta.env.DEV && (
        <div className="guided-dev-notice" role="note">وضع تجريبي للمختبر الموجه: واجهة الحل التفاعلي غير متصلة حالياً.</div>
      )}

      {error && <ErrorBanner message={error} />}

      <div className="solver-layout">
        <div className="solver-main-column">
          <Card className="solver-problem-summary">
            <div className="solver-feedback-head">
              <StatusPill tone="gold">{session.problem_type}</StatusPill>
              <span>{completedCount}/{session.steps.length} خطوات</span>
            </div>
            <h2>نص المسألة</h2>
            <p>{session.problem_text}</p>
          </Card>

          {canShowStepInput && (
            <SolverStepCard
              step={activeStep}
              answer={answer}
              submitting={submitting}
              hintLoading={hintLoading}
              onAnswerChange={setAnswer}
              onSubmit={submitAnswer}
              onHint={requestHint}
              onExplainDifferently={() => {
                setHint('فكّر في المطلوب أولاً: هل نبحث عن قانون، تحويل وحدة، أم تعويض عددي؟');
              }}
            />
          )}

          {hint && (
            <Card className="solver-hint-card">
              <StatusPill tone="purple">تلميح</StatusPill>
              <p>{hint}</p>
            </Card>
          )}

          {feedback && <SolverFeedbackCard feedback={feedback} onNext={moveNext} onHint={requestHint} />}

          {session.status === 'completed' && <FinalSummaryCard session={session} />}
        </div>

        <aside className="solver-side-column">
          <Card className="solver-side-card">
            <StepProgressBar steps={session.steps} currentStepIndex={session.current_step_index} />
            <div className="guided-card-actions">
              <Button variant="secondary" onClick={finishSession} disabled={submitting || session.status === 'completed'}>
                إنهاء وعرض ملخص الحل
              </Button>
            </div>
          </Card>
          <FormulaPad onInsert={insertFormula} />
          <SourceCitationPanel sources={session.sources} />
        </aside>
      </div>
    </div>
  );
};
