import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { curriculumApi, fallbackCurriculumUnits } from '../api';
import { mockLessons, getLessonQualityReport } from '../api/mockChemistryData';
import { Card, PageHeader, Button, ProgressBar, StatusPill } from '../components/DesignSystem';
import type { LessonCatalogItem, LessonQualityReport } from '../types';

const findFallbackLesson = (id: number): LessonCatalogItem | null => {
  for (const unit of fallbackCurriculumUnits) {
    for (const chapter of unit.chapters) {
      const lesson = chapter.lessons.find((item) => item.id === id);
      if (lesson) return lesson;
    }
  }
  return null;
};

const formatPages = (start?: number | null, end?: number | null) => {
  if (!start) return 'غير محددة بعد';
  return end && end !== start ? `${start} - ${end}` : `${start}`;
};

export const LessonDetailPage = () => {
  const { lessonId } = useParams<{ lessonId: string }>();
  const navigate = useNavigate();
  const [showQuizModal, setShowQuizModal] = useState(false);
  const [showFlashcardModal, setShowFlashcardModal] = useState(false);
  const [catalogLesson, setCatalogLesson] = useState<LessonCatalogItem | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');

  // Quiz configuration state
  const [questionsPerLesson, setQuestionsPerLesson] = useState(3);
  const [quizDifficulty, setQuizDifficulty] = useState<'easy' | 'medium' | 'hard' | 'mixed'>('mixed');
  const [quizTypes, setQuizTypes] = useState<string[]>(['mcq', 'true_false', 'short_answer', 'calculation', 'equation_balancing']);

  // Flashcard configuration state
  const [cardsPerLesson, setCardsPerLesson] = useState(4);
  const [cardDifficulty, setCardDifficulty] = useState<'easy' | 'medium' | 'hard' | 'mixed'>('mixed');
  const [cardTypes, setCardTypes] = useState<string[]>(['term', 'definition', 'formula', 'experiment']);
  const [spacedRepetition, setSpacedRepetition] = useState(true);

  const lesson = mockLessons.find((l) => l.lessonId === lessonId) ?? null;
  const report = lesson ? getLessonQualityReport(lesson) : null;

  useEffect(() => {
    const numericId = Number(lessonId);
    if (lesson || !Number.isFinite(numericId)) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setCatalogLoading(true);
      setCatalogError('');
    });
    curriculumApi.getLesson(numericId)
      .then((data) => {
        if (!cancelled) setCatalogLesson(data);
      })
      .catch(() => {
        if (cancelled) return;
        const fallback = findFallbackLesson(numericId);
        setCatalogLesson(fallback);
        if (!fallback) setCatalogError('تعذر تحميل هذا الدرس من الخادم.');
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lesson, lessonId]);

  if (!lesson || !report) {
    if (catalogLoading) {
      return (
        <div className="page-stack lesson-detail-page">
          <PageHeader eyebrow="تفاصيل الدرس" title="جار تحميل الدرس..." subtitle="نقرأ بيانات الدرس من بنية الكتاب." />
        </div>
      );
    }

    if (catalogLesson) {
      return (
        <div className="page-stack lesson-detail-page">
          <PageHeader
            eyebrow="تفاصيل الدرس"
            title={catalogLesson.title_ar}
            subtitle={`الصفحات: ${formatPages(catalogLesson.page_start, catalogLesson.page_end)} · ${catalogLesson.duration_min} دقيقة`}
            action={<Link className="ed-btn ed-btn-ghost" to="/lessons">← العودة للدروس</Link>}
          />
          <div className="lesson-grid">
            <Card className="content-section-card">
              <div className="section-title">
                <h2>مفاهيم الدرس</h2>
                <StatusPill tone={catalogLesson.difficulty >= 3 ? 'gold' : 'teal'}>
                  مستوى {catalogLesson.difficulty}
                </StatusPill>
              </div>
              {catalogLesson.topics.length > 0 ? (
                <div className="topic-chip-row">
                  {catalogLesson.topics.map((topic) => (
                    <span className="topic-chip" key={topic.id}>{topic.title_ar}</span>
                  ))}
                </div>
              ) : (
                <p className="muted-text">لم تُربط مفاهيم بهذا الدرس بعد.</p>
              )}
            </Card>
            <Card className="content-section-card">
              <h3>إجراءات سريعة</h3>
              <div className="action-buttons-row">
                <Link className="ed-btn ed-btn-ghost" to={`/ask-ai?question=${encodeURIComponent(`اشرح لي درس: ${catalogLesson.title_ar}`)}&lessonId=${catalogLesson.id}`}>
                  اسأل الذكاء عن الدرس
                </Link>
                <Link className="ed-btn ed-btn-primary" to={`/quiz?lessonId=${catalogLesson.id}`}>
                  توليد اختبار
                </Link>
                <Link className="ed-btn ed-btn-secondary" to={`/flashcards?lessonId=${catalogLesson.id}`}>
                  بطاقات مراجعة
                </Link>
              </div>
            </Card>
          </div>
        </div>
      );
    }

    return (
      <div className="page-stack error-page">
        <PageHeader eyebrow="خطأ 404" title="الدرس غير موجود" subtitle={catalogError || 'لم نتمكن من العثور على الدرس المطلوب.'} />
        <Link className="ed-btn ed-btn-primary" to="/lessons">العودة للدروس</Link>
      </div>
    );
  }

  const getStatusTone = (status: LessonQualityReport['status']) => {
    if (status === 'ready') return 'teal';
    if (status === 'needs_review') return 'gold';
    return 'coral';
  };

  const getStatusLabel = (status: LessonQualityReport['status']) => {
    if (status === 'ready') return 'جاهز للتوليد';
    if (status === 'needs_review') return 'يحتاج مراجعة (مسودة)';
    return 'مغلق (بحاجة جودة)';
  };

  const toggleQuizType = (type: string) => {
    setQuizTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
  };

  const toggleCardType = (type: string) => {
    setCardTypes(prev => prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]);
  };

  const handleStartQuiz = () => {
    if (report.status === 'blocked') return;
    const typesParam = quizTypes.join(',');
    navigate(`/quiz?auto=true&mode=single_lesson&lessonId=${lesson.lessonId}&questions=${questionsPerLesson}&difficulty=${quizDifficulty}&types=${typesParam}`);
  };

  const handleStartFlashcards = () => {
    if (report.status === 'blocked') return;
    const typesParam = cardTypes.join(',');
    navigate(`/flashcards?auto=true&mode=single_lesson&lessonId=${lesson.lessonId}&cards=${cardsPerLesson}&difficulty=${cardDifficulty}&types=${typesParam}&spaced=${spacedRepetition}`);
  };

  return (
    <div className="page-stack lesson-detail-page">
      <div className="lesson-detail-header-row">
        <PageHeader
          eyebrow="تفاصيل الدرس كيمياء التاسع"
          title={lesson.titleAr}
          subtitle={`الصفحات من ${lesson.pageStart} إلى ${lesson.pageEnd} · وحدة: ${
            lesson.chapterId === 'chapter_1' ? 'المحاليل المائية' :
            lesson.chapterId === 'chapter_2' ? 'المحاليل الحمضية' :
            lesson.chapterId === 'chapter_3' ? 'المحاليل الأساسية' :
            lesson.chapterId === 'chapter_4' ? 'أنواع التفاعلات الكيميائية' : 'الأملاح'
          }`}
          action={
            <div className="header-actions">
              <Link className="ed-btn ed-btn-ghost" to="/lessons">← العودة للدروس</Link>
            </div>
          }
        />
      </div>

      <div className="lesson-grid">
        {/* Quality Check Card */}
        <Card className="quality-report-card">
          <div className="section-title">
            <h2>فحص جودة الدرس (Lesson Quality Check)</h2>
            <StatusPill tone={getStatusTone(report.status)}>{getStatusLabel(report.status)}</StatusPill>
          </div>

          <div className="score-meter">
            <div className="score-value">
              <strong>{report.score}</strong>
              <span>درجة الجودة</span>
            </div>
            <ProgressBar value={report.score} tone={getStatusTone(report.status)} />
          </div>

          <div className="quality-checklist">
            <h3>قائمة متطلبات الدرس</h3>
            <ul className="checklist-items">
              <li className={report.checks.hasTitle ? 'checked' : 'failed'}>
                <span>{report.checks.hasTitle ? '✓' : '✗'}</span> اسم الدرس ومعلوماته الأساسية
              </li>
              <li className={report.checks.hasSourcePages ? 'checked' : 'failed'}>
                <span>{report.checks.hasSourcePages ? '✓' : '✗'}</span> تحديد صفحات الكتاب المدرسي
              </li>
              <li className={report.checks.hasObjectives ? 'checked' : 'failed'}>
                <span>{report.checks.hasObjectives ? '✓' : '✗'}</span> أهداف الدرس التعليمية
              </li>
              <li className={report.checks.hasKeyTerms ? 'checked' : 'failed'}>
                <span>{report.checks.hasKeyTerms ? '✓' : '✗'}</span> المصطلحات الكيميائية المهمة
              </li>
              <li className={report.checks.hasDefinitions ? 'checked' : 'failed'}>
                <span>{report.checks.hasDefinitions ? '✓' : '✗'}</span> التعاريف الكيميائية الرسمية
              </li>
              <li className={report.checks.hasEquations ? 'checked' : 'failed'}>
                <span>{report.checks.hasEquations ? '✓' : '✗'}</span> المعادلات والقوانين الرياضية
              </li>
              <li className={report.checks.hasExamples ? 'checked' : 'failed'}>
                <span>{report.checks.hasExamples ? '✓' : '✗'}</span> المسائل والأمثلة المحلولة
              </li>
              <li className={report.checks.hasExercises ? 'checked' : 'failed'}>
                <span>{report.checks.hasExercises ? '✓' : '✗'}</span> التمارين والمسائل التدريبية
              </li>
              <li className={report.checks.hasValidRagChunks ? 'checked' : 'failed'}>
                <span>{report.checks.hasValidRagChunks ? '✓' : '✗'}</span> مقاطع RAG المرتبطة
              </li>
              <li className={report.checks.hasNoOcrGaps ? 'checked' : 'failed'}>
                <span>{report.checks.hasNoOcrGaps ? '✓' : '✗'}</span> سلامة النص وخلوه من فجوات القراءة (OCR)
              </li>
            </ul>
          </div>

          {report.status === 'blocked' && (
            <div className="blocked-warning-box">
              <strong>⚠ توليد الأسئلة والبطاقات محظور</strong>
              <p>مستوى جودة هذا الدرس منخفض جداً ({report.score}/100). يجب استكمال البيانات التالية أولاً:</p>
              <ul>
                {report.issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="action-buttons-row">
            <Link 
              className="ed-btn ed-btn-ghost" 
              to={`/ask-ai?question=${encodeURIComponent(`اشرح لي بالتفصيل درس: ${lesson.titleAr}`)}${Number.isInteger(Number(lessonId)) ? `&lessonId=${Number(lessonId)}` : ''}`}
            >
              اسأل الذكاء عن الدرس
            </Link>
            <Link 
              className="ed-btn ed-btn-ghost" 
              to={`/book-search?query=${encodeURIComponent(lesson.titleAr)}`}
            >
              RAG بحث في الدرس
            </Link>
          </div>

          <div className="generation-triggers mt-4">
            <Button 
              variant={report.status === 'blocked' ? 'ghost' : 'primary'}
              disabled={report.status === 'blocked'}
              onClick={() => setShowQuizModal(true)}
              className="w-full mb-2"
            >
              {report.status === 'blocked' ? 'توليد اختبار (مغلق)' : 'توليد اختبار مخصص'}
            </Button>
            <Button 
              variant={report.status === 'blocked' ? 'ghost' : 'secondary'}
              disabled={report.status === 'blocked'}
              onClick={() => setShowFlashcardModal(true)}
              className="w-full"
            >
              {report.status === 'blocked' ? 'توليد بطاقات (مغلق)' : 'توليد بطاقات مراجعة'}
            </Button>
          </div>
        </Card>

        {/* Content Details */}
        <div className="lesson-content-details">
          {/* Objectives */}
          <Card className="content-section-card">
            <h3>🎯 أهداف الدرس التعليمية</h3>
            <ul>
              {lesson.objectives.map((obj, i) => (
                <li key={i}>{obj}</li>
              ))}
            </ul>
          </Card>

          {/* Key Terms & Definitions */}
          <Card className="content-section-card">
            <h3>📖 المصطلحات والتعاريف الكيميائية</h3>
            {lesson.keyTerms.length > 0 && (
              <div className="terms-sublist">
                <h4>المصطلحات المهمة:</h4>
                <div className="terms-grid">
                  {lesson.keyTerms.map((kt, i) => (
                    <div className="term-item" key={i}>
                      <strong>{kt.term}</strong>
                      <p>{kt.definition}</p>
                      <small>صفحة {kt.sourcePage}</small>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {lesson.definitions.length > 0 && (
              <div className="definitions-sublist mt-4">
                <h4>التعاريف الرسمية:</h4>
                <div className="definitions-grid">
                  {lesson.definitions.map((def, i) => (
                    <div className="def-item" key={i}>
                      <strong>{def.concept}</strong>
                      <p>{def.explanation}</p>
                      <small>صفحة {def.sourcePage}</small>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {lesson.keyTerms.length === 0 && lesson.definitions.length === 0 && (
              <p className="no-data-text">لا توجد مصطلحات أو تعاريف مستخرجة لهذا الدرس.</p>
            )}
          </Card>

          {/* Equations */}
          {lesson.equations.length > 0 && (
            <Card className="content-section-card">
              <h3>⚗ المعادلات والقوانين الكيميائية</h3>
              <div className="equations-list">
                {lesson.equations.map((eq, i) => (
                  <div className="equation-detail-item" key={i}>
                    <div className="latex-box" dir="ltr">
                      <code>{eq.latex}</code>
                    </div>
                    <p className="eq-explanation">{eq.explanation}</p>
                    {eq.variables.length > 0 && (
                      <div className="eq-variables">
                        <strong>الدلالات:</strong>
                        <ul>
                          {eq.variables.map((v, idx) => (
                            <li key={idx}>{v}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <small className="block mt-2">صفحة المصدر {eq.sourcePage}</small>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Examples */}
          {lesson.examples.length > 0 && (
            <Card className="content-section-card">
              <h3>📝 أمثلة ومسائل محلولة</h3>
              <div className="examples-list">
                {lesson.examples.map((ex, i) => (
                  <div className="example-detail-item" key={i}>
                    <div className="example-q">
                      <strong>السؤال:</strong>
                      <p>{ex.question}</p>
                    </div>
                    <div className="example-a">
                      <strong>الحل المعتمد:</strong>
                      <p dir="ltr" className="text-right font-mono">{ex.solution}</p>
                    </div>
                    <small>صفحة {ex.sourcePage}</small>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Experiments */}
          {lesson.experiments.length > 0 && (
            <Card className="content-section-card">
              <h3>🧪 التجارب العلمية والمخبرية</h3>
              <div className="experiments-list">
                {lesson.experiments.map((exp, i) => (
                  <div className="experiment-detail-item" key={i}>
                    <h4>{exp.title}</h4>
                    <div className="exp-materials">
                      <strong>المواد والأدوات:</strong>
                      <span>{exp.materials.join('، ')}</span>
                    </div>
                    <div className="exp-steps">
                      <strong>الخطوات العملية:</strong>
                      <ol>
                        {exp.steps.map((step, idx) => (
                          <li key={idx}>{step}</li>
                        ))}
                      </ol>
                    </div>
                    <div className="exp-conclusion">
                      <strong>الاستنتاج العلمي:</strong>
                      <p>{exp.conclusion}</p>
                    </div>
                    <small>صفحة المصدر {exp.sourcePage}</small>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Exercises */}
          {lesson.exercises.length > 0 && (
            <Card className="content-section-card">
              <h3>❓ تمارين تدريبية</h3>
              <div className="exercises-list">
                {lesson.exercises.map((exe, i) => (
                  <div className="exercise-detail-item" key={i}>
                    <strong>السؤال:</strong>
                    <p>{exe.question}</p>
                    {exe.answer && (
                      <div className="exercise-ans">
                        <strong>الإجابة:</strong>
                        <p>{exe.answer}</p>
                      </div>
                    )}
                    <small>صفحة {exe.sourcePage}</small>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* RAG Chunks */}
          <Card className="content-section-card text-xs">
            <h3>🔗 معرفات مقاطع RAG المرجعية</h3>
            <div className="rag-chunk-badge-row">
              {lesson.ragChunkIds.map((id) => (
                <StatusPill tone="blue" key={id}>{id}</StatusPill>
              ))}
              {lesson.ragChunkIds.length === 0 && <span>لا توجد معرفات مقاطع</span>}
            </div>
          </Card>
        </div>
      </div>

      {/* QUIZ GENERATION MODAL */}
      <AnimatePresence>
        {showQuizModal && (
          <div className="modal-overlay" onClick={() => setShowQuizModal(false)}>
            <motion.div
              className="modal-content"
              onClick={(e) => e.stopPropagation()}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
            >
              <div className="modal-header">
                <h2>إعداد وتوليد اختبار مخصص</h2>
                <button className="close-btn" onClick={() => setShowQuizModal(false)}>×</button>
              </div>

              <div className="modal-body">
                <div className="modal-quality-indicator">
                  <span>الدرس المحدد: <strong>{lesson.titleAr}</strong></span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs">جودة المحتوى:</span>
                    <StatusPill tone={getStatusTone(report.status)}>{report.score}/100 ({getStatusLabel(report.status)})</StatusPill>
                  </div>
                </div>

                <div className="form-group mt-4">
                  <label>عدد الأسئلة المطلوبة من الدرس:</label>
                  <select value={questionsPerLesson} onChange={(e) => setQuestionsPerLesson(Number(e.target.value))}>
                    <option value={2}>سؤالان</option>
                    <option value={3}>3 أسئلة</option>
                    <option value={5}>5 أسئلة</option>
                    <option value={8}>8 أسئلة</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>مستوى الصعوبة:</label>
                  <div className="radio-group">
                    <label>
                      <input type="radio" name="quizDiff" value="mixed" checked={quizDifficulty === 'mixed'} onChange={() => setQuizDifficulty('mixed')} />
                      مختلط
                    </label>
                    <label>
                      <input type="radio" name="quizDiff" value="easy" checked={quizDifficulty === 'easy'} onChange={() => setQuizDifficulty('easy')} />
                      سهل
                    </label>
                    <label>
                      <input type="radio" name="quizDiff" value="medium" checked={quizDifficulty === 'medium'} onChange={() => setQuizDifficulty('medium')} />
                      متوسط
                    </label>
                    <label>
                      <input type="radio" name="quizDiff" value="hard" checked={quizDifficulty === 'hard'} onChange={() => setQuizDifficulty('hard')} />
                      صعب
                    </label>
                  </div>
                </div>

                <div className="form-group">
                  <label>أنواع الأسئلة لتضمينها:</label>
                  <div className="checkbox-grid">
                    <label>
                      <input type="checkbox" checked={quizTypes.includes('mcq')} onChange={() => toggleQuizType('mcq')} />
                      خيارات متعددة (MCQ)
                    </label>
                    <label>
                      <input type="checkbox" checked={quizTypes.includes('true_false')} onChange={() => toggleQuizType('true_false')} />
                      صح / خطأ
                    </label>
                    <label>
                      <input type="checkbox" checked={quizTypes.includes('short_answer')} onChange={() => toggleQuizType('short_answer')} />
                      إجابة قصيرة
                    </label>
                    <label>
                      <input type="checkbox" checked={quizTypes.includes('calculation')} onChange={() => toggleQuizType('calculation')} />
                      مسائل حسابية
                    </label>
                    <label>
                      <input type="checkbox" checked={quizTypes.includes('equation_balancing')} onChange={() => toggleQuizType('equation_balancing')} />
                      موازنة معادلات
                    </label>
                  </div>
                </div>

                {report.status === 'needs_review' && (
                  <div className="warning-notice-box">
                    <span>💡 ملاحظة: جودة الدرس متوسطة ({report.score}/100)، سيتم توليد أسئلة مسودة وقد تحتوي على بعض النقص.</span>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <Button variant="secondary" onClick={() => setShowQuizModal(false)}>إلغاء</Button>
                <Button onClick={handleStartQuiz} disabled={quizTypes.length === 0}>ابدأ الاختبار الآن</Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* FLASHCARD GENERATION MODAL */}
      <AnimatePresence>
        {showFlashcardModal && (
          <div className="modal-overlay" onClick={() => setShowFlashcardModal(false)}>
            <motion.div
              className="modal-content"
              onClick={(e) => e.stopPropagation()}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
            >
              <div className="modal-header">
                <h2>إعداد وتوليد بطاقات المراجعة</h2>
                <button className="close-btn" onClick={() => setShowFlashcardModal(false)}>×</button>
              </div>

              <div className="modal-body">
                <div className="modal-quality-indicator">
                  <span>الدرس المحدد: <strong>{lesson.titleAr}</strong></span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs">جودة المحتوى:</span>
                    <StatusPill tone={getStatusTone(report.status)}>{report.score}/100 ({getStatusLabel(report.status)})</StatusPill>
                  </div>
                </div>

                <div className="form-group mt-4">
                  <label>عدد البطاقات المطلوبة:</label>
                  <select value={cardsPerLesson} onChange={(e) => setCardsPerLesson(Number(e.target.value))}>
                    <option value={3}>3 بطاقات</option>
                    <option value={4}>4 بطاقات</option>
                    <option value={6}>6 بطاقات</option>
                    <option value={10}>10 بطاقات</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>مستوى الصعوبة للبطاقات:</label>
                  <div className="radio-group">
                    <label>
                      <input type="radio" name="cardDiff" value="mixed" checked={cardDifficulty === 'mixed'} onChange={() => setCardDifficulty('mixed')} />
                      مختلط
                    </label>
                    <label>
                      <input type="radio" name="cardDiff" value="easy" checked={cardDifficulty === 'easy'} onChange={() => setCardDifficulty('easy')} />
                      سهل
                    </label>
                    <label>
                      <input type="radio" name="cardDiff" value="medium" checked={cardDifficulty === 'medium'} onChange={() => setCardDifficulty('medium')} />
                      متوسط
                    </label>
                    <label>
                      <input type="radio" name="cardDiff" value="hard" checked={cardDifficulty === 'hard'} onChange={() => setCardDifficulty('hard')} />
                      صعب
                    </label>
                  </div>
                </div>

                <div className="form-group">
                  <label>أنواع البطاقات المرغوبة:</label>
                  <div className="checkbox-grid">
                    <label>
                      <input type="checkbox" checked={cardTypes.includes('term')} onChange={() => toggleCardType('term')} />
                      مصطلحات ومفاهيم
                    </label>
                    <label>
                      <input type="checkbox" checked={cardTypes.includes('definition')} onChange={() => toggleCardType('definition')} />
                      تعاريف كيميائية
                    </label>
                    <label>
                      <input type="checkbox" checked={cardTypes.includes('formula')} onChange={() => toggleCardType('formula')} />
                      قوانين وصيغ كيميائية
                    </label>
                    <label>
                      <input type="checkbox" checked={cardTypes.includes('experiment')} onChange={() => toggleCardType('experiment')} />
                      خطوات وتجارب
                    </label>
                  </div>
                </div>

                <div className="form-group">
                  <label>خيارات التكرار المتباعد:</label>
                  <label className="checkbox-label">
                    <input type="checkbox" checked={spacedRepetition} onChange={(e) => setSpacedRepetition(e.target.checked)} />
                    تفعيل التكرار المتباعد الذكي (Spaced Repetition)
                  </label>
                </div>

                {report.status === 'needs_review' && (
                  <div className="warning-notice-box">
                    <span>💡 ملاحظة: جودة الدرس متوسطة ({report.score}/100)، سيتم توليد بطاقات مسودة مخصصة للمراجعة الفورية.</span>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <Button variant="secondary" onClick={() => setShowFlashcardModal(false)}>إلغاء</Button>
                <Button onClick={handleStartFlashcards} disabled={cardTypes.length === 0}>ابدأ الدراسة الآن</Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
