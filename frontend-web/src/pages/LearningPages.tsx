import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { aiApi, curriculumApi, fallbackCurriculumUnits } from '../api';
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
import type { UnitCatalogItem } from '../types';

const SEMESTER_STORAGE_KEY = 'edumind.activeSemester';
const chapterColors: Array<'blue' | 'teal' | 'gold' | 'coral' | 'purple'> = ['blue', 'teal', 'purple', 'gold', 'coral'];

const filterUnitsBySemester = (units: UnitCatalogItem[], semester: number) =>
  units.filter((unit) => unit.semester === semester);

const formatPages = (start?: number | null, end?: number | null) => {
  if (!start) return 'غير محددة بعد';
  return end && end !== start ? `${start} - ${end}` : `${start}`;
};

const difficultyLabel = (difficulty: number) => {
  if (difficulty <= 1) return 'سهل';
  if (difficulty === 2) return 'متوسط';
  return 'متقدم';
};

export const LessonsPage = () => {
  const [activeSemester, setActiveSemester] = useState(() => {
    const saved = Number(localStorage.getItem(SEMESTER_STORAGE_KEY));
    return saved === 2 ? 2 : 1;
  });
  const [units, setUnits] = useState<UnitCatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    localStorage.setItem(SEMESTER_STORAGE_KEY, String(activeSemester));
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setLoading(true);
      setError('');
      setUsingFallback(false);
    });
    curriculumApi.getUnits(activeSemester)
      .then((data) => {
        if (cancelled) return;
        setUnits(data.length ? data : filterUnitsBySemester(fallbackCurriculumUnits, activeSemester));
        setUsingFallback(data.length === 0);
      })
      .catch(() => {
        if (cancelled) return;
        setUnits(filterUnitsBySemester(fallbackCurriculumUnits, activeSemester));
        setUsingFallback(true);
        setError('تعذر تحميل بنية الكتاب من الخادم. تُعرض بنية مطابقة للكتاب للتجربة فقط.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeSemester]);

  const lessonCount = useMemo(
    () => units.reduce((total, unit) => total + unit.chapters.reduce((sum, chapter) => sum + chapter.lessons.length, 0), 0),
    [units],
  );

  return (
    <div className="page-stack lessons-page">
      <PageHeader
        eyebrow="الدروس"
        title="منهج الكيمياء للصف التاسع"
        subtitle="تصفح المنهج حسب بنية الكتاب الحقيقية: وحدة، فصل، درس، ومفاهيم مرتبطة."
        action={<Link className="ed-btn ed-btn-secondary" to="/study-plan">الخطة الأسبوعية</Link>}
      />

      <Card className="curriculum-toolbar">
        <div>
          <strong>الفصل الدراسي</strong>
          <span>{lessonCount} درساً من بنية الكتاب</span>
        </div>
        <div className="semester-switch" role="tablist" aria-label="اختيار الفصل الدراسي">
          {[1, 2].map((semester) => (
            <button
              key={semester}
              type="button"
              className={activeSemester === semester ? 'active' : ''}
              onClick={() => setActiveSemester(semester)}
              role="tab"
              aria-selected={activeSemester === semester}
            >
              الفصل {semester}
            </button>
          ))}
        </div>
      </Card>

      {error && <ErrorBanner message={error} />}
      {usingFallback && !error && <ErrorBanner message="لا توجد وحدات من الخادم لهذا الفصل حالياً. تُعرض بنية تجريبية مطابقة للكتاب." />}
      {loading && <LoadingSkeleton rows={5} />}

      <div className="chapter-list">
        {!loading && units.map((unit) => (
          <Card key={unit.id} className="chapter-card lesson-unit-card">
            <div className="chapter-head">
              <div>
                <StatusPill tone={activeSemester === 1 ? 'blue' : 'purple'}>الوحدة {unit.unit_number}</StatusPill>
                <h2>{unit.title_ar}</h2>
                <p>{unit.description_ar || unit.title_en}</p>
              </div>
            </div>

            {unit.chapters.map((chapter, chapterIndex) => (
              <section className="lesson-chapter-section" key={chapter.id}>
                <div className="section-title">
                  <div>
                    <StatusPill tone={chapterColors[chapterIndex % chapterColors.length]}>
                      الفصل {chapter.order}
                    </StatusPill>
                    <h3>{chapter.title_ar}</h3>
                  </div>
                  <span className="muted-text">{chapter.lessons.length} دروس</span>
                </div>

                <div className="lesson-list mt-4">
                  {chapter.lessons.map((lesson) => (
                    <div className="lesson-row-with-actions" key={lesson.id}>
                      <div className="lesson-info-box">
                        <strong className="lesson-title">{lesson.order}. {lesson.title_ar}</strong>
                        <span className="lesson-pages">الصفحات: {formatPages(lesson.page_start, lesson.page_end)}</span>
                        {lesson.topics.length > 0 && (
                          <div className="topic-chip-row" aria-label="مفاهيم الدرس">
                            {lesson.topics.slice(0, 5).map((topic) => (
                              <span className="topic-chip" key={topic.id}>{topic.title_ar}</span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="lesson-quality-badge-row">
                        <span className="quality-label">المدة:</span>
                        <StatusPill tone="teal">{lesson.duration_min} دقيقة</StatusPill>
                        <StatusPill tone={lesson.difficulty >= 3 ? 'gold' : 'blue'}>
                          {difficultyLabel(lesson.difficulty)}
                        </StatusPill>
                      </div>

                      <div className="lesson-actions">
                        <Link to={`/lessons/${lesson.id}`} className="ed-btn ed-btn-secondary ed-btn-xs">
                          عرض المحتوى
                        </Link>
                        <Link to={`/quiz?lessonId=${lesson.id}`} className="ed-btn ed-btn-primary ed-btn-xs">
                          توليد اختبار
                        </Link>
                        <Link to={`/flashcards?lessonId=${lesson.id}`} className="ed-btn ed-btn-ghost ed-btn-xs">
                          بطاقات مراجعة
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
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
        teaching_level: 'simple',
        explanation_method: 'direct',
        learning_modes: format === 'text' ? ['text'] : ['text', format],
        student_interests: [],
        interests: [],
        language: 'ar',
        answer_scope: 'book_only',
        source_types: ['textbook', 'solutions'],
      });
      setResult(answer);
    } catch {
      setError('تعذر البحث في مصادر الكتاب حالياً. تأكد من تشغيل الخادم.');
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
