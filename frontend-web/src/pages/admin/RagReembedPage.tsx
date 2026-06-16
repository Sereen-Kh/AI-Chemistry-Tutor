import { useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type { RagReembedStatus } from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, PageHeader, ProgressBar, StatusPill } from '../../components/DesignSystem';

export const RagReembedPage = () => {
  const [sourceType, setSourceType] = useState('');
  const [batchSize, setBatchSize] = useState(50);
  const [dryRun, setDryRun] = useState(true);
  const [force, setForce] = useState(false);
  const [jobId, setJobId] = useState('');
  const [status, setStatus] = useState<RagReembedStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const start = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await adminRagApi.startReembed({
        source_id: null,
        source_type: sourceType || null,
        batch_size: batchSize,
        dry_run: dryRun,
        force,
        resume_failed: false,
      });
      setJobId(response.job_id);
      setStatus(null);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر بدء مهمة إعادة التضمين.'));
    } finally {
      setLoading(false);
    }
  };

  const refresh = async () => {
    if (!jobId.trim()) return;
    setLoading(true);
    setError('');
    try {
      setStatus(await adminRagApi.getReembedStatus(jobId.trim()));
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر قراءة حالة المهمة.'));
    } finally {
      setLoading(false);
    }
  };

  const progress = status?.total_candidates
    ? Math.round((status.processed / status.total_candidates) * 100)
    : status?.progress ?? 0;

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة RAG"
        title="إعادة تضمين المقاطع"
        subtitle="شغّل المهمة أولاً بوضع dry-run، ثم نفّذ التضمين الحقيقي بعد مراجعة العدد."
      />
      {error && <ErrorBanner message={error} />}

      <section className="admin-two-column">
        <Card className="admin-form-card">
          <h2>إعداد المهمة</h2>
          <label>
            نوع المصدر
            <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
              <option value="">كل المصادر</option>
              <option value="textbook">textbook</option>
              <option value="solution_book">solution_book</option>
              <option value="exam">exam</option>
            </select>
          </label>
          <label>
            حجم الدفعة
            <input type="number" min={1} max={500} value={batchSize} onChange={(event) => setBatchSize(Number(event.target.value))} />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
            تشغيل تجريبي فقط
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} />
            إعادة تضمين إجبارية
          </label>
          <Button onClick={start} disabled={loading}>{loading ? 'جار البدء...' : 'بدء المهمة'}</Button>
        </Card>

        <Card className="admin-form-card">
          <h2>متابعة المهمة</h2>
          <label>
            معرّف المهمة
            <input value={jobId} onChange={(event) => setJobId(event.target.value)} dir="ltr" />
          </label>
          <Button variant="secondary" onClick={refresh} disabled={loading || !jobId.trim()}>تحديث الحالة</Button>
          {status && (
            <div className="admin-job-status">
              <div className="solver-feedback-head">
                <StatusPill tone={status.failed ? 'coral' : status.status === 'success' ? 'teal' : 'blue'}>{status.status}</StatusPill>
                <span>{progress}%</span>
              </div>
              <ProgressBar value={progress} tone={status.failed ? 'coral' : 'teal'} />
              <div className="admin-source-type-grid">
                <article><span>تمت معالجتها</span><strong>{status.processed}</strong></article>
                <article><span>تم تحديثها</span><strong>{status.updated}</strong></article>
                <article><span>تم تخطيها</span><strong>{status.skipped}</strong></article>
                <article><span>فشلت</span><strong>{status.failed}</strong></article>
              </div>
              <p className="admin-muted">نموذج التضمين: <span className="formula">{status.embedding_model || 'غير معروف'}</span></p>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
};
