import { useState, useEffect, useMemo, useRef } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { quizGenerationErrorMessage, quizzesApi } from '../api/quizzesApi';
import { Card, PageHeader, Button, ProgressBar, StatusPill, LoadingSkeleton, ErrorBanner } from '../components/DesignSystem';
import { getCurriculumLessonQuality, lessonPageRange, useActiveCurriculum } from '../hooks/useActiveCurriculum';
import type { QuizGenerationConfig, GeneratedQuizQuestion } from '../types';

type QuizMode = QuizGenerationConfig['mode'];
type QuizDifficulty = QuizGenerationConfig['difficulty'];
type QuizQuestionType = QuizGenerationConfig['questionTypes'][number];
type QuizAnswerReview = {
  questionId: string;
  question: string;
  userAnswer: string;
  correctAnswer: string;
  explanation: string;
  isCorrect: boolean;
};

export const QuizzesPage = () => {
  const location = useLocation();

  // Route/Query parameters parser
  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const paramLessonId = queryParams.get('lessonId');
  const paramAuto = queryParams.get('auto') === 'true';
  const autoGenerationStartedRef = useRef(false);

  // Config UI State
  const [mode, setMode] = useState<QuizMode>(paramLessonId ? 'single_lesson' : 'single_lesson');
  const [selectedLessonIds, setSelectedLessonIds] = useState<string[]>(paramLessonId ? [paramLessonId] : []);
  const [selectedTopicId, setSelectedTopicId] = useState<string>('');
  const [selectedChapterId, setSelectedChapterId] = useState<string>('');
  const [questionsPerLesson, setQuestionsPerLesson] = useState<number>(3);
  const [difficulty, setDifficulty] = useState<QuizDifficulty>('mixed');
  const [questionTypes, setQuestionTypes] = useState<QuizGenerationConfig['questionTypes']>(['mcq', 'true_false', 'short_answer', 'calculation', 'equation_balancing']);
  
  // Game Play State
  const [gameState, setGameState] = useState<'setup' | 'generating' | 'playing' | 'results'>('setup');
  const [questions, setQuestions] = useState<GeneratedQuizQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOptionIndex, setSelectedOptionIndex] = useState<number | null>(null);
  const [textAnswer, setTextAnswer] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isCurrentCorrect, setIsCurrentCorrect] = useState(false);
  const [score, setScore] = useState(0);
  const [error, setError] = useState('');
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [streak, setStreak] = useState(0);
  const [answerReviews, setAnswerReviews] = useState<QuizAnswerReview[]>([]);
  const [showQualityReport, setShowQualityReport] = useState(false);
  const [lastGenerationConfig, setLastGenerationConfig] = useState<QuizGenerationConfig | null>(null);

  const { allLessons, chapters, loading: curriculumLoading, usingFallback: usingFallbackCurriculum } = useActiveCurriculum();
  const effectiveSelectedChapterId = selectedChapterId || (chapters[0] ? String(chapters[0].id) : '');

  // Compute selected lessons based on mode
  const currentSelectedLessons = useMemo(() => {
    if (mode === 'single_lesson') {
      return allLessons.filter(l => selectedLessonIds.includes(String(l.id)));
    }
    if (mode === 'selected_lessons') {
      return allLessons.filter(l => selectedLessonIds.includes(String(l.id)));
    }
    if (mode === 'chapter') {
      return allLessons.filter(l => String(l.chapter_id) === effectiveSelectedChapterId || String(l.chapter.id) === effectiveSelectedChapterId);
    }
    if (mode === 'weak_lessons') {
      return allLessons.filter(l => l.difficulty >= 3).slice(0, 5);
    }
    if (mode === 'study_plan' || mode === 'exam_review') {
      return allLessons.filter(l => l.difficulty <= 3).slice(0, 4);
    }
    return [];
  }, [mode, selectedLessonIds, effectiveSelectedChapterId, allLessons]);
  const selectedSingleLesson = mode === 'single_lesson' ? currentSelectedLessons[0] : null;

  // Compute validation report for selected lessons
  const validationReport = useMemo(() => {
    const reports = currentSelectedLessons.map(getCurriculumLessonQuality);
    const blocked = reports.filter(r => r.status === 'blocked');
    const needsReview = reports.filter(r => r.status === 'needs_review');
    
    return {
      reports,
      isBlocked: blocked.length > 0,
      hasWarning: needsReview.length > 0,
      blockedLessons: blocked,
      needsReviewLessons: needsReview
    };
  }, [currentSelectedLessons]);

  const handleGenerateQuiz = async (overrideConfig?: QuizGenerationConfig) => {
    setError('');
    setGameState('generating');

    const config: QuizGenerationConfig = overrideConfig || {
      mode,
      lessonIds: currentSelectedLessons.map(l => String(l.id)),
      topicId: selectedTopicId || undefined,
      chapterIds: mode === 'chapter' && effectiveSelectedChapterId ? [effectiveSelectedChapterId] : undefined,
      questionsPerLesson,
      difficulty,
      questionTypes,
      includeSourcePage: true,
      requireExplanation: true,
      avoidDuplicateQuestions: true
    };
    setLastGenerationConfig(config);

    if (config.lessonIds.length === 0) {
      setError('يرجى تحديد درس واحد على الأقل لتوليد الاختبار.');
      setGameState('setup');
      return;
    }

    // Double check blocking
    const selectedReports = allLessons
      .filter(l => config.lessonIds.includes(String(l.id)))
      .map(getCurriculumLessonQuality);
    
    if (selectedReports.some(r => r.status === 'blocked')) {
      setError('لا يمكن توليد الاختبار. أحد الدروس المحددة محظور بسبب نقص الجودة.');
      setGameState('setup');
      return;
    }

    try {
      const generated = await quizzesApi.generateQuiz(config);
      if (generated.length === 0) {
        setError('لم نتمكن من توليد أسئلة بناءً على التفضيلات المحددة. حاول اختيار أنواع أسئلة أخرى.');
        setGameState('setup');
      } else {
        setQuestions(generated);
        setCurrentIndex(0);
        setSelectedOptionIndex(null);
        setTextAnswer('');
        setSubmitted(false);
        setScore(0);
        setTimeElapsed(0);
        setStreak(0);
        setAnswerReviews([]);
        setGameState('playing');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : quizGenerationErrorMessage(err));
      setGameState('setup');
    }
  };

  const handleToggleLessonSelection = (lessonId: string) => {
    setSelectedLessonIds(prev => 
      prev.includes(lessonId)
        ? prev.filter(id => id !== lessonId) 
        : [...prev, lessonId]
    );
    setSelectedTopicId('');
  };

  const handleToggleType = (type: QuizQuestionType) => {
    setQuestionTypes(prev => 
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const handleCheckAnswer = () => {
    if (submitted) return;

    const currentQ = questions[currentIndex];
    let correct: boolean;

    if (currentQ.questionType === 'mcq' || currentQ.questionType === 'true_false') {
      if (selectedOptionIndex === null) return;
      correct = selectedOptionIndex === currentQ.correctOptionIndex;
    } else {
      // For short answers / calculations / equation balancing: check text similarity
      const normalizedInput = textAnswer.trim().toLowerCase().replace(/\s+/g, '');
      const normalizedCorrect = currentQ.correctAnswer.trim().toLowerCase().replace(/\s+/g, '');
      correct = normalizedInput === normalizedCorrect || normalizedInput.includes(normalizedCorrect) || normalizedCorrect.includes(normalizedInput);
    }

    setIsCurrentCorrect(correct);
    const userAnswer = currentQ.questionType === 'mcq' || currentQ.questionType === 'true_false'
      ? currentQ.options?.[selectedOptionIndex ?? -1] ?? ''
      : textAnswer;
    setAnswerReviews((current) => [
      ...current.filter((item) => item.questionId !== currentQ.id),
      {
        questionId: currentQ.id,
        question: currentQ.question,
        userAnswer,
        correctAnswer: currentQ.correctAnswer,
        explanation: currentQ.explanation,
        isCorrect: correct,
      },
    ]);
    if (correct) {
      setScore(prev => prev + 1);
      setStreak(prev => prev + 1);
    } else {
      setStreak(0);
    }
    setSubmitted(true);

    // Call submit answer in backend
    void quizzesApi.submitQuizAnswer('session_quiz', currentQ.id, 
      currentQ.questionType === 'mcq' || currentQ.questionType === 'true_false' 
        ? String(selectedOptionIndex) 
        : textAnswer
    );
  };

  const handleSelfRate = (isCorrect: boolean) => {
    const currentQ = questions[currentIndex];
    if (isCorrect) {
      setScore(prev => prev + 1);
      setIsCurrentCorrect(true);
    } else {
      setIsCurrentCorrect(false);
    }
    setAnswerReviews((current) => [
      ...current.filter((item) => item.questionId !== currentQ.id),
      {
        questionId: currentQ.id,
        question: currentQ.question,
        userAnswer: textAnswer || 'تقييم ذاتي دون إجابة مكتوبة',
        correctAnswer: currentQ.correctAnswer,
        explanation: currentQ.explanation,
        isCorrect,
      },
    ]);
    setSubmitted(true);
  };

  const handleNextQuestion = () => {
    if (currentIndex + 1 < questions.length) {
      setCurrentIndex(prev => prev + 1);
      setSelectedOptionIndex(null);
      setTextAnswer('');
      setSubmitted(false);
    } else {
      setGameState('results');
      void quizzesApi.submitQuizResult('session_quiz', score, questions.length);
    }
  };

  const currentQuestion = questions[currentIndex];

  useEffect(() => {
    if (gameState !== 'playing') return;
    const interval = window.setInterval(() => setTimeElapsed((current) => current + 1), 1000);
    return () => window.clearInterval(interval);
  }, [gameState]);

  const formattedElapsed = `${Math.floor(timeElapsed / 60)}:${String(timeElapsed % 60).padStart(2, '0')}`;

  // Auto-generate if specified in route params. Kept after generator declaration
  // so React Compiler and ESLint can track the function binding correctly.
  useEffect(() => {
    if (!paramAuto) return;
    if (autoGenerationStartedRef.current) return;
    if (!paramLessonId) {
      setError('لا يوجد درس محدد لتوليد الاختبار.');
      return;
    }
    if (curriculumLoading) return;
    const qCount = Number(queryParams.get('questions') || '3');
    const qDiff = (queryParams.get('difficulty') || 'mixed') as QuizDifficulty;
    const qTypes = (queryParams.get('types') || 'mcq').split(',') as QuizQuestionType[];

    const config: QuizGenerationConfig = {
      mode: 'single_lesson',
      lessonIds: [paramLessonId],
      questionsPerLesson: qCount,
      difficulty: qDiff,
      questionTypes: qTypes,
      includeSourcePage: true,
      requireExplanation: true,
      avoidDuplicateQuestions: true
    };

    const lesson = allLessons.find(l => String(l.id) === paramLessonId);
    if (!lesson) {
      setError('تعذر تحميل بيانات الدرس المحدد.');
      return;
    }
    autoGenerationStartedRef.current = true;
    const report = getCurriculumLessonQuality(lesson);
    if (report.status !== 'blocked') {
      queueMicrotask(() => void handleGenerateQuiz(config));
    } else {
      queueMicrotask(() => setError(`تعذر التوليد التلقائي: درس "${lesson.title_ar}" محظور بسبب جودة المحتوى.`));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramAuto, paramLessonId, queryParams, allLessons, curriculumLoading]);

  return (
    <div className="page-stack quizzes-page">
      <PageHeader
        eyebrow="مدرّب الكيمياء"
        title="الاختبارات الذكية للدروس"
        subtitle="اختبارات مبنية على محتوى الدرس ونواتج التعلم، مع مراجعة شاملة للإجابات والتفسيرات."
      />

      {usingFallbackCurriculum && <ErrorBanner message="تعذر تحميل المنهج من الخادم، لذلك نعرض بنية الكتاب الاحتياطية مؤقتاً." />}
      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => {
            if (lastGenerationConfig) {
              void handleGenerateQuiz(lastGenerationConfig);
            } else {
              setError('');
            }
          }}
        />
      )}

      {/* SETUP GAME STATE */}
      {gameState === 'setup' && (
        <div className={`quiz-setup-grid ${showQualityReport ? 'has-report' : 'report-collapsed'}`}>
          {/* Config form */}
          <Card className="quiz-config-card">
            <div className="section-title">
              <h2>تكوين معايير الاختبار</h2>
              <Button variant="ghost" onClick={() => setShowQualityReport((open) => !open)} className="ed-btn-xs">
                {showQualityReport ? 'إخفاء تقرير الجودة' : 'عرض تقرير الجودة'}
              </Button>
            </div>

            <div className="form-group">
              <label>نمط توليد الاختبار:</label>
              <select value={mode} onChange={(e) => { setMode(e.target.value as QuizMode); setSelectedLessonIds([]); setSelectedTopicId(''); }}>
                <option value="single_lesson">درس واحد محدد</option>
                <option value="selected_lessons">مجموعة دروس محددة</option>
                <option value="chapter">فصل كامل من الوحدة</option>
                <option value="weak_lessons">دروس تحتاج لمراجعة (تحت 80%)</option>
                <option value="study_plan">خطة المذاكرة اليومية</option>
                <option value="exam_review">مراجعة الامتحان الشاملة</option>
              </select>
            </div>

            {/* Mode Specific Inputs */}
            {mode === 'single_lesson' && (
              <div className="form-group">
                <label>اختر الدرس:</label>
                {curriculumLoading ? <LoadingSkeleton rows={3} /> : (
                  <div className="lesson-selector-grid">
                    {allLessons.map((lesson) => {
                      const lessonId = String(lesson.id);
                      const selected = selectedLessonIds.includes(lessonId);
                      return (
                        <button
                          key={lesson.id}
                          type="button"
                          className={`lesson-select-card ${selected ? 'selected' : ''}`}
                          onClick={() => { setSelectedLessonIds([lessonId]); setSelectedTopicId(''); }}
                          aria-pressed={selected}
                        >
                          <span className="lesson-num">درس {lesson.order}</span>
                          <strong>{lesson.title_ar}</strong>
                          <small>{lesson.unit.title_ar} · {lessonPageRange(lesson)}</small>
                          {selected && <span className="check-mark">✓</span>}
                        </button>
                      );
                    })}
                  </div>
                )}
                {selectedSingleLesson && (
                  <div className="selected-lesson-topics-panel">
                    <div className="selected-lesson-topics-head">
                      <strong>موضوعات {selectedSingleLesson.title_ar}</strong>
                      <span>{selectedSingleLesson.topics.length ? `${selectedSingleLesson.topics.length} موضوعات` : 'لا توجد موضوعات مرتبطة بهذا الدرس'}</span>
                    </div>
                    {selectedSingleLesson.topics.length ? (
                      <div className="topic-chip-row selectable">
                        <button
                          type="button"
                          className={`topic-chip ${selectedTopicId ? '' : 'active'}`}
                          onClick={() => setSelectedTopicId('')}
                        >
                          كل موضوعات الدرس
                        </button>
                        {selectedSingleLesson.topics.map((topic) => (
                          <button
                            key={topic.id}
                            type="button"
                            className={`topic-chip ${selectedTopicId === String(topic.id) ? 'active' : ''}`}
                            onClick={() => setSelectedTopicId(String(topic.id))}
                          >
                            {topic.title_ar}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p className="muted-text">أضف موضوعات لهذا الدرس من بيانات المنهج حتى تظهر هنا.</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {mode === 'selected_lessons' && (
              <div className="form-group">
                <label>اختر الدروس المطلوبة:</label>
                {curriculumLoading ? <LoadingSkeleton rows={3} /> : (
                  <div className="lesson-selector-grid">
                    {allLessons.map((lesson) => {
                      const lessonId = String(lesson.id);
                      const selected = selectedLessonIds.includes(lessonId);
                      return (
                        <button
                          key={lesson.id}
                          type="button"
                          className={`lesson-select-card ${selected ? 'selected' : ''}`}
                          onClick={() => handleToggleLessonSelection(lessonId)}
                          aria-pressed={selected}
                        >
                          <span className="lesson-num">درس {lesson.order}</span>
                          <strong>{lesson.title_ar}</strong>
                          <small>{lesson.chapter.title_ar} · {lessonPageRange(lesson)}</small>
                          {selected && <span className="check-mark">✓</span>}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {mode === 'chapter' && (
              <div className="form-group">
                <label>اختر الفصل داخل الوحدة:</label>
                <select value={effectiveSelectedChapterId} onChange={(e) => setSelectedChapterId(e.target.value)}>
                  {chapters.map((chapter) => (
                    <option key={chapter.id} value={String(chapter.id)}>
                      {chapter.unit.title_ar} · {chapter.title_ar}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="form-group-row">
              <div className="form-group">
                <label>الأسئلة لكل درس:</label>
                <input 
                  type="number" 
                  min={1} 
                  max={10} 
                  value={questionsPerLesson} 
                  onChange={(e) => setQuestionsPerLesson(Math.max(1, Number(e.target.value)))} 
                />
              </div>
              <div className="form-group">
                <label>مستوى الصعوبة:</label>
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as QuizDifficulty)}>
                  <option value="mixed">مختلط</option>
                  <option value="easy">سهل</option>
                  <option value="medium">متوسط</option>
                  <option value="hard">صعب</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>أنواع الأسئلة المرغوبة:</label>
              <div className="type-pill-row" aria-label="أنواع الأسئلة">
                {[
                  { value: 'mcq' as const, label: 'خيارات متعددة', icon: 'MCQ' },
                  { value: 'true_false' as const, label: 'صح أم خطأ', icon: '✓' },
                  { value: 'short_answer' as const, label: 'إجابة قصيرة', icon: 'SA' },
                  { value: 'calculation' as const, label: 'مسائل حسابية', icon: '∑' },
                  { value: 'equation_balancing' as const, label: 'موازنة معادلات', icon: '→' },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`type-pill ${questionTypes.includes(option.value) ? 'active' : ''}`}
                    onClick={() => handleToggleType(option.value)}
                    aria-pressed={questionTypes.includes(option.value)}
                  >
                    <span>{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="setup-summary-bar">
              <strong>{currentSelectedLessons.length} دروس مختارة</strong>
              <span>{Math.max(1, currentSelectedLessons.length) * questionsPerLesson} أسئلة متوقعة</span>
              <span>{questionTypes.length} أنواع أسئلة</span>
            </div>

            <Button 
              onClick={() => handleGenerateQuiz()} 
              disabled={validationReport.isBlocked || currentSelectedLessons.length === 0 || questionTypes.length === 0}
              className="w-full mt-4"
            >
              توليد وبدء الاختبار
            </Button>
          </Card>

          {/* Quality check display */}
          {showQualityReport && (
            <Card className="quiz-quality-report-sidebar">
              <div className="section-title">
                <h2>تقرير سلامة توليد الأسئلة</h2>
              </div>
              {currentSelectedLessons.length === 0 ? (
                <p className="no-data-text text-sm">حدد درساً أو مجموعة دروس لرؤية تقرير فحص الجودة الخاص بها.</p>
              ) : (
                <div className="quiz-lessons-status-report">
                  <p className="text-sm mb-3">الدروس المحددة للاختبار ({currentSelectedLessons.length}):</p>
                  <div className="status-lesson-list">
                    {validationReport.reports.map(rep => {
                      const l = allLessons.find(m => String(m.id) === rep.lessonId);
                      return (
                        <div className={`status-lesson-item ${rep.status}`} key={rep.lessonId}>
                          <div className="flex justify-between items-center">
                            <strong>{l?.title_ar}</strong>
                            <span className={`text-xs badge-${rep.status}`}>
                              {rep.status === 'ready' ? 'جاهز' : rep.status === 'needs_review' ? 'مسودة' : 'محظور'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <ProgressBar value={rep.score} tone={rep.status === 'ready' ? 'teal' : rep.status === 'needs_review' ? 'gold' : 'coral'} />
                            <span className="text-xs font-mono">{rep.score}/100</span>
                          </div>

                          {rep.status === 'blocked' && (
                            <div className="blocked-items-preview mt-2">
                              <strong>العناصر المفقودة التي تمنع التوليد:</strong>
                              <ul>
                                {rep.issues.map((issue, idx) => (
                                  <li key={idx}>• {issue}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {validationReport.isBlocked && (
                    <div className="warning-card-box tone-coral mt-4">
                      <p className="text-sm">⚠ يحتوي التحديد الحالي على دروس <strong>محظورة التوليد</strong>. يرجى إزالة الدروس ذات الجودة المتدنية للتمكن من بدء الاختبار.</p>
                    </div>
                  )}

                  {validationReport.hasWarning && !validationReport.isBlocked && (
                    <div className="warning-card-box tone-gold mt-4">
                      <p className="text-sm">💡 تنبيه: يحتوي التحديد على دروس <strong>تحتاج مراجعة</strong>. سيتم استخدام نصوص مسودة لتوليد بعض الأسئلة.</p>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* GENERATING LOADING STATE */}
      {gameState === 'generating' && (
        <Card className="quiz-generating-loader text-center">
          <LoadingSkeleton rows={4} />
          <p className="mt-4 text-lg">جاري فحص محتوى الدروس وتوليد الأسئلة من RAG ...</p>
        </Card>
      )}

      {/* ACTIVE QUIZ PLAYER STATE */}
      {gameState === 'playing' && currentQuestion && (
        <div className="quiz-player-container">
          <Card className="quiz-progress-card">
            <div className="player-progress-header">
              <span>السؤال <strong>{currentIndex + 1}</strong> من <strong>{questions.length}</strong></span>
              <div className="quiz-player-badges">
                <StatusPill tone="purple">النتيجة: {score}/{currentIndex}</StatusPill>
                <StatusPill tone="blue">الوقت: {formattedElapsed}</StatusPill>
                {streak >= 2 && <StatusPill tone="gold">{streak} إجابات متتالية</StatusPill>}
              </div>
            </div>
            <ProgressBar value={Math.round(((currentIndex + 1) / questions.length) * 100)} tone="blue" />
          </Card>

          <Card className="quiz-question-card mt-4">
            <div className="question-header">
              <StatusPill tone="blue">
                {currentQuestion.questionType === 'mcq' ? 'سؤال خيارات' : 
                 currentQuestion.questionType === 'true_false' ? 'صح / خطأ' :
                 currentQuestion.questionType === 'short_answer' ? 'إجابة قصيرة' :
                 currentQuestion.questionType === 'calculation' ? 'مسألة حسابية' : 'موازنة معادلة'}
              </StatusPill>
              <StatusPill tone="gold">صعوبة: {currentQuestion.difficulty === 'easy' ? 'سهل' : currentQuestion.difficulty === 'medium' ? 'متوسط' : 'صعب'}</StatusPill>
            </div>

            <h2 className="question-text mt-4">{currentQuestion.question}</h2>

            {/* OPTIONS RENDERER FOR MCQ / TRUE-FALSE */}
            {(currentQuestion.questionType === 'mcq' || currentQuestion.questionType === 'true_false') && currentQuestion.options && (
              <div className="quiz-choice-grid mt-6">
                {currentQuestion.options.map((option, idx) => {
                  let classes = '';
                  if (selectedOptionIndex === idx) classes += ' selected';
                  if (submitted) {
                    if (idx === currentQuestion.correctOptionIndex) classes += ' correct correct-pulse';
                    else if (selectedOptionIndex === idx) classes += ' wrong wrong-shake';
                  }

                  return (
                    <button
                      key={idx}
                      type="button"
                      disabled={submitted}
                      className={classes}
                      onClick={() => setSelectedOptionIndex(idx)}
                    >
                      {option}
                    </button>
                  );
                })}
              </div>
            )}

            {/* INPUT FIELD FOR SHORT ANSWER / CALCULATION / EQUATION */}
            {!(currentQuestion.questionType === 'mcq' || currentQuestion.questionType === 'true_false') && (
              <div className="quiz-input-box mt-6">
                <label>اكتب إجابتك هنا:</label>
                <textarea 
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  disabled={submitted}
                  rows={3}
                  placeholder="أدخل الرموز الكيميائية أو القيمة الحسابية أو الشرح..."
                  dir={currentQuestion.questionType === 'equation_balancing' ? 'ltr' : 'rtl'}
                />
              </div>
            )}

            {/* ACTION BUTTON ROW */}
            <div className="button-row mt-6">
              {!submitted ? (
                <>
                  <Button 
                    onClick={handleCheckAnswer} 
                    disabled={
                      (currentQuestion.questionType === 'mcq' || currentQuestion.questionType === 'true_false') 
                        ? selectedOptionIndex === null 
                        : textAnswer.trim() === ''
                    }
                  >
                    التحقق من الإجابة
                  </Button>
                  
                  {/* Option to self-rate for complex open queries */}
                  {!(currentQuestion.questionType === 'mcq' || currentQuestion.questionType === 'true_false') && (
                    <div className="flex gap-2">
                      <Button variant="ghost" onClick={() => handleSelfRate(true)}>أعرف الإجابة (صح)</Button>
                      <Button variant="ghost" onClick={() => handleSelfRate(false)} className="text-coral">لا أعرف (خطأ)</Button>
                    </div>
                  )}
                </>
              ) : (
                <Button onClick={handleNextQuestion}>
                  {currentIndex + 1 < questions.length ? 'السؤال التالي ←' : 'عرض النتيجة النهائية'}
                </Button>
              )}

              <Link 
                className="ed-btn ed-btn-ghost" 
                to={`/ask-ai?question=${encodeURIComponent(`اشرح لي بالتفصيل كيف نحل هذا السؤال الكيميائي: ${currentQuestion.question}`)}`}
              >
                اشرح لي بالذكاء
              </Link>
            </div>

            {/* EXPLANATION AND CITATIONS OVERLAY */}
            {submitted && (
              <div className={`quiz-explanation-overlay mt-6 ${isCurrentCorrect ? 'correct' : 'wrong'}`}>
                <div className="explanation-status-header">
                  <strong>{isCurrentCorrect ? 'إجابة صحيحة! أحسنت 🎯' : 'يحتاج مراجعة 📚'}</strong>
                  <span className="source-citation font-mono">صفحة الكتاب المدرسي: {currentQuestion.sourcePage}</span>
                </div>
                
                {/* For non-mcq show the exact expected answer */}
                {!(currentQuestion.questionType === 'mcq' || currentQuestion.questionType === 'true_false') && (
                  <div className="expected-answer-box mt-2">
                    <strong>الإجابة النموذجية المعتمدة:</strong>
                    <p dir={currentQuestion.questionType === 'equation_balancing' ? 'ltr' : 'rtl'}>
                      {currentQuestion.correctAnswer}
                    </p>
                  </div>
                )}

                <div className="explanation-body mt-2">
                  <strong>التفسير العلمي:</strong>
                  <p>{currentQuestion.explanation}</p>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* RESULTS STATE */}
      {gameState === 'results' && (
        <Card className="quiz-results-card text-center">
          <div className="trophy-icon">🏆</div>
          <h2>اكتمل الاختبار!</h2>
          <p className="mt-2 text-lg">لقد حصلت على نتيجة:</p>
          <div className="score-percentage-circle mt-4">
            <strong className="text-4xl">{Math.round((score / questions.length) * 100)}%</strong>
            <span className="text-sm block mt-1">{score} إجابات صحيحة من أصل {questions.length}</span>
          </div>

          <div className="score-comment mt-4">
            {score / questions.length >= 0.85 ? (
              <StatusPill tone="teal">ممتاز! مهاراتك الكيميائية استثنائية.</StatusPill>
            ) : score / questions.length >= 0.6 ? (
              <StatusPill tone="gold">أداء جيد! يمكنك مراجعة المصادر لرفع مستواك.</StatusPill>
            ) : (
              <StatusPill tone="coral">تحتاج للمزيد من التركيز. راجع درسك واعد المحاولة.</StatusPill>
            )}
          </div>

          <div className="results-actions mt-6 flex justify-center gap-4">
            <Button onClick={() => setGameState('setup')}>إعداد اختبار جديد</Button>
            <Link className="ed-btn ed-btn-secondary" to="/lessons">العودة لقائمة الدروس</Link>
          </div>

          <div className="quiz-review-list">
            {answerReviews.map((review, index) => (
              <article className={`quiz-review-item ${review.isCorrect ? 'correct' : 'wrong'}`} key={review.questionId}>
                <div>
                  <strong>{index + 1}. {review.question}</strong>
                  <span>{review.isCorrect ? 'صحيحة' : 'بحاجة مراجعة'}</span>
                </div>
                <p><b>إجابتك:</b> {review.userAnswer || 'لم يتم إدخال إجابة'}</p>
                <p><b>الإجابة المعتمدة:</b> {review.correctAnswer}</p>
                <small>{review.explanation}</small>
                <Link to={`/ask-ai?question=${encodeURIComponent(`اشرح لي هذا السؤال: ${review.question}`)}`}>اسأل AI عن هذا السؤال</Link>
              </article>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
