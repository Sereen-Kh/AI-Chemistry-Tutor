import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminRagApi, toErrorMessage } from '../../api';
import type { RagEvaluationResponse, RagIngestionStats, RagQueryLog, RagSource } from '../../api/adminRagApi';
import { Card, ErrorBanner, LoadingSkeleton, PageHeader, ProgressBar, StatusPill } from '../../components/DesignSystem';

export const RagAdminPage = () => {
  const [stats, setStats] = useState<RagIngestionStats | null>(null);
  const [sources, setSources] = useState<RagSource[]>([]);
  const [evaluation, setEvaluation] = useState<RagEvaluationResponse | null>(null);
  const [logs, setLogs] = useState<RagQueryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [nextStats, nextSources, nextLogs] = await Promise.all([
          adminRagApi.getStats(),
          adminRagApi.getSources(),
          adminRagApi.getQueryLogs({ limit: 8 }),
        ]);
        let latestEval: RagEvaluationResponse | null = null;
        try {
          latestEval = await adminRagApi.getLatestEvaluation();
        } catch {
          latestEval = null;
        }
        if (!cancelled) {
          setStats(nextStats);
          setSources(nextSources);
          setLogs(nextLogs);
          setEvaluation(latestEval);
        }
      } catch (err) {
        if (!cancelled) setError(toErrorMessage(err, 'تعذر تحميل لوحة RAG الإدارية.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const embeddedRatio = useMemo(() => {
    if (!stats?.total_chunks) return 0;
    const completed = Number(stats.chunks_by_source_type.textbook || 0) + Number(stats.chunks_by_source_type.solution_book || 0);
    return Math.min(100, Math.round((completed / stats.total_chunks) * 100));
  }, [stats]);

  if (loading) {
    return <main className="page-stack"><LoadingSkeleton rows={6} /></main>;
  }

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة RAG"
        title="لوحة مراقبة مصادر الكيمياء"
        subtitle="راقب المصادر، المقاطع، التقييمات، والاستعلامات منخفضة الثقة."
        action={<Link className="ed-btn ed-btn-primary" to="/admin/rag/reembed">إعادة التضمين</Link>}
      />
      {error && <ErrorBanner message={error} />}

      <section className="admin-stat-grid">
        <Card>
          <StatusPill tone="blue">مصادر</StatusPill>
          <strong>{stats?.total_sources ?? sources.length}</strong>
          <span>مصادر مفهرسة</span>
        </Card>
        <Card>
          <StatusPill tone="teal">مقاطع</StatusPill>
          <strong>{stats?.total_chunks ?? 0}</strong>
          <span>مقاطع RAG</span>
        </Card>
        <Card>
          <StatusPill tone="purple">صفحات</StatusPill>
          <strong>{stats?.pages_processed ?? 0}</strong>
          <span>صفحات ممثلة</span>
        </Card>
        <Card>
          <StatusPill tone={evaluation?.passed ? 'teal' : 'gold'}>تقييم</StatusPill>
          <strong>{evaluation ? (evaluation.passed ? 'ناجح' : 'يحتاج ضبط') : 'غير متاح'}</strong>
          <span>آخر تقييم RAG</span>
        </Card>
      </section>

      <section className="admin-two-column">
        <Card>
          <div className="section-title">
            <h2>حالة التضمين</h2>
            <Link to="/admin/rag/reembed">إدارة المهمة</Link>
          </div>
          <ProgressBar value={embeddedRatio} tone="teal" />
          <p className="admin-muted">نسبة تقريبية مبنية على إحصاءات المقاطع حسب نوع المصدر. استخدم شاشة إعادة التضمين للتفاصيل الدقيقة.</p>
          <div className="admin-source-type-grid">
            {Object.entries(stats?.chunks_by_source_type || {}).map(([sourceType, count]) => (
              <article key={sourceType}>
                <span>{sourceType}</span>
                <strong>{count}</strong>
              </article>
            ))}
          </div>
        </Card>

        <Card>
          <div className="section-title">
            <h2>تقييم الجودة</h2>
            <Link to="/admin/rag/evaluation">فتح التقييم</Link>
          </div>
          {evaluation ? (
            <div className="admin-metric-list">
              {Object.entries(evaluation.metrics).slice(0, 6).map(([key, value]) => (
                <article key={key}>
                  <span>{key}</span>
                  <strong>{String(value)}</strong>
                </article>
              ))}
              {evaluation.threshold_failures.length > 0 && (
                <ErrorBanner message={`فشل في ${evaluation.threshold_failures.length} عتبات تقييم.`} />
              )}
            </div>
          ) : (
            <p className="admin-muted">لا يوجد تقرير تقييم محفوظ بعد. شغّل التقييم من صفحة تقييم RAG.</p>
          )}
        </Card>
      </section>

      <Card>
        <div className="section-title">
          <h2>آخر الاستعلامات</h2>
          <Link to="/admin/rag/query-logs">كل السجلات</Link>
        </div>
        <div className="admin-log-table">
          {logs.map((log) => (
            <article key={log.id} className={log.low_confidence ? 'warning' : ''}>
              <strong>{log.query_text}</strong>
              <span>{log.route}</span>
              <span>{log.result_count} نتائج</span>
              <span>{log.max_similarity ? Math.round(log.max_similarity * 100) : 0}%</span>
            </article>
          ))}
          {!logs.length && <p className="admin-muted">لا توجد سجلات استعلام بعد.</p>}
        </div>
      </Card>
    </div>
  );
};
