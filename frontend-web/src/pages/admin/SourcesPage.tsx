import { useEffect, useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type {
  IngestionPage,
  RagChunkExplorerResponse,
  RagChunkExplorerItem,
  RagIngestionStats,
  RagSourceStatus,
} from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, StatusPill } from '../../components/DesignSystem';

type MissingMetadataFilter = 'all' | 'missing' | 'complete';

const statusTone = (status: string): string => {
  if (['complete', 'embedded', 'reviewed_source_ready'].includes(status) || status.startsWith('completed')) return 'teal';
  if (status === 'failed' || status === 'missing') return 'coral';
  if (status === 'partial' || status.includes('review') || status.includes('skipped')) return 'gold';
  if (status === 'running' || status === 'processing') return 'blue';
  if (status === 'not_registered' || status === 'not_embedded') return 'slate';
  return 'slate';
};

const sourceLabel = (sourceType: RagSourceStatus['source_type']): string =>
  sourceType === 'textbook' ? 'كتاب الكيمياء' : 'كتاب الحلول';

const formatBytes = (value?: number | null): string => {
  if (!value) return '—';
  const mb = value / (1024 * 1024);
  return `${mb >= 10 ? Math.round(mb) : mb.toFixed(1)} MB`;
};

const formatDate = (value?: string | null): string => {
  if (!value) return '—';
  return new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
};

const issueText = (value: IngestionPage['errors_json'] | IngestionPage['warnings_json']): string => {
  if (!value) return '';
  if (Array.isArray(value)) return value.map((item) => String(item)).join('، ');
  return JSON.stringify(value);
};

const qualityLabel = (status?: string | null): string => {
  if (status === 'ready') return 'جاهز';
  if (status === 'needs_review') return 'يحتاج مراجعة';
  if (status === 'blocked') return 'محظور';
  return status || 'غير معروف';
};

const qualityTone = (status?: string | null): string => {
  if (status === 'ready') return 'teal';
  if (status === 'blocked') return 'coral';
  if (status === 'needs_review') return 'gold';
  return 'slate';
};

const embeddingLabel = (status?: string | null): string => {
  if (status === 'completed') return 'مضمّن';
  if (status === 'pending') return 'بانتظار التضمين';
  if (status === 'failed') return 'فشل التضمين';
  if (status === 'processing') return 'قيد التضمين';
  return status || 'غير معروف';
};

