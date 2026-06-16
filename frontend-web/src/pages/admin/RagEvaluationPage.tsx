import { useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type { RagEvaluationResponse } from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, PageHeader, StatusPill } from '../../components/DesignSystem';

export const RagEvaluationPage = () => {
  const [evaluation, setEvaluation] = useState<RagEvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadLatest = async () => {
    setLoading(true);
    setError('');
    try {
      setEvaluation(await adminRagApi.getLatestEvaluation());
    } catch (err) {
      setError(toErrorMessage(err, 'لا يوجد تقرير تقييم محفوظ بعد.'));
    } finally {
      setLoading(false);
    }
  };

  const runEvaluation = async () => {
    setLoading(true);
    setError('');
    try {
      setEvaluation(await adminRagApi.runEvaluation());
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تشغيل تقييم RAG.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة RAG"
        title="تقييم جودة الاسترجاع"
        subtitle="شغّل مجموعة الأسئلة الذهبية وراجع استدعاء الصفحات، مطابقة الكلمات المفتاحية، أخطاء المصدر، والعتبات الفاشلة."
      />
      {error && <ErrorBanner message={error} />}

      <Card>
        <div className="guided-card-actions">
          <Button onClick={runEvaluation} disabled={loading}>{loading ? 'جار التشغيل...' : 'تشغيل التقييم'}</Button>
          <Button variant="secondary" onClick={loadLatest} disabled={loading}>تحميل آخر تقرير</Button>
        </div>
      </Card>

      {evaluation && (
        <Card>
          <div className="section-title">
            <h2>نتيجة التقييم</h2>
            <StatusPill tone={evaluation.passed ? 'teal' : 'coral'}>
              {evaluation.passed ? 'ناجح' : 'فشل في العتبات'}
            </StatusPill>
          </div>
          <div className="admin-metric-list">
            {Object.entries(evaluation.metrics).map(([key, value]) => (
              <article key={key}>
                <span>{key}</span>
                <strong>{String(value)}</strong>
              </article>
            ))}
          </div>
          {evaluation.threshold_failures.length > 0 && (
            <div className="admin-failure-list">
              <h3>العتبات الفاشلة</h3>
              {evaluation.threshold_failures.map((failure) => <p key={failure}>{failure}</p>)}
            </div>
          )}
          <p className="admin-muted">تقرير JSON: <span className="formula">{evaluation.report_json_path}</span></p>
          <p className="admin-muted">تقرير Markdown: <span className="formula">{evaluation.report_markdown_path}</span></p>
        </Card>
      )}
    </div>
  );
};
