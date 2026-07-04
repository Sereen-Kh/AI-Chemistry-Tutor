import { useEffect, useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type { IngestionPage, RagIngestionStats, RagSource } from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, StatusPill } from '../../components/DesignSystem';

const statusTone = (status: string): string => {
  if (status.startsWith('completed')) return 'teal';
  if (status === 'failed') return 'coral';
  if (status.includes('retry') || status.includes('review') || status.includes('skipped')) return 'gold';
  if (status === 'running' || status === 'processing') return 'blue';
  return 'slate';
};

const issueText = (value: IngestionPage['errors_json'] | IngestionPage['warnings_json']): string => {
  if (!value) return '';
  if (Array.isArray(value)) return value.map((item) => String(item)).join('، ');
  return JSON.stringify(value);
};

export const SourcesPage = () => {
  const [sources, setSources] = useState<RagSource[]>([]);
  const [stats, setStats] = useState<RagIngestionStats | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [pages, setPages] = useState<IngestionPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagesLoading, setPagesLoading] = useState(false);
  const [retryingPageId, setRetryingPageId] = useState<number | null>(null);
  const [validatingSources, setValidatingSources] = useState(false);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [nextSources, nextStats] = await Promise.all([
          adminRagApi.getSources(),
          adminRagApi.getStats(),
        ]);
        if (!cancelled) {
          setSources(nextSources);
          setStats(nextStats);
          setSelectedSourceId((current) => current ?? nextSources[0]?.id ?? null);
        }
      } catch (err) {
        if (!cancelled) setError(toErrorMessage(err, 'تعذر تحميل مصادر RAG.'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedSourceId) {
      setPages([]);
      return;
    }
    let cancelled = false;
    const loadPages = async () => {
      setPagesLoading(true);
      setDetailError('');
      try {
        const nextPages = await adminRagApi.getSourcePages(selectedSourceId);
        if (!cancelled) setPages(nextPages);
      } catch (err) {
        if (!cancelled) setDetailError(toErrorMessage(err, 'تعذر تحميل صفحات المصدر.'));
      } finally {
        if (!cancelled) setPagesLoading(false);
      }
    };
    void loadPages();
    return () => {
      cancelled = true;
    };
  }, [selectedSourceId]);

  const retryPage = async (pageId?: number | null) => {
    if (!pageId || !selectedSourceId) return;
    setRetryingPageId(pageId);
    setDetailError('');
    try {
      await adminRagApi.retryPage(pageId);
      const [nextSources, nextPages, nextStats] = await Promise.all([
        adminRagApi.getSources(),
        adminRagApi.getSourcePages(selectedSourceId),
        adminRagApi.getStats(),
      ]);
      setSources(nextSources);
      setPages(nextPages);
      setStats(nextStats);
    } catch (err) {
      setDetailError(toErrorMessage(err, 'تعذر إعادة معالجة الصفحة.'));
    } finally {
      setRetryingPageId(null);
    }
  };

  const validateSources = async () => {
    setValidatingSources(true);
    setError('');
    try {
      await adminRagApi.validateCanonicalSources();
      const [nextSources, nextStats] = await Promise.all([
        adminRagApi.getSources(),
        adminRagApi.getStats(),
      ]);
      setSources(nextSources);
      setStats(nextStats);
      setSelectedSourceId((current) => current ?? nextSources[0]?.id ?? null);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر التحقق من مصادر PDF المعتمدة.'));
    } finally {
      setValidatingSources(false);
    }
  };

  if (loading) {
    return <main className="page-stack"><LoadingSkeleton rows={6} /></main>;
  }

  const selectedSource = sources.find((source) => source.id === selectedSourceId) ?? null;
  const failedPages = pages.filter((page) => page.status === 'failed').length;
  const reviewPages = pages.filter((page) => ['skipped_dry_run', 'queued_retry'].includes(page.status) || page.status.includes('review')).length;

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة المصادر"
        title="مصادر الكتاب وكتاب الحلول"
        subtitle="راجع مصادر RAG المفهرسة وحالة كل مصدر وعدد المقاطع حسب النوع."
        action={
          <Button variant="secondary" onClick={() => void validateSources()} disabled={validatingSources}>
            {validatingSources ? 'جار التحقق...' : 'تحقق من مصادر PDF'}
          </Button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="admin-stat-grid">
        <Card><StatusPill tone="blue">مصادر</StatusPill><strong>{stats?.total_sources ?? sources.length}</strong><span>مصادر</span></Card>
        <Card><StatusPill tone="teal">مقاطع</StatusPill><strong>{stats?.total_chunks ?? 0}</strong><span>مقاطع</span></Card>
        <Card><StatusPill tone="purple">أسئلة</StatusPill><strong>{stats?.total_questions ?? 0}</strong><span>أسئلة مستخرجة</span></Card>
        <Card><StatusPill tone={failedPages ? 'coral' : reviewPages ? 'gold' : 'teal'}>صفحات</StatusPill><strong>{stats?.pages_processed ?? 0}</strong><span>صفحات ممثلة</span></Card>
        <Card><StatusPill tone="teal">Canonical</StatusPill><strong>{sources.filter((source) => source.canonical_source).length}</strong><span>مصادر PDF معتمدة</span></Card>
      </section>

      <section className="admin-two-column admin-source-detail-layout">
        <Card>
          <div className="section-title">
            <h2>قائمة المصادر</h2>
            <span>{sources.length} مصدر</span>
          </div>
          <div className="admin-source-list">
            {sources.map((source) => (
              <button
                type="button"
                key={source.id}
                className={`admin-source-row ${selectedSourceId === source.id ? 'active' : ''}`}
                onClick={() => setSelectedSourceId(source.id)}
              >
                <div>
                  <StatusPill tone={statusTone(source.status)}>{source.status}</StatusPill>
                  <strong>{source.title}</strong>
                </div>
                <span>{source.source_type} · {source.grade} · {source.subject}</span>
                <small>{source.file_path || source.original_filename || 'لا يوجد مسار ملف'}</small>
                {source.canonical_source && (
                  <small>
                    {source.page_count ?? 0} صفحة · {source.ready_for_embedding ? 'metadata جاهزة' : 'metadata غير جاهزة'}
                  </small>
                )}
                <div className="admin-source-counters">
                  <span>{source.chunk_count ?? 0} مقطع</span>
                  <span>{source.embedded_chunk_count ?? 0} مضمّن</span>
                  <span>{source.question_count ?? 0} سؤال</span>
                </div>
              </button>
            ))}
            {!sources.length && <p className="admin-muted">لا توجد مصادر مسجلة بعد.</p>}
          </div>
        </Card>

        <Card>
          <div className="section-title">
            <h2>صحة المصدر</h2>
            {selectedSource && <StatusPill tone={statusTone(selectedSource.status)}>{selectedSource.status}</StatusPill>}
          </div>
          {detailError && <ErrorBanner message={detailError} />}
          {!selectedSource && <p className="admin-muted">اختر مصدراً لعرض الصفحات.</p>}
          {selectedSource && (
            <>
              <div className="admin-source-type-grid">
                <article><span>كل الصفحات</span><strong>{selectedSource.pages_summary?.total ?? pages.length}</strong></article>
                <article><span>مكتملة</span><strong>{selectedSource.pages_summary?.completed ?? 0}</strong></article>
                <article><span>فاشلة</span><strong>{selectedSource.pages_summary?.failed ?? failedPages}</strong></article>
                <article><span>تحتاج مراجعة</span><strong>{selectedSource.pages_summary?.needs_review ?? reviewPages}</strong></article>
                <article><span>صفحات PDF</span><strong>{selectedSource.page_count ?? '—'}</strong></article>
                <article><span>metadata ناقصة</span><strong>{selectedSource.missing_metadata_count ?? 0}</strong></article>
                <article><span>مراجعة يدوية</span><strong>{selectedSource.manual_review_count ?? 0}</strong></article>
                <article><span>جاهزية التضمين</span><strong>{selectedSource.ready_for_embedding ? 'جاهزة' : 'غير جاهزة'}</strong></article>
              </div>
              {selectedSource.file_sha256 && (
                <p className="admin-muted">SHA256: {selectedSource.file_sha256.slice(0, 16)}… · {selectedSource.reviewed_metadata_version || 'بدون نسخة مراجعة'}</p>
              )}
              {selectedSource.reviewed_chunks_path && (
                <div className="admin-metric-list">
                  <article>
                    <span>مسار المقاطع المراجعة</span>
                    <strong>{selectedSource.reviewed_chunks_path}</strong>
                  </article>
                  {selectedSource.reviewed_preview_path && (
                    <article>
                      <span>مسار preview</span>
                      <strong>{selectedSource.reviewed_preview_path}</strong>
                    </article>
                  )}
                  {selectedSource.reviewed_metadata_path && (
                    <article>
                      <span>مسار metadata</span>
                      <strong>{selectedSource.reviewed_metadata_path}</strong>
                    </article>
                  )}
                </div>
              )}
              {pagesLoading ? (
                <LoadingSkeleton rows={4} />
              ) : (
                <div className="admin-page-list">
                  {pages.map((page) => {
                    const errors = issueText(page.errors_json);
                    const warnings = issueText(page.warnings_json);
                    const actionable = page.status === 'failed' || page.status.includes('review') || page.status.includes('skipped');
                    return (
                      <article key={`${page.source_id}-${page.page_number}`}>
                        <div className="admin-page-row-head">
                          <strong>صفحة {page.page_number}</strong>
                          <StatusPill tone={statusTone(page.status)}>{page.status}</StatusPill>
                        </div>
                        <span>{page.page_type} · {page.char_count} حرف · جودة {Math.round((page.completeness_score || 0) * 100)}%</span>
                        {page.content_preview && <p>{page.content_preview}</p>}
                        {warnings && <small className="admin-warning-text">تحذيرات: {warnings}</small>}
                        {errors && <small className="admin-error-text">أخطاء: {errors}</small>}
                        {actionable && (
                          <Button
                            variant="secondary"
                            onClick={() => void retryPage(page.id)}
                            disabled={!page.id || retryingPageId === page.id}
                          >
                            {retryingPageId === page.id ? 'جار الإعادة...' : 'إعادة معالجة الصفحة'}
                          </Button>
                        )}
                      </article>
                    );
                  })}
                  {!pages.length && <p className="admin-muted">لا توجد صفحات محفوظة لهذا المصدر بعد.</p>}
                </div>
              )}
            </>
          )}
        </Card>
      </section>
    </div>
  );
};