export const SourcesPage = () => {
  const [sources, setSources] = useState<RagSourceStatus[]>([]);
  const [stats, setStats] = useState<RagIngestionStats | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<RagSourceStatus['id'] | null>(null);
  const [pages, setPages] = useState<IngestionPage[]>([]);
  const [chunks, setChunks] = useState<RagChunkExplorerResponse | null>(null);
  const [chunkQualityFilter, setChunkQualityFilter] = useState('');
  const [chunkEmbeddingFilter, setChunkEmbeddingFilter] = useState('');
  const [chunkMissingFilter, setChunkMissingFilter] = useState<MissingMetadataFilter>('all');
  const [chunkSearch, setChunkSearch] = useState('');
  const [chunkContentType, setChunkContentType] = useState('');
  const [chunkLegacyFilter, setChunkLegacyFilter] = useState('');
  const [selectedChunk, setSelectedChunk] = useState<RagChunkExplorerItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [pagesLoading, setPagesLoading] = useState(false);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [scanningSourceId, setScanningSourceId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [chunkError, setChunkError] = useState('');

  const loadSources = async () => {
    const [nextSources, nextStats] = await Promise.all([
      adminRagApi.getRagSources(),
      adminRagApi.getStats(),
    ]);
    setSources(nextSources);
    setStats(nextStats);
    setSelectedSourceId((current) => current ?? nextSources[0]?.id ?? null);
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const [nextSources, nextStats] = await Promise.all([
          adminRagApi.getRagSources(),
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
    queueMicrotask(() => void load());
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const selected = sources.find((source) => source.id === selectedSourceId) ?? null;
    if (!selected?.db_source_id) {
      queueMicrotask(() => setPages([]));
      return;
    }
    let cancelled = false;
    const loadPages = async () => {
      setPagesLoading(true);
      setDetailError('');
      try {
        const nextPages = await adminRagApi.getSourcePages(selected.db_source_id as number);
        if (!cancelled) setPages(nextPages);
      } catch (err) {
        if (!cancelled) setDetailError(toErrorMessage(err, 'تعذر تحميل صفحات المصدر.'));
      } finally {
        if (!cancelled) setPagesLoading(false);
      }
    };
    queueMicrotask(() => void loadPages());
    return () => {
      cancelled = true;
    };
  }, [selectedSourceId, sources]);

  useEffect(() => {
    const selected = sources.find((source) => source.id === selectedSourceId) ?? null;
    if (!selected) {
      queueMicrotask(() => setChunks(null));
      return;
    }
    let cancelled = false;
    const loadChunks = async () => {
      setChunksLoading(true);
      setChunkError('');
      try {
        const nextChunks = await adminRagApi.getRagChunks({
          source_type: selected.source_type,
          quality_status: chunkQualityFilter || undefined,
          embedding_status: chunkEmbeddingFilter || undefined,
          missing_metadata:
            chunkMissingFilter === 'all' ? undefined : chunkMissingFilter === 'missing',
          search: chunkSearch || undefined,
          content_type: chunkContentType || undefined,
          legacy_unmapped: chunkLegacyFilter === '' ? undefined : chunkLegacyFilter === 'true',
          limit: 25,
        });
        if (!cancelled) setChunks(nextChunks);
      } catch (err) {
        if (!cancelled) setChunkError(toErrorMessage(err, 'تعذر تحميل مقاطع RAG.'));
      } finally {
        if (!cancelled) setChunksLoading(false);
      }
    };
    queueMicrotask(() => void loadChunks());
    return () => {
      cancelled = true;
    };
  }, [selectedSourceId, sources, chunkQualityFilter, chunkEmbeddingFilter, chunkMissingFilter, chunkSearch, chunkContentType, chunkLegacyFilter]);

  const scanSource = async (sourceId: string) => {
    setScanningSourceId(sourceId);
    setError('');
    setDetailError('');
    try {
      await adminRagApi.scanRagSource(sourceId);
      await loadSources();
      setSelectedSourceId(sourceId as RagSourceStatus['id']);
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر مسح المصدر وتحديث حالته.'));
    } finally {
      setScanningSourceId(null);
    }
  };

  const scanAllSources = async () => {
    setScanningSourceId('all');
    setError('');
    try {
      await Promise.all(['textbook', 'solution_book'].map((sourceId) => adminRagApi.scanRagSource(sourceId)));
      await loadSources();
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر مسح مصادر PDF.'));
    } finally {
      setScanningSourceId(null);
    }
  };

  if (loading) {
    return <main className="page-stack"><LoadingSkeleton rows={6} /></main>;
  }

  const selectedSource = sources.find((source) => source.id === selectedSourceId) ?? null;
  const failedPages = pages.filter((page) => page.status === 'failed').length;
  const reviewPages = pages.filter((page) => ['skipped_dry_run', 'queued_retry'].includes(page.status) || page.status.includes('review')).length;
  const registeredCount = sources.filter((source) => source.db_source_id).length;

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة المصادر"
        title="مصادر RAG"
        subtitle="اكتشاف حالة كتاب الكيمياء وكتاب الحلول قبل الاستخراج والتقطيع والتضمين."
        action={
          <Button variant="secondary" onClick={() => void scanAllSources()} disabled={Boolean(scanningSourceId)}>
            {scanningSourceId === 'all' ? 'جار المسح...' : 'مسح كل المصادر'}
          </Button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <section className="admin-stat-grid">
        <Card><StatusPill tone="blue">مصادر</StatusPill><strong>{sources.length}</strong><span>مصادر Canonical</span></Card>
        <Card><StatusPill tone="teal">مسجلة</StatusPill><strong>{registeredCount}</strong><span>مصادر في قاعدة البيانات</span></Card>
        <Card><StatusPill tone="purple">DB chunks</StatusPill><strong>{stats?.total_chunks ?? 0}</strong><span>مقاطع محفوظة</span></Card>
        <Card><StatusPill tone="gold">Pages</StatusPill><strong>{sources.reduce((sum, source) => sum + (source.page_count ?? 0), 0)}</strong><span>صفحات PDF</span></Card>
      </section>

      <section className="admin-two-column admin-source-detail-layout">
        <Card>
          <div className="section-title">
            <h2>قائمة المصادر</h2>
            <span>{sources.length} مصدر</span>
          </div>
          <div className="admin-source-list">
            {sources.map((source) => (
              <article
                key={source.id}
                className={`admin-source-row ${selectedSourceId === source.id ? 'active' : ''}`}
              >
                <button type="button" onClick={() => setSelectedSourceId(source.id)}>
                  <div>
                    <StatusPill tone={statusTone(source.ingestion_status)}>{source.ingestion_status}</StatusPill>
                    <strong>{sourceLabel(source.source_type)}</strong>
                  </div>
                  <span>{source.filename} · {source.page_count ?? '—'} صفحة · {formatBytes(source.file_size_bytes)}</span>
                  <small>{source.file_path}</small>
                  <div className="admin-source-counters">
                    <span>استخراج: {source.extraction_status}</span>
                    <span>مقاطع: {source.chunk_status}</span>
                    <span>تضمين: {source.embedding_status}</span>
                  </div>
                </button>
                <div className="admin-source-actions">
                  <Button variant="secondary" onClick={() => setSelectedSourceId(source.id)}>عرض التفاصيل</Button>
                  <Button
                    variant="primary"
                    onClick={() => void scanSource(source.id)}
                    disabled={Boolean(scanningSourceId)}
                  >
                    {scanningSourceId === source.id ? 'جار المسح...' : 'Scan'}
                  </Button>
                </div>
              </article>
            ))}
            {!sources.length && <p className="admin-muted">لا توجد مصادر RAG معتمدة بعد.</p>}
          </div>
        </Card>

        <Card>
          <div className="section-title">
            <h2>تفاصيل المصدر</h2>
            {selectedSource && <StatusPill tone={statusTone(selectedSource.ingestion_status)}>{selectedSource.ingestion_status}</StatusPill>}
          </div>
          {detailError && <ErrorBanner message={detailError} />}
          {!selectedSource && <p className="admin-muted">اختر مصدراً لعرض التفاصيل.</p>}
          {selectedSource && (
            <>
              <div className="admin-source-type-grid">
                <article><span>نوع المصدر</span><strong>{sourceLabel(selectedSource.source_type)}</strong></article>
                <article><span>صفحات PDF</span><strong>{selectedSource.page_count ?? '—'}</strong></article>
                <article><span>حجم الملف</span><strong>{formatBytes(selectedSource.file_size_bytes)}</strong></article>
                <article><span>آخر تعديل</span><strong>{formatDate(selectedSource.last_modified_at)}</strong></article>
                <article><span>حالة الاستخراج</span><strong>{selectedSource.extraction_status}</strong></article>
                <article><span>حالة المقاطع</span><strong>{selectedSource.chunk_status}</strong></article>
                <article><span>حالة التضمين</span><strong>{selectedSource.embedding_status}</strong></article>
                <article><span>DB source</span><strong>{selectedSource.db_source_id ?? 'غير مسجل'}</strong></article>
              </div>

              <div className="admin-metric-list">
                <article>
                  <span>المسار</span>
                  <strong>{selectedSource.file_path}</strong>
                </article>
                <article>
                  <span>SHA256</span>
                  <strong>{selectedSource.checksum_sha256 ? `${selectedSource.checksum_sha256.slice(0, 24)}…` : '—'}</strong>
                </article>
                <article>
                  <span>المقاطع المراجعة</span>
                  <strong>{selectedSource.counts.reviewed_chunks ?? 0}</strong>
                </article>
                <article>
                  <span>صفحات بدون مقاطع</span>
                  <strong>{selectedSource.counts.missing_chunk_pages ?? 0}</strong>
                </article>
                <article>
                  <span>مقاطع جاهزة</span>
                  <strong>{selectedSource.counts.ready_chunks ?? 0}</strong>
                </article>
                <article>
                  <span>تحتاج مراجعة</span>
                  <strong>{selectedSource.counts.needs_review_chunks ?? 0}</strong>
                </article>
              </div>

              {(selectedSource.warnings.length > 0 || selectedSource.errors.length > 0) && (
                <div className="admin-metric-list">
                  {selectedSource.warnings.length > 0 && (
                    <article>
                      <span>تحذيرات</span>
                      <strong>{selectedSource.warnings.join('، ')}</strong>
                    </article>
                  )}
                  {selectedSource.errors.length > 0 && (
                    <article>
                      <span>أخطاء</span>
                      <strong>{selectedSource.errors.join('، ')}</strong>
                    </article>
                  )}
                </div>
              )}

              {pagesLoading ? (
                <LoadingSkeleton rows={4} />
              ) : selectedSource.db_source_id ? (
                <div className="admin-page-list">
                  <div className="section-title">
                    <h3>صفحات مسجلة في قاعدة البيانات</h3>
                    <span>{pages.length} صفحة · {failedPages} فاشلة · {reviewPages} مراجعة</span>
                  </div>
                  {pages.map((page) => {
                    const errors = issueText(page.errors_json);
                    const warnings = issueText(page.warnings_json);
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
                      </article>
                    );
                  })}
                  {!pages.length && <p className="admin-muted">لا توجد صفحات DB محفوظة لهذا المصدر بعد. هذا طبيعي في Slice 6A.</p>}
                </div>
              ) : (
                <p className="admin-muted">اضغط Scan لتسجيل المصدر في قاعدة البيانات وتحديث حالته.</p>
              )}

              <div className="admin-page-list">
                <div className="section-title">
                  <h3>مقاطع RAG الجاهزة للتضمين</h3>
                  <span>{chunks?.filtered_total ?? chunks?.total ?? 0} مقطع مطابق · {chunks?.global_counts?.total_chunks ?? chunks?.counts.total_chunks ?? 0} إجمالي</span>
                </div>
                {chunkError && <ErrorBanner message={chunkError} />}
                <div className="admin-source-counters">
                  <label>
                    حالة الجودة
                    <select value={chunkQualityFilter} onChange={(event) => setChunkQualityFilter(event.target.value)}>
                      <option value="">كل الحالات</option>
                      <option value="ready">جاهز</option>
                      <option value="needs_review">يحتاج مراجعة</option>
                      <option value="blocked">محظور</option>
                    </select>
                  </label>
                  <label>
                    حالة التضمين
                    <select value={chunkEmbeddingFilter} onChange={(event) => setChunkEmbeddingFilter(event.target.value)}>
                      <option value="">كل الحالات</option>
                      <option value="pending">بانتظار التضمين</option>
                      <option value="processing">قيد التضمين</option>
                      <option value="completed">مضمّن</option>
                      <option value="failed">فشل</option>
                    </select>
                  </label>
                  <label>
                    البيانات الناقصة
                    <select
                      value={chunkMissingFilter}
                      onChange={(event) => setChunkMissingFilter(event.target.value as MissingMetadataFilter)}
                    >
                      <option value="all">الكل</option>
                      <option value="missing">فيه نقص</option>
                      <option value="complete">مكتمل metadata</option>
                    </select>
                  </label>
                  <label>
                    بحث
                    <input
                      value={chunkSearch}
                      onChange={(event) => setChunkSearch(event.target.value)}
                      placeholder="رقم المقطع أو النص أو الوحدة"
                    />
                  </label>
                  <label>
                    نوع المحتوى
                    <input
                      value={chunkContentType}
                      onChange={(event) => setChunkContentType(event.target.value)}
                      placeholder="concept / formula"
                    />
                  </label>
                  <label>
                    Legacy
                    <select value={chunkLegacyFilter} onChange={(event) => setChunkLegacyFilter(event.target.value)}>
                      <option value="">الكل</option>
                      <option value="true">قديم يحتاج مراجعة</option>
                      <option value="false">مراجَع</option>
                    </select>
                  </label>
                </div>

                <div className="admin-source-type-grid">
                  <article><span>جاهزة</span><strong>{chunks?.counts.ready_chunks ?? 0}</strong></article>
                  <article><span>تحتاج مراجعة</span><strong>{chunks?.counts.needs_review_chunks ?? 0}</strong></article>
                  <article><span>محظورة</span><strong>{chunks?.counts.blocked_chunks ?? 0}</strong></article>
                  <article><span>Metadata ناقصة</span><strong>{chunks?.counts.missing_metadata_chunks ?? 0}</strong></article>
                  <article><span>مضمّنة</span><strong>{chunks?.counts.embedded_chunks ?? 0}</strong></article>
                  <article><span>بانتظار التضمين</span><strong>{chunks?.counts.pending_chunks ?? 0}</strong></article>
                </div>

                {chunksLoading ? (
                  <LoadingSkeleton rows={5} />
                ) : (
                  <>
                    {chunks?.items.map((chunk) => (
                      <article key={chunk.id}>
                        <div className="admin-page-row-head">
                          <strong>Chunk #{chunk.id} · {chunk.reviewed_chunk_id ?? 'بدون ID مراجعة'}</strong>
                          <div className="admin-source-actions">
                            <StatusPill tone={qualityTone(chunk.quality_status)}>
                              {qualityLabel(chunk.quality_status)}
                            </StatusPill>
                            <StatusPill tone={statusTone(chunk.embedding_status)}>
                              {embeddingLabel(chunk.embedding_status)}
                            </StatusPill>
                          </div>
                        </div>
                        <span>
                          {sourceLabel(chunk.source_type as RagSourceStatus['source_type'])}
                          {' · '}
                          {chunk.content_type}
                          {' · '}
                          صفحة {chunk.printed_page_start ?? chunk.page_number ?? '—'}
                          {chunk.printed_page_end && chunk.printed_page_end !== chunk.printed_page_start ? `-${chunk.printed_page_end}` : ''}
                        </span>
                        <span>
                          وحدة: {chunk.unit_id ?? '—'} · درس: {chunk.lesson_id ?? '—'} · نسخة metadata: {chunk.reviewed_metadata_version ?? '—'}
                        </span>
                          {chunk.missing_metadata.length > 0 && (
                          <small className="admin-warning-text">
                            Metadata ناقصة: {chunk.missing_metadata.join('، ')}
                          </small>
                        )}
                        <small>
                          صلاحية التضمين: {chunk.embedding_allowed ? 'نعم' : 'لا'} · البحث: {chunk.rag_search_allowed ? 'نعم' : 'لا'} · توليد الطالب: {chunk.student_generation_allowed ? 'نعم' : 'لا'}
                        </small>
                        {(chunk.reason_codes?.length || chunk.embedding_error || chunk.source_file || chunk.content_hash) && (
                          <details>
                            <summary>تفاصيل metadata والحالة</summary>
                            <small>المصدر: {chunk.source_file ?? '—'}</small>
                            <small>Hash: {chunk.content_hash ?? '—'}</small>
                            <small>الأسباب: {chunk.reason_codes?.join('، ') || '—'}</small>
                            <small>خطأ التضمين: {chunk.embedding_error ?? '—'}</small>
                            <button type="button" onClick={() => setSelectedChunk(chunk)}>عرض JSON</button>
                          </details>
                        )}
                        <p>{chunk.content_preview}</p>
                      </article>
                    ))}
                    {!chunks?.items.length && <p className="admin-muted">لا توجد مقاطع تطابق هذا الفلتر.</p>}
                  </>
                )}
                {selectedChunk && (
                  <div role="dialog" aria-label="تفاصيل مقطع RAG">
                    <div className="section-title">
                      <h3>تفاصيل Chunk #{selectedChunk.id}</h3>
                      <button type="button" onClick={() => setSelectedChunk(null)}>إغلاق</button>
                    </div>
                    <pre>{JSON.stringify(selectedChunk.metadata_json, null, 2)}</pre>
                  </div>
                )}
              </div>
            </>
          )}
        </Card>
      </section>
    </div>
  );
};
