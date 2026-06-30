import { useCallback, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { homeworkApi, toErrorMessage } from '../api';
import type { HomeworkSource, HomeworkSolveTextResponse, HomeworkSolveImageResponse } from '../api/homeworkApi';
import { Button, Card, ErrorBanner, PageHeader, SourceCard, StatusPill } from '../components/DesignSystem';
import type { SourceCitation } from '../types';

type SolverTab = 'text' | 'image';

const sampleProblem =
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g من الحمض. احسب التركيز الغرامي والمولي.';

const ACCEPTED_IMAGE_TYPES = 'image/jpeg,image/png,image/webp';
const MAX_FILE_SIZE_MB = 8;

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
  const [activeTab, setActiveTab] = useState<SolverTab>('text');
  const [problemText, setProblemText] = useState(sampleProblem);
  const [result, setResult] = useState<HomeworkSolveTextResponse | HomeworkSolveImageResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  // Image upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<'idle' | 'uploading' | 'solving' | 'done'>('idle');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sources = useMemo(() => normalizeSources(result?.source_chunks), [result?.source_chunks]);
  const guidedSolverUrl = `/guided-lab?problem=${encodeURIComponent(problemText.trim() || result?.problem_text || '')}`;

  const handleFileSelect = useCallback((file: File) => {
    if (!ACCEPTED_IMAGE_TYPES.split(',').includes(file.type)) {
      setError('الرجاء اختيار صورة بصيغة JPEG أو PNG أو WebP فقط.');
      return;
    }
    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`حجم الصورة يتجاوز الحد الأقصى (${MAX_FILE_SIZE_MB} MB).`);
      return;
    }
    setSelectedFile(file);
    setError('');
    setResult(null);
    setUploadProgress('idle');

    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const clearImage = useCallback(() => {
    setSelectedFile(null);
    setImagePreview(null);
    setUploadProgress('idle');
    setResult(null);
    setError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const solveText = async () => {
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

  const solveImage = async () => {
    if (!selectedFile || loading) return;
    setLoading(true);
    setError('');
    setSaved(false);
    try {
      // Step 1: Upload the image
      setUploadProgress('uploading');
      const uploadResult = await homeworkApi.uploadImage(selectedFile);

      // Step 2: Solve the uploaded image
      setUploadProgress('solving');
      const solveResult = await homeworkApi.solveImage(uploadResult.image_path);
      setResult(solveResult);
      setUploadProgress('done');
    } catch (err) {
      setError(toErrorMessage(err, 'تعذر رفع أو حل صورة الواجب. تأكد أن الخادم يعمل ثم أعد المحاولة.'));
      setUploadProgress('idle');
    } finally {
      setLoading(false);
    }
  };

  const uploadStatusLabel = (): string => {
    switch (uploadProgress) {
      case 'uploading': return 'جار رفع الصورة...';
      case 'solving': return 'جار تحليل الصورة وحل المسألة...';
      case 'done': return 'تم الحل بنجاح';
      default: return 'حل من الصورة';
    }
  };

  return (
    <div className="homework-page page-stack">
      <PageHeader
        eyebrow="حل الواجبات"
        title="مساعد الواجبات"
        subtitle="اكتب المسألة أو ارفع صورتها، ثم راجع الحل مع مصادره أو حوّلها إلى جلسة حل موجهة."
      />

      {/* Tab Switcher */}
      <div className="homework-tabs" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === 'text'}
          className={`homework-tab ${activeTab === 'text' ? 'homework-tab--active' : ''}`}
          onClick={() => { setActiveTab('text'); setError(''); }}
        >
          <span className="homework-tab-icon">✏️</span>
          حل نصي
        </button>
        <button
          role="tab"
          aria-selected={activeTab === 'image'}
          className={`homework-tab ${activeTab === 'image' ? 'homework-tab--active' : ''}`}
          onClick={() => { setActiveTab('image'); setError(''); }}
        >
          <span className="homework-tab-icon">📷</span>
          حل من صورة
        </button>
      </div>

      <section className="homework-layout">
        <Card className="homework-input-card">
          {/* Text Solver Tab */}
          {activeTab === 'text' && (
            <>
              <div className="section-title">
                <h2>نص الواجب</h2>
                <StatusPill tone="blue">نصي</StatusPill>
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
              {error && <ErrorBanner message={error} onRetry={solveText} />}
              <div className="guided-card-actions">
                <Button onClick={solveText} disabled={loading || problemText.trim().length < 8}>
                  {loading ? 'جار حل الواجب...' : 'حل الواجب'}
                </Button>
                <Link className="ed-btn ed-btn-secondary" to={guidedSolverUrl}>
                  حوّل إلى حل موجه
                </Link>
              </div>
            </>
          )}

          {/* Image Solver Tab */}
          {activeTab === 'image' && (
            <>
              <div className="section-title">
                <h2>صورة الواجب</h2>
                <StatusPill tone="purple">صورة</StatusPill>
              </div>

              {!imagePreview ? (
                <div
                  className={`homework-dropzone ${isDragging ? 'homework-dropzone--active' : ''}`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
                >
                  <div className="homework-dropzone-content">
                    <span className="homework-dropzone-icon">📤</span>
                    <strong>اسحب الصورة هنا أو اضغط للاختيار</strong>
                    <span className="homework-dropzone-hint">
                      JPEG, PNG, أو WebP — الحد الأقصى {MAX_FILE_SIZE_MB} MB
                    </span>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ACCEPTED_IMAGE_TYPES}
                    onChange={handleInputChange}
                    className="homework-file-input"
                    aria-label="اختر صورة الواجب"
                  />
                </div>
              ) : (
                <div className="homework-preview-container">
                  <div className="homework-preview-header">
                    <StatusPill tone="teal">
                      {selectedFile?.name ?? 'صورة'}
                    </StatusPill>
                    <button className="homework-preview-clear" onClick={clearImage} title="إزالة الصورة">
                      ✕
                    </button>
                  </div>
                  <img
                    src={imagePreview}
                    alt="معاينة صورة الواجب"
                    className="homework-preview-image"
                  />
                  {uploadProgress !== 'idle' && uploadProgress !== 'done' && (
                    <div className="homework-upload-progress">
                      <div className={`homework-progress-bar ${uploadProgress === 'solving' ? 'homework-progress-bar--solving' : ''}`} />
                      <span>{uploadStatusLabel()}</span>
                    </div>
                  )}
                </div>
              )}

              {error && <ErrorBanner message={error} onRetry={solveImage} />}
              <div className="guided-card-actions">
                <Button onClick={solveImage} disabled={loading || !selectedFile}>
                  {loading ? uploadStatusLabel() : 'حل من الصورة'}
                </Button>
                {selectedFile && (
                  <Button variant="secondary" onClick={clearImage} disabled={loading}>
                    صورة أخرى
                  </Button>
                )}
              </div>
            </>
          )}
        </Card>

        <aside className="homework-side-card">
          <Card>
            <StatusPill tone="purple">طريقة أفضل للتعلم</StatusPill>
            <h2>لا تكتف بالجواب النهائي.</h2>
            <p>إذا كانت المسألة حسابية، استخدم الحل الموجه ليطلب منك القانون والتحويل والتعويض خطوة بخطوة.</p>
            <Link className="card-link-button" to={guidedSolverUrl}>ابدأ جلسة موجهة</Link>
          </Card>
          <Card>
            <StatusPill tone="teal">رفع الصور</StatusPill>
            <h2>التقط صورة الواجب من الدفتر.</h2>
            <p>ارفع صورة واضحة بصيغة JPEG أو PNG وسيقوم الذكاء الاصطناعي بتحليلها وحلها خطوة بخطوة.</p>
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
          {'extracted_text' in result && result.extracted_text && (
            <div className="homework-extracted-text">
              <StatusPill tone="blue">النص المستخرج من الصورة</StatusPill>
              <p>{result.extracted_text}</p>
            </div>
          )}
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
