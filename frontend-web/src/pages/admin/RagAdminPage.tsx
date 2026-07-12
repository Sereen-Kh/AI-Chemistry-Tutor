import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { adminRagApi, toErrorMessage } from '../../api';
import type {
  EmbeddingReadiness,
  LoadReviewedChunksResponse,
  RagEvaluationResponse,
  RagIngestionStats,
  RagPreflightResponse,
  RagOperationsResponse,
  RagQaResponse,
  RagQueryLog,
  RagSource,
  RagSourceStatus,
  RagReembedStatus,
} from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, ProgressBar, StatusPill } from '../../components/DesignSystem';

const recordValue = (value: unknown): Record<string, unknown> => (
  value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
);

export const RagAdminPage = () => {
  const [stats, setStats] = useState<RagIngestionStats | null>(null);
  const [sources, setSources] = useState<RagSource[]>([]);
  const [readiness, setReadiness] = useState<EmbeddingReadiness | null>(null);
  const [preflight, setPreflight] = useState<RagPreflightResponse | null>(null);
  const [ragSources, setRagSources] = useState<RagSourceStatus[]>([]);
  const [loadResult, setLoadResult] = useState<LoadReviewedChunksResponse | null>(null);
  const [reembedJobId, setReembedJobId] = useState<string | null>(null);
  const [reembedStatus, setReembedStatus] = useState<RagReembedStatus | null>(null);
  const [evaluation, setEvaluation] = useState<RagEvaluationResponse | null>(null);
  const [qa, setQa] = useState<RagQaResponse | null>(null);
  const [operations, setOperations] = useState<RagOperationsResponse | null>(null);
  const [logs, setLogs] = useState<RagQueryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [error, setError] = useState('');

  const loadDashboard = async (cancelledRef?: { cancelled: boolean }) => {
      setLoading(true);
      setError('');
      try {
        const [nextStats, nextSources, nextLogs, nextReadiness, nextPreflight, nextRagSources] = await Promise.all([
          adminRagApi.getStats(),
          adminRagApi.getSources(),
          adminRagApi.getQueryLogs({ limit: 8 }),
          adminRagApi.getEmbeddingReadiness(),
          adminRagApi.getPreflight(),
          adminRagApi.getRagSources(),
        ]);
        let latestEval: RagEvaluationResponse | null = null;
        let latestQa: RagQaResponse | null = null;
        let latestOperations: RagOperationsResponse | null = null;
        try {
          [latestEval, latestQa, latestOperations] = await Promise.all([
            adminRagApi.getLatestEvaluation().catch(() => null),
            adminRagApi.getLatestQa().catch(() => null),
            adminRagApi.getOperations().catch(() => null),
          ]);
        } catch {
          latestEval = null;
          latestQa = null;
          latestOperations = null;
        }
        if (!cancelledRef?.cancelled) {
          setStats(nextStats);
          setSources(nextSources);
          setLogs(nextLogs);
          setReadiness(nextReadiness);
          setPreflight(nextPreflight);
          setRagSources(nextRagSources);
          setEvaluation(latestEval);
          setQa(latestQa);
          setOperations(latestOperations);
        }
      } catch (err) {
        if (!cancelledRef?.cancelled) setError(toErrorMessage(err, 'تعذر تحميل لوحة RAG الإدارية.'));
      } finally {
        if (!cancelledRef?.cancelled) setLoading(false);
      }
    };

  useEffect(() => {
    const cancelledRef = { cancelled: false };
    queueMicrotask(() => void loadDashboard(cancelledRef));
    return () => {
      cancelledRef.cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!reembedJobId) return undefined;
    let cancelled = false;
    let timeoutId: number | undefined;
    const poll = async () => {
      try {
        const nextStatus = await adminRagApi.getReembedStatus(reembedJobId);
        if (cancelled) return;
        setReembedStatus(nextStatus);
        if (!['success', 'completed', 'completed_with_errors', 'failure', 'failed'].includes(nextStatus.status)) {
          timeoutId = window.setTimeout(() => void poll(), 1500);
        } else {
          await loadDashboard();
        }
      } catch (err) {
        if (!cancelled) setError(toErrorMessage(err, 'تعذر متابعة مهمة التضمين.'));
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [reembedJobId]);

  const embeddedRatio = useMemo(() => {
    const chunks = preflight?.chunks;
    if (!chunks) return 0;
    const eligible = Number(chunks.pending_embeddings || 0) + Number(chunks.processing_embeddings || 0) + Number(chunks.completed_embeddings || 0) + Number(chunks.failed_embeddings || 0);
    if (!eligible) return 0;
    return Math.min(100, Math.round((Number(chunks.completed_embeddings || 0) / eligible) * 100));
  }, [preflight]);

  const validateSources = async () => {
    if (!window.confirm('سيتم تسجيل/تحديث مصادر PDF في قاعدة البيانات. هل تريد المتابعة؟')) return;
    setActionLoading('validate');
    setActionMessage('');
    setError('');
    try {
      const result = await adminRagApi.validateCanonicalSources();
      setActionMessage(`تم التحقق من ${result.sources.length} مصدر. جاهزية التضمين: ${result.ready_for_embedding ? 'جاهزة' : 'غير جاهزة'}.`);
      await loadDashboard();
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر التحقق من مصادر PDF.'));
    } finally {
      setActionLoading('');
    }
  };

  const prepareChunks = async () => {
    if (!window.confirm('سيتم تحديث ملفات المقاطع المراجعة ونسخها الاحتياطية. هل تريد المتابعة؟')) return;
    setActionLoading('prepare');
    setActionMessage('');
    setError('');
    try {
      const result = await adminRagApi.prepareReviewedChunks({ write: true });
      setActionMessage(
        `تم تجهيز ${result.counts.textbook_chunk_preview_chunks ?? 0} مقطع كتاب و${result.counts.solution_chunks ?? 0} مقطع حلول.`
      );
      await loadDashboard();
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تجهيز المقاطع المراجعة.'));
    } finally {
      setActionLoading('');
    }
  };

  const runLoadDryRun = async () => {
    setActionLoading('load-dry-run');
    setError('');
    try {
      const result = await adminRagApi.loadReviewedChunks({ dry_run: true });
      setLoadResult(result);
      setActionMessage(`فحص التحميل: ${result.chunks_inserted} جديد، ${result.chunks_updated} محدث، ${result.chunks_unchanged} بدون تغيير.`);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تشغيل الفحص الجاف لتحميل المقاطع.'));
    } finally {
      setActionLoading('');
    }
  };

  const loadReviewedChunks = async () => {
    if (!window.confirm('سيتم تحميل المقاطع المراجعة إلى قاعدة البيانات دون حذف الصفوف الحالية. هل تريد المتابعة؟')) return;
    setActionLoading('load');
    setError('');
    try {
      const result = await adminRagApi.loadReviewedChunks({ dry_run: false, clear_existing: false });
      setLoadResult(result);
      setActionMessage(`تم تحميل المقاطع: ${result.chunks_inserted} جديد، ${result.chunks_updated} محدث، ${result.chunks_stale} قديم.`);
      await loadDashboard();
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تحميل المقاطع المراجعة.'));
    } finally {
      setActionLoading('');
    }
  };

  const startEmbedding = async () => {
    if (!preflight?.can_embed) return;
    if (!window.confirm('سيبدأ هذا مهمة التضمين باستخدام Gemini ويكتب المتجهات إلى pgvector. هل تريد المتابعة؟')) return;
    setActionLoading('embed');
    setError('');
    try {
      const result = await adminRagApi.startReembed({
        batch_size: 50,
        dry_run: false,
        force: false,
        resume_failed: false,
      });
      setReembedJobId(result.job_id);
      setActionMessage(`بدأت مهمة التضمين ${result.job_id}.`);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر بدء مهمة التضمين.'));
    } finally {
      setActionLoading('');
    }
  };

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
      {actionMessage && <StatusPill tone="teal">{actionMessage}</StatusPill>}

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
        <Card>
          <StatusPill tone={qa?.status === 'passed' ? 'teal' : 'gold'}>QA</StatusPill>
          <strong>{qa ? (qa.status === 'passed' ? 'ناجح' : qa.status) : 'غير متاح'}</strong>
          <span>تدفقات الطالب</span>
        </Card>
        <Card>
          <StatusPill tone={readiness?.ready_for_embedding ? 'teal' : 'coral'}>جاهزية</StatusPill>
          <strong>{readiness?.ready_for_embedding ? 'جاهز' : 'محجوب'}</strong>
          <span>{readiness?.reviewed_metadata_version || 'لا توجد نسخة مراجعة'}</span>
        </Card>
        <Card>
          <StatusPill tone={(readiness?.textbook_missing_metadata_count ?? 0) > 0 ? 'coral' : 'teal'}>بيانات</StatusPill>
          <strong>{readiness?.textbook_missing_metadata_count ?? 0}</strong>
          <span>مقاطع كتاب ناقصة metadata</span>
        </Card>
        <Card>
          <StatusPill tone={(readiness?.solution_bad_endings_count ?? 0) > 0 ? 'coral' : 'gold'}>حلول</StatusPill>
          <strong>{readiness?.solution_manual_review_count ?? 0}</strong>
          <span>مقاطع تحتاج مراجعة يدوية</span>
        </Card>
      </section>

      <Card>
        <div className="section-title">
          <h2>تشغيل RAG في الإنتاج</h2>
          <StatusPill tone={operations?.status === 'healthy' ? 'teal' : 'coral'}>
            {operations?.status || 'غير متاح'}
          </StatusPill>
        </div>
        <div className="admin-metric-list">
          <article><span>استعلامات 24 ساعة</span><strong>{operations?.query_volume ?? 0}</strong></article>
          <article><span>بدون نتائج</span><strong>{Math.round((operations?.no_result_rate ?? 0) * 100)}%</strong></article>
          <article><span>ثقة منخفضة</span><strong>{Math.round((operations?.low_confidence_rate ?? 0) * 100)}%</strong></article>
          <article><span>متوسط الاسترجاع</span><strong>{operations?.average_retrieval_latency_ms ?? 0} ms</strong></article>
          <article><span>P95</span><strong>{operations?.p95_retrieval_latency_ms ?? 0} ms</strong></article>
          <article><span>اقتباسات ناقصة</span><strong>{operations?.missing_citation_metadata_count ?? 0}</strong></article>
          <article><span>نسخة metadata</span><strong>{operations?.active_reviewed_metadata_version || '—'}</strong></article>
          <article><span>نموذج التضمين</span><strong>{operations?.embedding_model || '—'}</strong></article>
        </div>
        {operations?.degraded_reasons.length ? (
          <ErrorBanner message={`حالة متدهورة: ${operations.degraded_reasons.join('، ')}`} />
        ) : null}
      </Card>

      <Card>
        <div className="section-title">
          <h2>QA لتدفقات الطالب</h2>
          <StatusPill tone={qa?.status === 'passed' ? 'teal' : 'coral'}>{qa?.status || 'غير متاح'}</StatusPill>
        </div>
        <p className="admin-muted">النتائج موزعة حسب نقطة النهاية ومرحلة الفشل؛ التقرير الحي لا يُقبل للإنتاج إلا بوضع integration.</p>
        <div className="admin-source-type-grid">
          {Object.entries(recordValue(qa?.metrics.by_endpoint)).map(([endpoint, value]) => (
            <article key={endpoint}>
              <span>{endpoint}</span>
              <strong>{JSON.stringify(value)}</strong>
            </article>
          ))}
          {Object.entries(recordValue(qa?.metrics.failures_by_stage)).map(([stage, value]) => (
            <article key={`stage-${stage}`}>
              <span>فشل: {stage}</span>
              <strong>{String(value)}</strong>
            </article>
          ))}
        </div>
        {qa?.threshold_failures.length ? (
          <ErrorBanner message={`عوائق QA: ${qa.threshold_failures.join('، ')}`} />
        ) : null}
      </Card>

      <Card>
        <div className="section-title">
          <h2>سير عمل الإدخال المراجَع</h2>
          <StatusPill tone={preflight?.status === 'ready' ? 'teal' : preflight?.status === 'degraded' ? 'gold' : 'coral'}>
            {preflight?.status || 'غير معروف'}
          </StatusPill>
        </div>
        <div className="admin-source-type-grid">
          {ragSources.map((source) => (
            <article key={source.id}>
              <span>{source.source_type === 'textbook' ? 'كتاب الكيمياء' : 'كتاب الحلول'}</span>
              <strong>{source.page_count ?? '—'} صفحة</strong>
              <small>{source.chunk_status} · {source.embedding_status}</small>
            </article>
          ))}
          <article><span>جاهز</span><strong>{preflight?.chunks.ready_chunks ?? 0}</strong></article>
          <article><span>يحتاج مراجعة</span><strong>{preflight?.chunks.needs_review_chunks ?? 0}</strong></article>
          <article><span>محظور</span><strong>{preflight?.chunks.blocked_chunks ?? 0}</strong></article>
          <article><span>مضمّن</span><strong>{preflight?.chunks.completed_embeddings ?? 0}</strong></article>
        </div>
        <div className="admin-action-row">
          <Button variant="secondary" onClick={() => void runLoadDryRun()} disabled={Boolean(actionLoading)}>
            {actionLoading === 'load-dry-run' ? 'جار الفحص...' : 'فحص تحميل المقاطع'}
          </Button>
          <Button variant="primary" onClick={() => void loadReviewedChunks()} disabled={Boolean(actionLoading) || !preflight?.can_load_chunks}>
            {actionLoading === 'load' ? 'جار التحميل...' : 'تحميل المقاطع المراجعة'}
          </Button>
          <Button variant="secondary" onClick={() => void startEmbedding()} disabled={Boolean(actionLoading) || !preflight?.can_embed}>
            {actionLoading === 'embed' ? 'جار البدء...' : 'بدء التضمين'}
          </Button>
        </div>
        {preflight?.blocking_issues.length ? <ErrorBanner message={`لا يمكن المتابعة: ${preflight.blocking_issues.join('، ')}`} /> : null}
        {preflight?.warnings.length ? <p className="admin-warning-text">تحذيرات: {preflight.warnings.join('، ')}</p> : null}
        {loadResult && <p className="admin-muted">آخر فحص تحميل: {loadResult.status} · هل سيكتب؟ {loadResult.would_write ? 'نعم' : 'لا'}</p>}
        {reembedStatus && (
          <div className="admin-metric-list">
            <article><span>مهمة التضمين</span><strong>{reembedStatus.status}</strong></article>
            <article><span>التقدم</span><strong>{reembedStatus.progress}%</strong></article>
            <article><span>مُحدّث</span><strong>{reembedStatus.updated}</strong></article>
            <article><span>فشل</span><strong>{reembedStatus.failed}</strong></article>
            <article><span>متجاوز: blocked</span><strong>{reembedStatus.skipped_blocked_count ?? 0}</strong></article>
            <article><span>متجاوز: stale</span><strong>{reembedStatus.skipped_stale_count ?? 0}</strong></article>
          </div>
        )}
      </Card>

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
            <h2>مصادر PDF المعتمدة</h2>
            <Link to="/admin/sources">فتح المصادر</Link>
          </div>
          <div className="admin-source-type-grid">
            <article><span>مصادر Canonical</span><strong>{sources.filter((source) => source.canonical_source).length || sources.length}</strong></article>
            <article><span>مقاطع جاهزة</span><strong>{readiness?.ready_chunk_count ?? 0}</strong></article>
            <article><span>needs_review</span><strong>{readiness?.needs_review_chunk_count ?? 0}</strong></article>
            <article><span>blocked</span><strong>{readiness?.blocked_chunk_count ?? 0}</strong></article>
          </div>
          <div className="admin-action-row">
            <Button variant="secondary" onClick={() => void validateSources()} disabled={Boolean(actionLoading)}>
              {actionLoading === 'validate' ? 'جار التحقق...' : 'تحقق من المصادر'}
            </Button>
            <Button variant="primary" onClick={() => void prepareChunks()} disabled={Boolean(actionLoading)}>
              {actionLoading === 'prepare' ? 'جار التجهيز...' : 'جهّز المقاطع المراجعة'}
            </Button>
          </div>
          {readiness?.blocking_issues?.length ? (
            <ErrorBanner message={`عوائق التضمين: ${readiness.blocking_issues.join('، ')}`} />
          ) : (
            <p className="admin-muted">المقاطع المراجعة جاهزة لحارس إعادة التضمين. لا يتم تشغيل embedding من هذه الشاشة.</p>
          )}
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
