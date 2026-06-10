import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { aiApi } from '../api';
import { mockLessons, getLessonQualityReport } from '../api/mockChemistryData';
import {
  AnswerFormatSelector,
  Button,
  Card,
  ErrorBanner,
  LoadingSkeleton,
  PageHeader,
  SourceCard,
  StatusPill,
} from '../components/DesignSystem';
import type { AiAskResponse, AnswerFormat } from '../types';

const chapterNames: Record<string, { title: string; subtitle: string; color: 'blue' | 'teal' | 'gold' | 'coral' | 'purple' }> = {
  chapter_1: { title: 'المحاليل المائية', subtitle: 'الوحدة الأولى · 4 دروس أساسية', color: 'blue' },
  chapter_2: { title: 'المحاليل الحمضية', subtitle: 'الوحدة الثانية · 3 دروس أساسية', color: 'teal' },
  chapter_3: { title: 'المحاليل الأساسية', subtitle: 'الوحدة الثالثة · درسان', color: 'purple' },
  chapter_4: { title: 'أنواع التفاعلات الكيميائية', subtitle: 'الوحدة الرابعة · 4 تفاعلات رئيسية', color: 'gold' },
  chapter_5: { title: 'الأملاح', subtitle: 'الوحدة الخامسة · درسان', color: 'coral' },
};

export const LessonsPage = () => {
  // Group lessons by chapter
  const chapters = useMemo(() => {
    const map: Record<string, typeof mockLessons> = {};
    mockLessons.forEach((lesson) => {
      if (!map[lesson.chapterId]) {
        map[lesson.chapterId] = [];
      }
      map[lesson.chapterId].push(lesson);
    });
    return Object.entries(chapterNames).map(([id, info]) => ({
      id,
      ...info,
      lessons: map[id] || [],
    }));
  }, []);

  const getStatusTone = (status: 'ready' | 'needs_review' | 'blocked') => {
    if (status === 'ready') return 'teal';
    if (status === 'needs_review') return 'gold';
    return 'coral';
  };

  const getStatusLabel = (status: 'ready' | 'needs_review' | 'blocked') => {
    if (status === 'ready') return 'جاهز للتوليد';
    if (status === 'needs_review') return 'مراجعة (مسودة)';
    return 'محظور (جودة منخفضة)';
  };

  return (
    <div className="page-stack lessons-page">
      <PageHeader
        eyebrow="الدروس"
        title="منهج الكيمياء للصف التاسع"
        subtitle="تنقل بين الوحدات، تابع نتائج فحص جودة الدروس، وابدأ الاختبارات والمراجعات."
        action={<Link className="ed-btn ed-btn-secondary" to="/study-plan">الخطة الأسبوعية</Link>}
      />

      <div className="chapter-list">
        {chapters.map((chapter, index) => (
          <Card key={chapter.id} className="chapter-card lesson-chapter-card">
            <div className="chapter-head">
              <div>
                <StatusPill tone={chapter.color}>الوحدة {index + 1}</StatusPill>
                <h2>{chapter.title}</h2>
                <p>{chapter.subtitle}</p>
              </div>
            </div>
            <div className="lesson-list mt-4">
              {chapter.lessons.map((lesson) => {
                const report = getLessonQualityReport(lesson);
                return (
                  <div className="lesson-row-with-actions" key={lesson.lessonId}>
                    <div className="lesson-info-box">
                      <strong className="lesson-title">{lesson.titleAr}</strong>
                      <span className="lesson-pages">الصفحات: {lesson.pageStart} - {lesson.pageEnd}</span>
                    </div>
                    
                    <div className="lesson-quality-badge-row">
                      <span className="quality-label">جودة المحتوى:</span>
                      <StatusPill tone={getStatusTone(report.status)}>
                        {report.score}/100 ({getStatusLabel(report.status)})
                      </StatusPill>
                    </div>

                    <div className="lesson-actions">
                      <Link to={`/lessons/${lesson.lessonId}`} className="ed-btn ed-btn-secondary ed-btn-xs">
                        عرض المحتوى
                      </Link>
                      {report.status !== 'blocked' ? (
                        <>
                          <Link to={`/quizzes?lessonId=${lesson.lessonId}`} className="ed-btn ed-btn-primary ed-btn-xs">
                            توليد اختبار
                          </Link>
                          <Link to={`/flashcards?lessonId=${lesson.lessonId}`} className="ed-btn ed-btn-ghost ed-btn-xs">
                            بطاقات مراجعة
                          </Link>
                        </>
                      ) : (
                        <span className="blocked-action-pill">التوليد معطل ⚠</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

const ragSamples = [
  'ما هي الحموض؟',
  'لماذا نضيف الحمض إلى الماء وليس العكس؟',
  'ما هو التركيز المولي؟',
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟',
];

export const RagSearchPage = () => {
  const [query, setQuery] = useState(ragSamples[0]);
  const [format, setFormat] = useState<AnswerFormat>('text');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AiAskResponse | null>(null);
  const [error, setError] = useState('');

  const runSearch = async () => {
    const text = query.trim();
    if (!text || loading) return;
    setLoading(true);
    setError('');
    try {
      const answer = await aiApi.ask({
        question: text,
        subject: 'chemistry',
        grade: 'grade_9',
        answer_format: format,
        teaching_style: 'simple',
        interests: [],
        language: 'ar',
        answer_scope: 'book_only',
        source_types: ['textbook', 'solutions'],
      });
      setResult(answer);
    } catch {
      setError('تعذر البحث في مصادر الكتاب حالياً. تأكد من تشغيل backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack rag-search-page">
      <PageHeader
        eyebrow="البحث في الكتاب"
        title="اختبر استرجاع RAG من مصادر الكيمياء"
        subtitle="استخدم هذا القسم لمراجعة الصفحات والمقاطع التي يعتمد عليها المعلّم الذكي."
      />

      <Card className="rag-search-card">
        <div className="rag-query-grid">
          <label>
            السؤال أو المصطلح
            <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={3} />
          </label>
          <div className="rag-controls">
            <AnswerFormatSelector value={format} onChange={setFormat} />
            <Button onClick={runSearch} disabled={loading || !query.trim()}>{loading ? 'جار البحث...' : 'بحث موثق'}</Button>
          </div>
        </div>
        <div className="suggestion-row">
          {ragSamples.map((sample) => (
            <button key={sample} type="button" onClick={() => setQuery(sample)}>{sample}</button>
          ))}
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}
      {loading && <LoadingSkeleton rows={4} />}
      {result && (
        <Card className="rag-result-card">
          <div className="section-title">
            <h2>الإجابة المسترجعة</h2>
            <StatusPill tone={result.confidence >= 0.7 ? 'teal' : result.confidence >= 0.45 ? 'gold' : 'coral'}>
              ثقة {Math.round(result.confidence * 100)}%
            </StatusPill>
          </div>
          <p className="rag-answer">{result.answer}</p>
          {result.source_page_image_url && (
            <figure className="answer-media">
              <img src={result.source_page_image_url} alt="صفحة من كتاب الكيمياء" />
              <figcaption>صفحة المصدر من الكتاب</figcaption>
            </figure>
          )}
          {result.sources.length > 0 && (
            <div className="source-grid">
              {result.sources.map((source) => <SourceCard key={`${source.chunk_id}-${source.page}`} source={source} />)}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
