import { useEffect, useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type { RagIngestionStats, RagSource } from '../../api/adminRagApi';
import { Card, ErrorBanner, LoadingSkeleton, PageHeader, StatusPill } from '../../components/DesignSystem';

export const SourcesPage = () => {
  const [sources, setSources] = useState<RagSource[]>([]);
  const [stats, setStats] = useState<RagIngestionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  if (loading) {
    return <main className="page-stack"><LoadingSkeleton rows={6} /></main>;
  }

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة المصادر"
        title="مصادر الكتاب وكتاب الحلول"
        subtitle="راجع مصادر RAG المفهرسة وحالة كل مصدر وعدد المقاطع حسب النوع."
      />
      {error && <ErrorBanner message={error} />}

      <section className="admin-stat-grid">
        <Card><StatusPill tone="blue">مصادر</StatusPill><strong>{stats?.total_sources ?? sources.length}</strong><span>مصادر</span></Card>
        <Card><StatusPill tone="teal">مقاطع</StatusPill><strong>{stats?.total_chunks ?? 0}</strong><span>مقاطع</span></Card>
        <Card><StatusPill tone="purple">أسئلة</StatusPill><strong>{stats?.total_questions ?? 0}</strong><span>أسئلة مستخرجة</span></Card>
        <Card><StatusPill tone="gold">صفحات</StatusPill><strong>{stats?.pages_processed ?? 0}</strong><span>صفحات</span></Card>
      </section>

      <Card>
        <div className="section-title">
          <h2>قائمة المصادر</h2>
          <span>{sources.length} مصدر</span>
        </div>
        <div className="admin-source-list">
          {sources.map((source) => (
            <article key={source.id}>
              <div>
                <StatusPill tone={source.status === 'completed' ? 'teal' : source.status === 'failed' ? 'coral' : 'gold'}>
                  {source.status}
                </StatusPill>
                <strong>{source.title}</strong>
              </div>
              <span>{source.source_type} · {source.grade} · {source.subject}</span>
              <small>{source.file_path || source.original_filename || 'لا يوجد مسار ملف'}</small>
            </article>
          ))}
          {!sources.length && <p className="admin-muted">لا توجد مصادر مسجلة بعد.</p>}
        </div>
      </Card>
    </div>
  );
};
