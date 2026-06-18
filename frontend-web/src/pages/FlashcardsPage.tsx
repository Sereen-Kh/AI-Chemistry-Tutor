import { useState, useEffect, useMemo } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { flashcardsApi } from '../api/flashcardsApi';
import { Card, PageHeader, Button, ProgressBar, StatusPill, LoadingSkeleton, ErrorBanner } from '../components/DesignSystem';
import { getCurriculumLessonQuality, lessonPageRange, useActiveCurriculum } from '../hooks/useActiveCurriculum';
import type { FlashcardGenerationConfig, GeneratedFlashcard } from '../types';

type FlashcardMode = FlashcardGenerationConfig['mode'];
type FlashcardDifficulty = FlashcardGenerationConfig['difficulty'];
type FlashcardType = FlashcardGenerationConfig['cardTypes'][number];

export const FlashcardsPage = () => {
  const location = useLocation();

  // Route/Query parameters parser
  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const paramLessonId = queryParams.get('lessonId');
  const paramAuto = queryParams.get('auto') === 'true';

  // Config UI State
  const [mode, setMode] = useState<FlashcardMode>(paramLessonId ? 'single_lesson' : 'single_lesson');
  const [selectedLessonIds, setSelectedLessonIds] = useState<string[]>(paramLessonId ? [paramLessonId] : []);
  const [selectedChapterId, setSelectedChapterId] = useState<string>('');
  const [cardsPerLesson, setCardsPerLesson] = useState<number>(4);
  const [difficulty, setDifficulty] = useState<FlashcardDifficulty>('mixed');
  const [cardTypes, setCardTypes] = useState<FlashcardGenerationConfig['cardTypes']>(['term', 'definition', 'formula', 'experiment']);
  const [spacedRepetition, setSpacedRepetition] = useState(true);

  // Flow States
  const [gameState, setGameState] = useState<'setup' | 'generating' | 'preview' | 'studying' | 'completed'>('setup');
  const [cards, setQuestions] = useState<GeneratedFlashcard[]>([]);
  const [flipped, setFlipped] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState('');
  
  // Study Metrics
  const [knownCount, setKnownCount] = useState(0);
  const [reviewCount, setReviewCount] = useState(0);
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  // Filter States (studying mode)
  const [filterType, setFilterType] = useState<string>('all');
  const [filterDifficulty, setFilterDifficulty] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [showQualityReport, setShowQualityReport] = useState(false);

  const { allLessons, chapters, loading: curriculumLoading, usingFallback: usingFallbackCurriculum } = useActiveCurriculum();
  const effectiveSelectedChapterId = selectedChapterId || (chapters[0] ? String(chapters[0].id) : '');

  // Compute selected lessons
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
    if (mode === 'study_plan') {
      return allLessons.filter(l => l.difficulty <= 3).slice(0, 4);
    }
    return [];
  }, [mode, selectedLessonIds, effectiveSelectedChapterId, allLessons]);

  // Compute validation report
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

  const handleGenerateFlashcards = async (overrideConfig?: FlashcardGenerationConfig) => {
    setError('');
    setGameState('generating');

    const config: FlashcardGenerationConfig = overrideConfig || {
      mode,
      lessonIds: currentSelectedLessons.map(l => String(l.id)),
      cardsPerLesson,
      difficulty,
      cardTypes,
      includeSourcePage: true,
      spacedRepetitionEnabled: spacedRepetition
    };

    if (config.lessonIds.length === 0) {
      setError('يرجى تحديد درس واحد على الأقل لتوليد البطاقات.');
      setGameState('setup');
      return;
    }

    const selectedReports = allLessons
      .filter(l => config.lessonIds.includes(String(l.id)))
      .map(getCurriculumLessonQuality);
    
    if (selectedReports.some(r => r.status === 'blocked')) {
      setError('لا يمكن توليد البطاقات. أحد الدروس المحددة محظور بسبب نقص الجودة.');
      setGameState('setup');
      return;
    }

    try {
      const generated = await flashcardsApi.generateFlashcards(config);
      if (generated.length === 0) {
        setError('لم نتمكن من توليد أي بطاقات مع هذا التكوين. حاول تحديد أنواع أخرى أو بطاقات إضافية.');
        setGameState('setup');
      } else {
        setQuestions(generated);
        setGameState('preview');
      }
    } catch {
      setError('حدث خطأ أثناء توليد البطاقات الكيميائية.');
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

  const handleToggleCardType = (type: FlashcardType) => {
    setCardTypes(prev => 
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const handleStartStudying = () => {
    setCurrentIndex(0);
    setFlipped(false);
    setKnownCount(0);
    setReviewCount(0);
    setShowFilters(false);
    setGameState('studying');
  };

  const filteredCards = cards.filter(card => {
    if (filterType !== 'all' && card.cardType !== filterType) return false;
    if (filterDifficulty !== 'all' && card.difficulty !== filterDifficulty) return false;
    return true;
  });

  const activeCard = filteredCards[currentIndex];

  const handleCardAction = async (action: 'known' | 'review' | 'skip') => {
    const currentCard = filteredCards[currentIndex];
    
    if (action === 'known') {
      setKnownCount(prev => prev + 1);
      void flashcardsApi.updateFlashcardReviewState(currentCard.id, 'known');
    } else if (action === 'review') {
      setReviewCount(prev => prev + 1);
      void flashcardsApi.updateFlashcardReviewState(currentCard.id, 'review');
    }

    setFlipped(false);
    
    // Wait for flip transition back to front before changing card index
    setTimeout(() => {
      if (currentIndex + 1 < filteredCards.length) {
        setCurrentIndex(prev => prev + 1);
      } else {
        setGameState('completed');
      }
    }, 200);
  };

  useEffect(() => {
    if (!paramAuto || !paramLessonId) return;
    const cCount = Number(queryParams.get('cards') || '4');
    const cDiff = (queryParams.get('difficulty') || 'mixed') as FlashcardDifficulty;
    const cTypes = (queryParams.get('types') || 'term').split(',') as FlashcardType[];

    const config: FlashcardGenerationConfig = {
      mode: 'single_lesson',
      lessonIds: [paramLessonId],
      cardsPerLesson: cCount,
      difficulty: cDiff,
      cardTypes: cTypes,
      includeSourcePage: true,
      spacedRepetitionEnabled: true
    };

    const lesson = allLessons.find(l => String(l.id) === paramLessonId);
    if (!lesson) return;
    const report = getCurriculumLessonQuality(lesson);
    if (report.status !== 'blocked') {
      queueMicrotask(() => void handleGenerateFlashcards(config));
    } else {
      queueMicrotask(() => setError(`تعذر التوليد التلقائي للبطاقات: درس "${lesson.title_ar}" محظور بسبب جودة المحتوى.`));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramAuto, paramLessonId, queryParams, allLessons]);

  const getCardTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      term: 'مصطلح',
      definition: 'تعريف علمي',
      formula: 'معادلة / قانون',
      reaction: 'تفاعل كيميائي',
      comparison: 'مقارنة كيميائية',
      experiment: 'تجربة مخبرية',
      common_mistake: 'خطأ شائع'
    };
    return labels[type] || type;
  };

  const getCardTypeTone = (type: string) => {
    const tones: Record<string, string> = {
      term: 'blue',
      definition: 'teal',
      formula: 'purple',
      reaction: 'gold',
      comparison: 'coral',
      experiment: 'teal',
      common_mistake: 'coral'
    };
    return tones[type] || 'blue';
  };

  const handleFlashcardTouchEnd = (clientX: number) => {
    if (touchStartX === null || !activeCard) return;
    const delta = clientX - touchStartX;
    setTouchStartX(null);
    if (Math.abs(delta) < 70) return;
    void handleCardAction(delta < 0 ? 'known' : 'review');
  };

  return (
    <div className="page-stack flashcards-page">
      <PageHeader
        eyebrow="المراجعة الذكية"
        title="البطاقات التعليمية للكيمياء"
        subtitle="مراجعة المفاهيم، موازنة الصيغ، وتثبيت نواتج التعلم بالاعتماد على خوارزمية التكرار المتباعد."
      />

      {usingFallbackCurriculum && <ErrorBanner message="تعذر تحميل المنهج من الخادم، لذلك نعرض بنية الكتاب الاحتياطية مؤقتاً." />}
      {error && <ErrorBanner message={error} onRetry={() => setError('')} />}

      {/* SETUP CONFIG STATE */}
      {gameState === 'setup' && (
        <div className={`quiz-setup-grid ${showQualityReport ? 'has-report' : 'report-collapsed'}`}>
          <Card className="quiz-config-card">
            <div className="section-title">
              <h2>إعداد مجموعة المراجعة</h2>
              <Button variant="ghost" onClick={() => setShowQualityReport((open) => !open)} className="ed-btn-xs">
                {showQualityReport ? 'إخفاء تقرير الجودة' : 'عرض تقرير الجودة'}
              </Button>
            </div>

            <div className="form-group">
              <label>نمط توليد البطاقات:</label>
              <select value={mode} onChange={(e) => { setMode(e.target.value as FlashcardMode); setSelectedLessonIds([]); }}>
                <option value="single_lesson">درس واحد محدد</option>
                <option value="selected_lessons">مجموعة دروس محددة</option>
                <option value="chapter">فصل كامل من الوحدة</option>
                <option value="weak_lessons">الدروس ذات التحصيل الضعيف (تحت 80%)</option>
                <option value="study_plan">خطة المراجعة اليومية الموصى بها</option>
              </select>
            </div>

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
                          onClick={() => setSelectedLessonIds([lessonId])}
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
                <label>البطاقات لكل درس:</label>
                <input 
                  type="number" 
                  min={1} 
                  max={10} 
                  value={cardsPerLesson} 
                  onChange={(e) => setCardsPerLesson(Math.max(1, Number(e.target.value)))} 
                />
              </div>
              <div className="form-group">
                <label>الصعوبة المفضلة:</label>
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as FlashcardDifficulty)}>
                  <option value="mixed">مختلط</option>
                  <option value="easy">سهل</option>
                  <option value="medium">متوسط</option>
                  <option value="hard">صعب</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>أنواع البطاقات المطلوبة:</label>
              <div className="type-pill-row" aria-label="أنواع البطاقات">
                {[
                  { value: 'term' as const, label: 'مصطلحات', icon: 'T' },
                  { value: 'definition' as const, label: 'تعاريف', icon: 'D' },
                  { value: 'formula' as const, label: 'قوانين', icon: 'F' },
                  { value: 'experiment' as const, label: 'تجارب', icon: 'E' },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`type-pill ${cardTypes.includes(option.value) ? 'active' : ''}`}
                    onClick={() => handleToggleCardType(option.value)}
                    aria-pressed={cardTypes.includes(option.value)}
                  >
                    <span>{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input type="checkbox" checked={spacedRepetition} onChange={(e) => setSpacedRepetition(e.target.checked)} />
                تفعيل التكرار المتباعد (Spaced Repetition)
              </label>
            </div>

            <div className="setup-summary-bar">
              <strong>{currentSelectedLessons.length} دروس مختارة</strong>
              <span>{Math.max(1, currentSelectedLessons.length) * cardsPerLesson} بطاقة متوقعة</span>
              <span>{spacedRepetition ? 'تكرار متباعد مفعل' : 'تكرار متباعد معطل'}</span>
            </div>

            <Button 
              onClick={() => handleGenerateFlashcards()} 
              disabled={validationReport.isBlocked || currentSelectedLessons.length === 0 || cardTypes.length === 0}
              className="w-full mt-4"
            >
              توليد البطاقات للمراجعة
            </Button>
          </Card>

          {/* Quality reports for verification */}
          {showQualityReport && (
          <Card className="quiz-quality-report-sidebar">
            <div className="section-title">
              <h2>تقرير جودة دروس البطاقات</h2>
            </div>
            {currentSelectedLessons.length === 0 ? (
              <p className="no-data-text text-sm">اختر درساً لرؤية تقرير سلامة جودة المحتوى.</p>
            ) : (
              <div className="quiz-lessons-status-report">
                <p className="text-sm mb-3">الدروس المختارة للتوليد ({currentSelectedLessons.length}):</p>
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
                            <strong>عناصر الجودة الناقصة:</strong>
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
                    <p className="text-sm">⚠ يحتوي التحديد الحالي على دروس <strong>مغلقة الجودة</strong>. يرجى تعديل الاختيارات ليتم توليد البطاقات بنجاح.</p>
                  </div>
                )}
              </div>
            )}
          </Card>
          )}
        </div>
      )}

      {/* GENERATING FLASHCARDS LOADER */}
      {gameState === 'generating' && (
        <Card className="quiz-generating-loader text-center">
          <LoadingSkeleton rows={4} />
          <p className="mt-4 text-lg">جاري مسح محتوى الدروس وتوليد بطاقات المراجعة من RAG ...</p>
        </Card>
      )}

      {/* PREVIEW FLASHCARDS BEFORE SAVING */}
      {gameState === 'preview' && (
        <Card className="flashcards-preview-panel">
          <div className="section-title">
            <h2>معاينة البطاقات المولدة ({cards.length} بطاقة)</h2>
            <StatusPill tone="teal">مسودة RAG جاهزة</StatusPill>
          </div>
          <p className="text-sm mb-4">راجع قائمة البطاقات المولدة وتأكد من ملائمتها قبل حفظها في ذاكرتك الكيميائية:</p>

          <div className="pre-generated-list">
            {cards.map((card, idx) => (
              <div className="pre-generated-card-item" key={card.id}>
                <div>
                  <span className="text-xs opacity-60 ml-2">[{idx + 1}]</span>
                  <strong>{card.front}</strong>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill tone={getCardTypeTone(card.cardType)}>{getCardTypeLabel(card.cardType)}</StatusPill>
                  <span className="text-xs opacity-50">صفحة {card.sourcePage}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="results-actions mt-6 flex justify-center gap-4">
            <Button onClick={handleStartStudying}>حفظ والبدء في الدراسة والتثبيت</Button>
            <Button variant="secondary" onClick={() => setGameState('setup')}>تعديل التكوين</Button>
          </div>
        </Card>
      )}

      {/* ACTIVE STUDY BOARD WITH 3D FLIP */}
      {gameState === 'studying' && activeCard && (
        <div className={`study-layout ${showFilters ? 'filters-open' : 'filters-collapsed'}`}>
          {/* Centered large 3D flip card */}
          <div className="study-card-player flex-grow">
            <div className="study-review-toolbar">
              <div>
                <strong>مراجعة البطاقات</strong>
                <span>{filteredCards.length} بطاقة ظاهرة · {knownCount} متقنة · {reviewCount} للمراجعة</span>
              </div>
              <div className="study-review-toolbar-actions">
                <Button variant="ghost" onClick={() => setShowFilters((open) => !open)}>
                  {showFilters ? 'إخفاء التصفية' : 'تصفية البطاقات'}
                </Button>
                <Button variant="ghost" onClick={() => setGameState('setup')}>إيقاف المراجعة</Button>
              </div>
            </div>

            {filteredCards.length === 0 ? (
            <Card className="text-center w-full flex-grow">
              <p className="no-data-text">لا توجد بطاقات مطابقة لخيارات التصفية الحالية.</p>
              <Button variant="secondary" onClick={() => { setFilterType('all'); setFilterDifficulty('all'); }} className="mt-4">إزالة التصفية</Button>
            </Card>
          ) : (
            <>
              <Card className="quiz-progress-card mb-4">
                <div className="player-progress-header text-sm">
                  <span>البطاقة <strong>{currentIndex + 1}</strong> من <strong>{filteredCards.length}</strong></span>
                  <StatusPill tone="blue">تكرار متباعد: {spacedRepetition ? 'مفعل' : 'معطل'}</StatusPill>
                </div>
                <ProgressBar value={Math.round(((currentIndex + 1) / filteredCards.length) * 100)} tone="teal" />
              </Card>

              {/* 3D Flashcard Stage */}
              <div className="flashcard-stage mt-6">
                <div
                  className="flashcard-wrapper"
                  onClick={() => setFlipped(!flipped)}
                  onTouchStart={(event) => setTouchStartX(event.changedTouches[0]?.clientX ?? null)}
                  onTouchEnd={(event) => handleFlashcardTouchEnd(event.changedTouches[0]?.clientX ?? 0)}
                >
                  <div className={`flashcard-inner ${flipped ? 'is-flipped' : ''}`}>
                    
                    {/* FRONT SIDE */}
                    <div className="flashcard-front">
                      <div className="card-header-badge-row">
                        <StatusPill tone={getCardTypeTone(activeCard.cardType)}>{getCardTypeLabel(activeCard.cardType)}</StatusPill>
                        <StatusPill tone="gold">صعوبة: {activeCard.difficulty === 'easy' ? 'سهل' : activeCard.difficulty === 'medium' ? 'متوسط' : 'صعب'}</StatusPill>
                      </div>

                      <div className="card-body-text">
                        {activeCard.front}
                      </div>

                      <div className="card-footer-info">
                        <span>انقر على البطاقة لرؤية الإجابة</span>
                        <span>بطاقة رقم {currentIndex + 1}</span>
                      </div>
                    </div>

                    {/* BACK SIDE */}
                    <div className="flashcard-back">
                      <div className="card-header-badge-row">
                        <StatusPill tone="teal">الإجابة الصحيحة</StatusPill>
                        <StatusPill tone="blue">صفحة المصدر: {activeCard.sourcePage}</StatusPill>
                      </div>

                      <div className="card-body-text whitespace-pre-line" dir={activeCard.cardType === 'formula' || activeCard.cardType === 'reaction' ? 'ltr' : 'rtl'}>
                        {activeCard.back}
                      </div>

                      <div className="card-footer-info">
                        <span>انقر للعودة للسؤال</span>
                        <span>كتاب الكيمياء - التاسع الأساسي</span>
                      </div>
                    </div>

                  </div>
                </div>

                {/* STUDY ACTIONS PANEL */}
                <div className="study-actions-row mt-8 flex justify-center gap-4">
                  <Button variant="secondary" onClick={() => handleCardAction('review')} className="ed-btn-danger">
                    مراجعة لاحقاً 🔁
                  </Button>
                  <Button variant="ghost" onClick={() => handleCardAction('skip')}>
                    تخطي البطاقة ↷
                  </Button>
                  <Button onClick={() => handleCardAction('known')} className="ed-btn-primary">
                    أعرفها تماماً ✓
                  </Button>
                </div>
              </div>
            </>
          )}
          </div>

          {showFilters && (
          <Card className="study-filters-panel">
            <h3>تصفية البطاقات الحالية</h3>

            <div className="form-group mt-4">
              <label>تصفية حسب النوع:</label>
              <select value={filterType} onChange={(e) => { setFilterType(e.target.value); setCurrentIndex(0); }}>
                <option value="all">كل الأنواع</option>
                <option value="term">المصطلحات</option>
                <option value="definition">التعاريف</option>
                <option value="formula">المعادلات والقوانين</option>
                <option value="experiment">التجارب والخلاصات</option>
              </select>
            </div>

            <div className="form-group">
              <label>تصفية حسب الصعوبة:</label>
              <select value={filterDifficulty} onChange={(e) => { setFilterDifficulty(e.target.value); setCurrentIndex(0); }}>
                <option value="all">كل الصعوبات</option>
                <option value="easy">سهل</option>
                <option value="medium">متوسط</option>
                <option value="hard">صعب</option>
              </select>
            </div>

            <div className="study-session-info mt-6 text-xs text-right opacity-85">
              <div className="font-semibold mb-2">إحصاءات الجلسة:</div>
              <div>بطاقات معروفة: {knownCount}</div>
              <div>بطاقات تحتاج مراجعة: {reviewCount}</div>
              <div>إجمالي ما تمت تصفيته: {filteredCards.length} بطاقة</div>
            </div>
          </Card>
          )}
        </div>
      )}

      {/* COMPLETED DECK RESULTS SCREEN */}
      {gameState === 'completed' && (
        <Card className="quiz-results-card text-center max-w-xl mx-auto mt-8">
          <div className="trophy-icon text-5xl">🎉</div>
          <h2>نهارك سعيد! اكتملت مراجعة البطاقات</h2>
          <p className="mt-2 text-lg">لقد أكملت بنجاح مراجعة <strong>{cards.length}</strong> بطاقة كيميائية.</p>
          
          <div className="stats-row inline mt-6 w-full max-w-md mx-auto">
            <article className="stat-tile">
              <strong>{knownCount}</strong>
              <span>بطاقات متقنة ✓</span>
            </article>
            <article className="stat-tile">
              <strong>{reviewCount}</strong>
              <span>تحتاج لمراجعة 🔁</span>
            </article>
          </div>

          <div className="results-actions mt-8 flex justify-center gap-4">
            <Button onClick={() => setGameState('setup')}>مراجعة مجموعة أخرى</Button>
            <Link className="ed-btn ed-btn-secondary" to="/lessons">العودة للدروس</Link>
          </div>
        </Card>
      )}
    </div>
  );
};
