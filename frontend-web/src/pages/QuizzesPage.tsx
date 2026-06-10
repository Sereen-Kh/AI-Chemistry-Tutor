import { useState, useEffect, useMemo } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { mockLessons, getLessonQualityReport } from '../api/mockChemistryData';
import { quizzesApi } from '../api/quizzesApi';
import { Card, PageHeader, Button, ProgressBar, StatusPill, LoadingSkeleton, ErrorBanner } from '../components/DesignSystem';
import type { QuizGenerationConfig, GeneratedQuizQuestion, LessonKnowledgeUnit } from '../types';

export const QuizzesPage = () => {
  const location = useLocation();

  // Route/Query parameters parser
  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const paramLessonId = queryParams.get('lessonId');
  const paramAuto = queryParams.get('auto') === 'true';

  // Config UI State
  const [mode, setMode] = useState<QuizGenerationConfig['mode']>('single_lesson');
  const [selectedLessonIds, setSelectedLessonIds] = useState<string[]>([]);
  const [selectedChapterId, setSelectedChapterId] = useState<string>('chapter_1');
  const [questionsPerLesson, setQuestionsPerLesson] = useState<number>(3);
  const [difficulty, setDifficulty] = useState<QuizGenerationConfig['difficulty']>('mixed');
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

  // Prepopulate config if parameters exist
  useEffect(() => {
    if (paramLessonId) {
      setMode('single_lesson');
      setSelectedLessonIds([paramLessonId]);
    }
  }, [paramLessonId]);

  // Auto-generate if specified
  useEffect(() => {
    if (paramAuto && paramLessonId) {
      const qCount = Number(queryParams.get('questions') || '3');
      const qDiff = (queryParams.get('difficulty') || 'mixed') as QuizGenerationConfig['difficulty'];
      const qTypes = (queryParams.get('types') || 'mcq').split(',') as QuizGenerationConfig['questionTypes'];
      
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

      // Check quality before auto-generating
      const lesson = mockLessons.find(l => l.lessonId === paramLessonId);
      if (lesson) {
        const report = getLessonQualityReport(lesson);
        if (report.status !== 'blocked') {
          handleGenerateQuiz(config);
        } else {
          setError(`تعذر التوليد التلقائي: درس "${lesson.titleAr}" محظور بسبب جودة المحتوى.`);
        }
      }
    }
  }, [paramAuto, paramLessonId, queryParams]);

  // Compute selected lessons based on mode
  const currentSelectedLessons = useMemo<LessonKnowledgeUnit[]>(() => {
    if (mode === 'single_lesson') {
      return mockLessons.filter(l => selectedLessonIds.includes(l.lessonId));
    }
    if (mode === 'selected_lessons') {
      return mockLessons.filter(l => selectedLessonIds.includes(l.lessonId));
    }
    if (mode === 'chapter') {
      return mockLessons.filter(l => l.chapterId === selectedChapterId);
    }
    if (mode === 'weak_lessons') {
      return mockLessons.filter(l => l.qualityScore >= 60 && l.qualityScore < 80);
    }
    if (mode === 'study_plan' || mode === 'exam_review') {
      return mockLessons.filter(l => l.qualityScore >= 80).slice(0, 4); // Select a subset of ready lessons
    }
    return [];
  }, [mode, selectedLessonIds, selectedChapterId]);

  // Compute validation report for selected lessons
  const validationReport = useMemo(() => {
    const reports = currentSelectedLessons.map(getLessonQualityReport);
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
      lessonIds: currentSelectedLessons.map(l => l.lessonId),
      chapterIds: mode === 'chapter' ? [selectedChapterId] : undefined,
      questionsPerLesson,
      difficulty,
      questionTypes,
      includeSourcePage: true,
      requireExplanation: true,
      avoidDuplicateQuestions: true
    };

    if (config.lessonIds.length === 0) {
      setError('يرجى تحديد درس واحد على الأقل لتوليد الاختبار.');
      setGameState('setup');
      return;
    }

    // Double check blocking
    const selectedReports = mockLessons
      .filter(l => config.lessonIds.includes(l.lessonId))
      .map(getLessonQualityReport);
    
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
        setGameState('playing');
      }
    } catch {
      setError('حدث خطأ أثناء توليد الأسئلة.');
      setGameState('setup');
    }
  };

  const handleToggleLessonSelection = (lessonId: string) => {
    setSelectedLessonIds(prev => 
      prev.includes(lessonId) 
        ? prev.filter(id => id !== lessonId) 
        : [...prev, lessonId]
    );
  };

  const handleToggleType = (type: string) => {
    setQuestionTypes(prev => 
      prev.includes(type as any) 
        ? prev.filter(t => t !== type) as any
        : [...prev, type as any]
    );
  };

  const handleCheckAnswer = () => {
    if (submitted) return;

    const currentQ = questions[currentIndex];
    let correct = false;

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
    if (correct) {
      setScore(prev => prev + 1);
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
    if (isCorrect) {
      setScore(prev => prev + 1);
      setIsCurrentCorrect(true);
    } else {
      setIsCurrentCorrect(false);
    }
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

  return (
    <div className="page-stack quizzes-page">
      <PageHeader
        eyebrow="مدرّب الكيمياء"
        title="الاختبارات الذكية للدروس"
        subtitle="اختبارات مبنية على محتوى الدرس ونواتج التعلم، مع مراجعة شاملة للإجابات والتفسيرات."
      />

      {error && <ErrorBanner message={error} onRetry={() => setError('')} />}

      {/* SETUP GAME STATE */}
      {gameState === 'setup' && (
        <div className="quiz-setup-grid">
          {/* Config form */}
          <Card className="quiz-config-card">
            <div className="section-title">
              <h2>تكوين معايير الاختبار</h2>
            </div>

            <div className="form-group">
              <label>نمط توليد الاختبار:</label>
              <select value={mode} onChange={(e) => { setMode(e.target.value as any); setSelectedLessonIds([]); }}>
                <option value="single_lesson">درس واحد محدد</option>
                <option value="selected_lessons">مجموعة دروس محددة</option>
                <option value="chapter">وحدة كاملة (Chapter)</option>
                <option value="weak_lessons">دروس تحتاج لمراجعة (تحت 80%)</option>
                <option value="study_plan">خطة المذاكرة اليومية</option>
                <option value="exam_review">مراجعة الامتحان الشاملة</option>
              </select>
            </div>

            {/* Mode Specific Inputs */}
            {mode === 'single_lesson' && (
              <div className="form-group">
                <label>اختر الدرس:</label>
                <select 
                  value={selectedLessonIds[0] || ''} 
                  onChange={(e) => setSelectedLessonIds([e.target.value])}
                >
                  <option value="" disabled>-- اختر الدرس --</option>
                  {mockLessons.map(l => (
                    <option key={l.lessonId} value={l.lessonId}>{l.titleAr}</option>
                  ))}
                </select>
              </div>
            )}

            {mode === 'selected_lessons' && (
              <div className="form-group">
                <label>اختر الدروس المطلوبة:</label>
                <div className="lessons-checkbox-list">
                  {mockLessons.map(l => (
                    <label className="checkbox-item" key={l.lessonId}>
                      <input 
                        type="checkbox" 
                        checked={selectedLessonIds.includes(l.lessonId)} 
                        onChange={() => handleToggleLessonSelection(l.lessonId)} 
                      />
                      {l.titleAr}
                    </label>
                  ))}
                </div>
              </div>
            )}

            {mode === 'chapter' && (
              <div className="form-group">
                <label>اختر الوحدة الدراسية:</label>
                <select value={selectedChapterId} onChange={(e) => setSelectedChapterId(e.target.value)}>
                  <option value="chapter_1">الوحدة الأولى: المحاليل المائية</option>
                  <option value="chapter_2">الوحدة الثانية: المحاليل الحمضية</option>
                  <option value="chapter_3">الوحدة الثالثة: المحاليل الأساسية</option>
                  <option value="chapter_4">الوحدة الرابعة: أنواع التفاعلات الكيميائية</option>
                  <option value="chapter_5">الوحدة الخامسة: الأملاح</option>
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
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as any)}>
                  <option value="mixed">مختلط</option>
                  <option value="easy">سهل</option>
                  <option value="medium">متوسط</option>
                  <option value="hard">صعب</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>أنواع الأسئلة المرغوبة:</label>
              <div className="checkbox-grid">
                <label>
                  <input type="checkbox" checked={questionTypes.includes('mcq')} onChange={() => handleToggleType('mcq')} />
                  خيارات متعددة
                </label>
                <label>
                  <input type="checkbox" checked={questionTypes.includes('true_false')} onChange={() => handleToggleType('true_false')} />
                  صح أم خطأ
                </label>
                <label>
                  <input type="checkbox" checked={questionTypes.includes('short_answer')} onChange={() => handleToggleType('short_answer')} />
                  إجابات قصيرة
                </label>
                <label>
                  <input type="checkbox" checked={questionTypes.includes('calculation')} onChange={() => handleToggleType('calculation')} />
                  مسائل حسابية
                </label>
                <label>
                  <input type="checkbox" checked={questionTypes.includes('equation_balancing')} onChange={() => handleToggleType('equation_balancing')} />
                  موازنة معادلات
                </label>
              </div>
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
                    const l = mockLessons.find(m => m.lessonId === rep.lessonId);
                    return (
                      <div className={`status-lesson-item ${rep.status}`} key={rep.lessonId}>
                        <div className="flex justify-between items-center">
                          <strong>{l?.titleAr}</strong>
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
              <StatusPill tone="purple">النتيجة: {score}/{currentIndex}</StatusPill>
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
                    if (idx === currentQuestion.correctOptionIndex) classes += ' correct';
                    else if (selectedOptionIndex === idx) classes += ' wrong';
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
        </Card>
      )}
    </div>
  );
};
