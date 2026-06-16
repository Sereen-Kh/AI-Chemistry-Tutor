import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { homeworkApi, toErrorMessage } from '../api';
import type { HomeworkSource, HomeworkSolveTextResponse } from '../api/homeworkApi';
import { Button, Card, ErrorBanner, PageHeader, SourceCard, StatusPill } from '../components/DesignSystem';
import type { SourceCitation } from '../types';

const sampleProblem =
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g من الحمض. احسب التركيز الغرامي والمولي.';

const sourceTypeLabel = (sourceType?: string): string => {
  if (sourceType === 'solution_book' || sourceType === 'solutions') return 'كتاب الحلول';
  if (sourceType === 'exam') return 'نموذج امتحاني';
  return 'كتاب الكيمياء';
};

const normalizeSources = (value: HomeworkSolveTextResponse['source_chunks']): SourceCitation[] => {
  if (!Array.isArray(value)) return [];
  return value.slice(0, 5).map((source: HomeworkSource, index) => ({
    title: sourceTypeLabel(source.source_type),
    page: source.page_number ?? source.page ?? null,
    chunk_id: source.chunk_id ?? `homework-source-${index}`,
    quote: source.preview ?? source.quote ?? source.content_type,
    score: source.score,
  }));
};

export const HomeworkPage = () => {
  const [problemText, setProblemText] = useState(sampleProblem);
  const [result, setResult] = useState<HomeworkSolveTextResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const sources = useMemo(() => normalizeSources(result?.source_chunks), [result?.source_chunks]);
  const guidedSolverUrl = `/guided-lab?problem=${encodeURIComponent(problemText.trim() || result?.problem_text || '')}`;

  const solve = async () => {
    const trimmed = problemText.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError('');
    setSaved(false);
    try {
      const response = await homeworkApi.solveText(trimmed);
      setResult(response);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر حل الواجب حالياً. تأكد أن الخادم يعمل ثم أعد المحاولة.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="homework-page page-stack">
      <PageHeader
        eyebrow="حل الواجبات"
        title="مساعد الواجبات النصية"
        subtitle="اكتب المسألة، ثم راجع الحل مع مصادره أو حوّلها إلى جلسة حل موجهة."
      />

      <section className="homework-layout">
        <Card className="homework-input-card">
          <div className="section-title">
            <h2>نص الواجب</h2>
            <StatusPill tone="blue">نصي حالياً</StatusPill>
          </div>
          <label htmlFor="homework-problem">
            اكتب المسألة كما ظهرت في الدفتر أو الكتاب
            <textarea
              id="homework-problem"
              value={problemText}
              onChange={(event) => setProblemText(event.target.value)}
              rows={8}
              placeholder={sampleProblem}
            />
          </label>
          <div className="homework-upload-placeholder" aria-disabled="true">
            <strong>رفع صورة الواجب</strong>
            <span>قادم لاحقاً بعد تفعيل رفع الصور من الخادم.</span>
          </div>
          {error && <ErrorBanner message={error} onRetry={solve} />}
          <div className="guided-card-actions">
            <Button onClick={solve} disabled={loading || problemText.trim().length < 8}>
              {loading ? 'جار حل الواجب...' : 'حل الواجب'}
            </Button>
            <Link className="ed-btn ed-btn-secondary" to={guidedSolverUrl}>
              حوّل إلى حل موجه
            </Link>
          </div>
        </Card>

        <aside className="homework-side-card">
          <Card>
            <StatusPill tone="purple">طريقة أفضل للتعلم</StatusPill>
            <h2>لا تكتف بالجواب النهائي.</h2>
            <p>إذا كانت المسألة حسابية، استخدم الحل الموجه ليطلب منك القانون والتحويل والتعويض خطوة بخطوة.</p>
            <Link className="card-link-button" to={guidedSolverUrl}>ابدأ جلسة موجهة</Link>
          </Card>
          <Card>
            <StatusPill tone="gold">حالة الصورة</StatusPill>
            <h2>حل الصور غير مفعّل في الواجهة بعد.</h2>
            <p>الواجهة جاهزة لعرضه لاحقاً، لكن هذا الإصدار يستخدم النص فقط حتى يتوفر رفع الصور.</p>
          </Card>
        </aside>
      </section>

      {result && (
        <Card className="homework-result-card">
          <div className="section-title">
            <h2>الحل المقترح</h2>
            <StatusPill tone={typeof result.confidence_score === 'number' && result.confidence_score >= 0.6 ? 'teal' : 'gold'}>
              {typeof result.confidence_score === 'number'
                ? `ثقة ${Math.round(result.confidence_score * 100)}%`
                : 'ثقة غير متاحة'}
            </StatusPill>
          </div>
          <p className="homework-solution">{result.solution}</p>
          <div className="guided-card-actions">
            <Link className="ed-btn ed-btn-primary" to={guidedSolverUrl}>ابدأ الحل خطوة بخطوة</Link>
            <Button variant="secondary" onClick={() => setSaved(true)}>
              {saved ? 'تم الحفظ في الجلسة' : 'حفظ في السجل'}
            </Button>
            <Link className="ed-btn ed-btn-ghost" to={`/ask-ai?question=${encodeURIComponent(`اشرح واجب الكيمياء هذا: ${result.problem_text}`)}`}>
              اسأل الذكاء عن الحل
            </Link>
          </div>
          {sources.length > 0 && (
            <div className="source-evidence-panel">
              <div className="source-evidence-head">
                <strong>مصادر الحل</strong>
                <span>مقاطع مسترجعة لدعم الإجابة</span>
              </div>
              <div className="source-grid">
                {sources.map((source) => <SourceCard key={`${source.chunk_id}-${source.page}`} source={source} />)}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
