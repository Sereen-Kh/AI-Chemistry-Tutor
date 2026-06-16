import { useEffect, useState } from 'react';
import { adminRagApi, toErrorMessage } from '../../api';
import type { RagDebugResponse, RagQueryLog } from '../../api/adminRagApi';
import { Button, Card, ErrorBanner, PageHeader, StatusPill } from '../../components/DesignSystem';

export const RagQueryLogsPage = () => {
  const [logs, setLogs] = useState<RagQueryLog[]>([]);
  const [lowConfidenceOnly, setLowConfidenceOnly] = useState(false);
  const [debugQuery, setDebugQuery] = useState('ما تعريف الحمض؟');
  const [debugResult, setDebugResult] = useState<RagDebugResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadLogs = async () => {
    setLoading(true);
    setError('');
    try {
      setLogs(await adminRagApi.getQueryLogs({ low_confidence: lowConfidenceOnly || undefined, limit: 50 }));
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تحميل سجلات RAG.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    queueMicrotask(() => void loadLogs());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lowConfidenceOnly]);

  const runDebug = async () => {
    setLoading(true);
    setError('');
    try {
      setDebugResult(await adminRagApi.retrieveDebug(debugQuery));
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر تشغيل retrieve-debug.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack admin-rag-page">
      <PageHeader
        eyebrow="إدارة RAG"
        title="سجلات الاستعلام و Debug Retrieval"
        subtitle="راجع الاستعلامات منخفضة الثقة، ثم اختبر الاسترجاع الخام من نفس الشاشة."
      />
      {error && <ErrorBanner message={error} />}

      <Card className="admin-form-card">
        <div className="section-title">
          <h2>اختبار استرجاع خام</h2>
          <StatusPill tone="purple">تشخيص الاسترجاع</StatusPill>
        </div>
        <label>
          الاستعلام
          <input value={debugQuery} onChange={(event) => setDebugQuery(event.target.value)} />
        </label>
        <Button onClick={runDebug} disabled={loading || !debugQuery.trim()}>تشغيل الاختبار</Button>
        {debugResult && (
          <div className="admin-debug-results">
            <pre>{JSON.stringify(debugResult.diagnostics, null, 2)}</pre>
            {debugResult.chunks.map((chunk) => (
              <article key={chunk.id}>
                <strong>#{chunk.id} · صفحة {chunk.page_number ?? '-'}</strong>
                <span>{chunk.source_type} · {chunk.content_type} · {Math.round(chunk.similarity_score * 100)}%</span>
                <p>{chunk.content.slice(0, 240)}...</p>
              </article>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <div className="section-title">
          <h2>سجلات الاستعلام</h2>
          <label className="checkbox-label">
            <input type="checkbox" checked={lowConfidenceOnly} onChange={(event) => setLowConfidenceOnly(event.target.checked)} />
            منخفضة الثقة فقط
          </label>
        </div>
        <div className="admin-log-table">
          {logs.map((log) => (
            <article key={log.id} className={log.low_confidence ? 'warning' : ''}>
              <strong>{log.query_text}</strong>
              <span>{log.route}</span>
              <span>{log.result_count} نتائج</span>
              <span>أعلى تشابه {log.max_similarity ? Math.round(log.max_similarity * 100) : 0}%</span>
              <span>{new Date(log.created_at).toLocaleString('ar')}</span>
              {log.retrieved_chunks.length > 0 && (
                <small>
                  أعلى مقطع: {log.retrieved_chunks[0].source_type} · صفحة {log.retrieved_chunks[0].page_number ?? '-'}
                </small>
              )}
            </article>
          ))}
          {!logs.length && <p className="admin-muted">لا توجد سجلات مطابقة.</p>}
        </div>
      </Card>
    </div>
  );
};
