import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { flashcardsApi } from '../api/flashcardsApi';
import { Button, Card, ErrorBanner, LoadingSkeleton, PageHeader, ProgressBar, StatusPill } from '../components/DesignSystem';
import { lessonPageRange, useActiveCurriculum } from '../hooks/useActiveCurriculum';
import type {
  FlashcardCardType,
  FlashcardDeck,
  FlashcardGenerationConfig,
  FlashcardProgressSummary,
  FlashcardRating,
  GeneratedFlashcard,
} from '../types';

type FlashcardsViewState =
  | 'loading'
  | 'empty'
  | 'setup'
  | 'generating'
  | 'deck_list'
  | 'review_session'
  | 'deck_detail'
  | 'error';

type SetupScope = 'lesson' | 'selected_lessons' | 'unit' | 'weak_topics' | 'study_plan';

const cardTypeOptions: Array<{ value: FlashcardCardType; label: string; purpose: string; tone: string }> = [
  { value: 'term_definition', label: 'مصطلح', purpose: 'تعريف المصطلحات العلمية', tone: 'blue' },
  { value: 'concept_explanation', label: 'مفهوم', purpose: 'شرح فكرة كيميائية', tone: 'teal' },
  { value: 'equation_law', label: 'قانون / معادلة', purpose: 'تثبيت القوانين والعلاقات', tone: 'purple' },
  { value: 'calculation', label: 'مسألة حسابية', purpose: 'تطبيق خطوات الحل', tone: 'gold' },
  { value: 'experiment_result', label: 'تجربة واستنتاج', purpose: 'ربط التجربة بالاستنتاج', tone: 'teal' },
  { value: 'compare_contrast', label: 'مقارنة', purpose: 'تمييز المفاهيم المتشابهة', tone: 'coral' },
  { value: 'reaction_balancing', label: 'موازنة معادلات', purpose: 'ممارسة توازن التفاعلات', tone: 'gold' },
  { value: 'safety_rule', label: 'قاعدة أمان', purpose: 'تذكر قواعد المختبر', tone: 'slate' },
  { value: 'image_based', label: 'بطاقة صورة', purpose: 'قراءة الأشكال والجداول', tone: 'cyan' },
];

const ratingOptions: Array<{ value: FlashcardRating; label: string; helper: string; tone: string }> = [
  { value: 'again', label: 'لم أتذكرها', helper: 'إعادة قريبة', tone: 'coral' },
  { value: 'hard', label: 'صعبة', helper: 'فاصل قصير', tone: 'gold' },
  { value: 'good', label: 'جيدة', helper: 'فاصل عادي', tone: 'blue' },
  { value: 'easy', label: 'سهلة', helper: 'فاصل أطول', tone: 'teal' },
];

const emptyProgress: FlashcardProgressSummary = {
  totalCards: 0,
  dueToday: 0,
  newCards: 0,
  learningCards: 0,
  masteredCards: 0,
  overdueCards: 0,
  masteryPercent: 0,
};

const typeLabel = (type: string) => cardTypeOptions.find((option) => option.value === type)?.label || type;

const typeTone = (type: string) => cardTypeOptions.find((option) => option.value === type)?.tone || 'blue';

const ratingFeedback: Record<FlashcardRating, string> = {
  again: 'لا بأس، سنراجعها قريباً مرة أخرى.',
  hard: 'سأعيدها لك بعد وقت قصير.',
  good: 'جيد، ستظهر لاحقاً حسب التكرار المتباعد.',
  easy: 'ممتاز، سنؤجلها لمدة أطول.',
};

const extractBackendDetail = (error: unknown): { status?: number; detail: string } => {
  const maybeResponse = error as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
  const detail = maybeResponse.response?.data?.detail;
  if (typeof detail === 'string') return { status: maybeResponse.response?.status, detail };
  if (Array.isArray(detail)) {
    return {
      status: maybeResponse.response?.status,
      detail: detail.map((item) => {
        if (typeof item === 'string') return item;
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg);
        return '';
      }).filter(Boolean).join(' '),
    };
  }
  return { status: maybeResponse.response?.status, detail: maybeResponse.message || '' };
};

const normalizeError = (error: unknown): string => {
  const { status, detail } = extractBackendDetail(error);
  if (status === 401 || /unauthorized|forbidden|token/i.test(detail)) {
    return 'يجب تسجيل الدخول لإنشاء بطاقات.';
  }
  if (/field required|required|lesson_ids|اختر درس/i.test(detail)) return 'اختر درساً واحداً على الأقل.';
  if (status === 404 || /not found|لم يتم العثور/i.test(detail)) return 'تعذر تحميل بيانات الدرس.';
  if (/content|chunk|لا يوجد محتوى|غير كاف/i.test(detail)) return 'لا يوجد محتوى كافٍ لهذا الدرس.';
  if (/timeout|server|503|unavailable/i.test(detail)) return 'تعذر توليد البطاقات من الخادم حالياً.';
  return detail && !/field required/i.test(detail) ? detail : 'تعذر توليد البطاقات من الخادم حالياً.';
};

const sourcePages = (card: GeneratedFlashcard) => {
  if (!card.sourcePage) return 'صفحات غير محددة';
  if (card.sourcePageEnd && card.sourcePageEnd !== card.sourcePage) return `صفحات ${card.sourcePage} - ${card.sourcePageEnd}`;
  return `صفحة ${card.sourcePage}`;
};

const buildConfig = ({
  scope,
  selectedLessonIds,
  selectedTopicIds,
  selectedUnitId,
  cardsPerLesson,
  difficulty,
  cardTypes,
}: {
  scope: SetupScope;
  selectedLessonIds: string[];
  selectedTopicIds: string[];
  selectedUnitId: string;
  cardsPerLesson: number;
  difficulty: FlashcardGenerationConfig['difficulty'];
  cardTypes: FlashcardCardType[];
}): FlashcardGenerationConfig => ({
  mode: scope === 'unit'
    ? 'chapter'
    : scope === 'study_plan'
      ? 'study_plan'
      : scope === 'weak_topics'
        ? 'weak_lessons'
        : scope === 'selected_lessons'
          ? 'selected_lessons'
          : 'single_lesson',
  lessonIds: selectedLessonIds,
  topicIds: selectedTopicIds,
  unitIds: selectedUnitId ? [selectedUnitId] : [],
  cardsPerLesson,
  difficulty,
  cardTypes,
  includeSourcePage: true,
  spacedRepetitionEnabled: true,
});

export const FlashcardsPage = () => {
  const location = useLocation();
  const query = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const queryLessonId = query.get('lessonId') || query.get('lesson_id') || '';
  const queryScope = query.get('scope');
  const queryAuto = query.get('auto') === 'true';
  const querySource = query.get('source') || query.get('mode') || '';

  const { units, allLessons, loading: curriculumLoading, usingFallback: usingFallbackCurriculum } = useActiveCurriculum();
  const autoGenerationStartedRef = useRef(false);

  const [viewState, setViewState] = useState<FlashcardsViewState>('loading');
  const [decks, setDecks] = useState<FlashcardDeck[]>([]);
  const [progress, setProgress] = useState<FlashcardProgressSummary>(emptyProgress);
  const [activeDeck, setActiveDeck] = useState<(FlashcardDeck & { generatedCards?: GeneratedFlashcard[] }) | null>(null);
  const [reviewCards, setReviewCards] = useState<GeneratedFlashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [hintVisible, setHintVisible] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState('');
  const [ratingPending, setRatingPending] = useState(false);
  const [error, setError] = useState('');

  const [scope, setScope] = useState<SetupScope>(
    queryScope === 'study_plan' || querySource === 'study_plan' ? 'study_plan' : queryLessonId ? 'lesson' : 'lesson',
  );
  const [selectedLessonIds, setSelectedLessonIds] = useState<string[]>(queryLessonId ? [queryLessonId] : []);
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([]);
  const [selectedUnitId, setSelectedUnitId] = useState<string>('');
  const [cardsPerLesson, setCardsPerLesson] = useState(4);
  const [difficulty, setDifficulty] = useState<FlashcardGenerationConfig['difficulty']>('mixed');
  const [cardTypes, setCardTypes] = useState<FlashcardCardType[]>([
    'term_definition',
    'concept_explanation',
    'equation_law',
    'calculation',
  ]);
  const [formErrors, setFormErrors] = useState<string[]>([]);

  const selectedLessons = useMemo(() => {
    if (scope === 'unit' && selectedUnitId) {
      return allLessons.filter((lesson) => String(lesson.unit.id) === selectedUnitId);
    }
    if (scope === 'weak_topics') {
      return allLessons.filter((lesson) => lesson.difficulty >= 3).slice(0, 6);
    }
    if (scope === 'study_plan') {
      return allLessons.slice(0, 4);
    }
    return allLessons.filter((lesson) => selectedLessonIds.includes(String(lesson.id)));
  }, [allLessons, scope, selectedLessonIds, selectedUnitId]);

  const activeCard = reviewCards[currentIndex];

  const loadFlashcards = async (preferredState?: FlashcardsViewState) => {
    setViewState('loading');
    setError('');
    try {
      const [loadedDecks, loadedProgress] = await Promise.all([
        flashcardsApi.getDecks(),
        flashcardsApi.getProgress(),
      ]);
      setDecks(loadedDecks);
      setProgress(loadedProgress);
      if (preferredState) {
        setViewState(preferredState);
      } else if (queryLessonId || queryScope || queryAuto) {
        setViewState('setup');
      } else if (loadedDecks.length === 0 || loadedProgress.totalCards === 0) {
        setViewState('empty');
      } else {
        setViewState('deck_list');
      }
    } catch (err) {
      setError(normalizeError(err));
      setViewState('error');
    }
  };

  useEffect(() => {
    void loadFlashcards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryLessonId, queryScope, queryAuto]);

  const validateSetup = () => {
    const errors: string[] = [];
    const lessonCount = selectedLessons.length;
    if (lessonCount === 0) errors.push('اختر درساً واحداً على الأقل');
    if (cardTypes.length === 0) errors.push('اختر نوع بطاقة واحداً على الأقل');
    if (!Number.isFinite(cardsPerLesson) || cardsPerLesson < 1) errors.push('عدد البطاقات غير صالح');
    if (!difficulty) errors.push('اختر مستوى الصعوبة');
    setFormErrors(errors);
    return errors.length === 0;
  };

  const resetReviewDisplay = () => {
    setRevealed(false);
    setHintVisible(false);
    setDetailsOpen(false);
    setReviewFeedback('');
    setRatingPending(false);
  };

  const generateDeckForLessons = async (lessonsToGenerate: typeof selectedLessons, requestedScope: SetupScope = scope) => {
    setError('');
    setViewState('generating');
    try {
      const generated = await flashcardsApi.generateDeck(buildConfig({
        scope: requestedScope,
        selectedLessonIds: lessonsToGenerate.map((lesson) => String(lesson.id)),
        selectedTopicIds,
        selectedUnitId,
        cardsPerLesson,
        difficulty,
        cardTypes,
      }));
      setActiveDeck(generated);
      setReviewCards(generated.generatedCards || []);
      setCurrentIndex(0);
      resetReviewDisplay();
      await loadFlashcards('deck_detail');
      setActiveDeck(generated);
      setReviewCards(generated.generatedCards || []);
    } catch (err) {
      setError(normalizeError(err));
      setViewState('setup');
    }
  };

  const generateDeck = async () => {
    if (!validateSetup()) return;
    await generateDeckForLessons(selectedLessons);
  };

  useEffect(() => {
    if (!queryAuto) return;
    if (autoGenerationStartedRef.current) return;
    if (!queryLessonId) {
      setError('لا يوجد درس محدد لتوليد المراجعة.');
      setViewState('setup');
      return;
    }
    if (curriculumLoading) return;
    const lesson = allLessons.find((item) => String(item.id) === String(queryLessonId));
    if (!lesson) {
      setError('تعذر تحميل بيانات الدرس.');
      setViewState('setup');
      return;
    }
    autoGenerationStartedRef.current = true;
    setScope(querySource === 'study_plan' ? 'study_plan' : 'lesson');
    setSelectedLessonIds([String(lesson.id)]);
    queueMicrotask(() => void generateDeckForLessons([lesson], querySource === 'study_plan' ? 'study_plan' : 'lesson'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryAuto, queryLessonId, querySource, curriculumLoading, allLessons]);

  const openDeck = async (deckId: string | number) => {
    setViewState('loading');
    setError('');
    try {
      const deck = await flashcardsApi.getDeck(deckId);
      setActiveDeck(deck);
      setReviewCards(deck.generatedCards || []);
      setCurrentIndex(0);
      resetReviewDisplay();
      setViewState('deck_detail');
    } catch (err) {
      setError(normalizeError(err));
      setViewState('deck_list');
    }
  };

  const startReview = async (deckId?: string | number) => {
    setViewState('loading');
    setError('');
    try {
      const session = await flashcardsApi.createReviewSession(deckId, 30);
      let cards = session.cards;
      if (cards.length === 0 && deckId) {
        const deck = await flashcardsApi.getDeck(deckId);
        cards = deck.generatedCards || [];
        setActiveDeck(deck);
      }
      if (cards.length === 0) {
        setError('لا توجد بطاقات مستحقة الآن. يمكنك إنشاء بطاقات جديدة أو فتح مجموعة للمراجعة الحرة.');
        setViewState(decks.length ? 'deck_list' : 'empty');
        return;
      }
      setReviewCards(cards);
      setCurrentIndex(0);
      resetReviewDisplay();
      setViewState('review_session');
    } catch (err) {
      setError(normalizeError(err));
      setViewState('deck_list');
    }
  };

  const rateCard = async (rating: FlashcardRating) => {
    if (!activeCard || ratingPending) return;
    setRatingPending(true);
    try {
      const review = await flashcardsApi.reviewFlashcard(activeCard.id, rating);
      setReviewCards((cards) => cards.map((card) => (
        card.id === activeCard.id
          ? {
              ...card,
              reviewState: review.status === 'mastered' ? 'mastered' : review.status,
              dueAt: review.new_due_at,
              nextReviewAt: review.new_due_at || undefined,
              intervalDays: review.interval_days,
              easeFactor: review.ease_factor,
              repetitions: review.repetitions,
              lapses: review.lapses,
            }
          : card
      )));
      setReviewFeedback(ratingFeedback[rating]);
      window.setTimeout(() => {
        resetReviewDisplay();
        if (currentIndex + 1 < reviewCards.length) {
          setCurrentIndex((index) => index + 1);
        } else {
          void loadFlashcards('deck_list');
        }
      }, 900);
    } catch {
      setError('تعذر حفظ تقييم البطاقة. حاول مرة أخرى.');
      setRatingPending(false);
    }
  };

  const toggleLesson = (lessonId: string) => {
    setSelectedLessonIds((current) => (
      current.includes(lessonId)
        ? current.filter((id) => id !== lessonId)
        : scope === 'lesson'
          ? [lessonId]
          : [...current, lessonId]
    ));
  };

  const toggleTopic = (topicId: string) => {
    setSelectedTopicIds((current) => (
      current.includes(topicId) ? current.filter((id) => id !== topicId) : [...current, topicId]
    ));
  };

  const toggleCardType = (type: FlashcardCardType) => {
    setCardTypes((current) => (
      current.includes(type) ? current.filter((item) => item !== type) : [...current, type]
    ));
  };

  return (
    <div className="page-stack flashcards-page flashcards-v2">
      <PageHeader
        eyebrow="المراجعة الذكية"
        title="البطاقات التعليمية"
        subtitle="بطاقات مرتبطة بالكتاب والدروس والموضوعات، مع وصف ومصدر وجدولة مراجعة متباعدة."
        action={
          <div className="flashcards-header-actions">
            <Button variant="secondary" onClick={() => setViewState('setup')}>إنشاء بطاقات</Button>
            <Button onClick={() => void startReview()}>ابدأ المراجعة</Button>
          </div>
        }
      />

      {usingFallbackCurriculum && <ErrorBanner message="تعذر تحميل المنهج من الخادم، لذلك نعرض بنية الكتاب الاحتياطية مؤقتاً." />}
      {error && <ErrorBanner message={error} onRetry={() => setError('')} />}

      {viewState === 'loading' && <FlashcardSkeleton />}
      {viewState === 'error' && (
        <FlashcardError onRetry={() => void loadFlashcards()} />
      )}
      {viewState === 'empty' && (
        <FlashcardsEmptyState onCreate={() => setViewState('setup')} />
      )}
      {viewState === 'setup' && (
        <FlashcardDeckSetup
          units={units}
          curriculumLoading={curriculumLoading}
          scope={scope}
          setScope={setScope}
          selectedLessonIds={selectedLessonIds}
          selectedTopicIds={selectedTopicIds}
          selectedUnitId={selectedUnitId}
          setSelectedUnitId={setSelectedUnitId}
          toggleLesson={toggleLesson}
          toggleTopic={toggleTopic}
          cardsPerLesson={cardsPerLesson}
          setCardsPerLesson={setCardsPerLesson}
          difficulty={difficulty}
          setDifficulty={setDifficulty}
          cardTypes={cardTypes}
          toggleCardType={toggleCardType}
          selectedLessonsCount={selectedLessons.length}
          formErrors={formErrors}
          onGenerate={() => void generateDeck()}
          onCancel={() => setViewState(decks.length ? 'deck_list' : 'empty')}
        />
      )}
      {viewState === 'generating' && <FlashcardGenerationOverlay />}
      {viewState === 'deck_list' && (
        <FlashcardDeckList
          progress={progress}
          decks={decks}
          onCreate={() => setViewState('setup')}
          onReview={() => void startReview()}
          onOpenDeck={(deckId) => void openDeck(deckId)}
        />
      )}
      {viewState === 'deck_detail' && activeDeck && (
        <FlashcardDeckDetail
          deck={activeDeck}
          cards={reviewCards}
          onBack={() => setViewState('deck_list')}
          onReview={() => void startReview(activeDeck.id)}
        />
      )}
      {viewState === 'review_session' && activeCard && (
        <FlashcardReviewSession
          card={activeCard}
          deck={activeDeck}
          index={currentIndex}
          total={reviewCards.length}
          revealed={revealed}
          hintVisible={hintVisible}
          detailsOpen={detailsOpen}
          reviewFeedback={reviewFeedback}
          ratingPending={ratingPending}
          onShowHint={() => setHintVisible(true)}
          setDetailsOpen={setDetailsOpen}
          onReveal={() => setRevealed(true)}
          onRate={(rating) => void rateCard(rating)}
          onExit={() => setViewState('deck_list')}
        />
      )}
    </div>
  );
};

const FlashcardSkeleton = () => (
  <Card className="flashcards-skeleton">
    <LoadingSkeleton rows={6} />
  </Card>
);

const FlashcardError = ({ onRetry }: { onRetry: () => void }) => (
  <Card className="flashcards-empty-state">
    <p className="eyebrow">تعذر التحميل</p>
    <h2>لم نتمكن من تحميل البطاقات</h2>
    <p>تحقق من اتصال الخادم ثم أعد المحاولة.</p>
    <Button onClick={onRetry}>إعادة المحاولة</Button>
  </Card>
);

const FlashcardsEmptyState = ({ onCreate }: { onCreate: () => void }) => (
  <Card className="flashcards-empty-state">
    <div>
      <p className="eyebrow">لا توجد مجموعات بعد</p>
      <h2>ابدأ ببناء ذاكرة كيميائية من الكتاب</h2>
      <p>
        أنشئ بطاقات من درس أو موضوع محدد. كل بطاقة ستعرض السؤال والإجابة والوصف والصفحات المصدرية،
        ثم يحدد التكرار المتباعد موعد المراجعة التالية.
      </p>
      <div className="flashcards-benefits">
        <span>مرتبطة بالدرس والموضوع</span>
        <span>مصادر من الكتاب</span>
        <span>وصف لكل بطاقة</span>
        <span>مراجعة متباعدة</span>
      </div>
    </div>
    <Button onClick={onCreate}>إنشاء بطاقات</Button>
  </Card>
);

const FlashcardDeckSetup = ({
  units,
  curriculumLoading,
  scope,
  setScope,
  selectedLessonIds,
  selectedTopicIds,
  selectedUnitId,
  setSelectedUnitId,
  toggleLesson,
  toggleTopic,
  cardsPerLesson,
  setCardsPerLesson,
  difficulty,
  setDifficulty,
  cardTypes,
  toggleCardType,
  selectedLessonsCount,
  formErrors,
  onGenerate,
  onCancel,
}: {
  units: ReturnType<typeof useActiveCurriculum>['units'];
  curriculumLoading: boolean;
  scope: SetupScope;
  setScope: (scope: SetupScope) => void;
  selectedLessonIds: string[];
  selectedTopicIds: string[];
  selectedUnitId: string;
  setSelectedUnitId: (value: string) => void;
  toggleLesson: (lessonId: string) => void;
  toggleTopic: (topicId: string) => void;
  cardsPerLesson: number;
  setCardsPerLesson: (value: number) => void;
  difficulty: FlashcardGenerationConfig['difficulty'];
  setDifficulty: (value: FlashcardGenerationConfig['difficulty']) => void;
  cardTypes: FlashcardCardType[];
  toggleCardType: (type: FlashcardCardType) => void;
  selectedLessonsCount: number;
  formErrors: string[];
  onGenerate: () => void;
  onCancel: () => void;
}) => (
  <div className="flashcards-setup-grid">
    <Card className="flashcards-setup-card">
      <div className="section-title">
        <h2>إعداد مجموعة بطاقات</h2>
        <StatusPill tone="teal">منهج → وحدة → فصل → درس → موضوع</StatusPill>
      </div>

      <div className="flashcards-scope-grid" role="radiogroup" aria-label="نطاق البطاقات">
        {[
          { value: 'lesson' as const, label: 'درس واحد' },
          { value: 'selected_lessons' as const, label: 'عدة دروس' },
          { value: 'unit' as const, label: 'وحدة كاملة' },
          { value: 'weak_topics' as const, label: 'نقاط الضعف فقط' },
          { value: 'study_plan' as const, label: 'خطة الدراسة' },
        ].map((option) => (
          <button
            key={option.value}
            type="button"
            className={scope === option.value ? 'is-active' : ''}
            onClick={() => setScope(option.value)}
            role="radio"
            aria-checked={scope === option.value}
          >
            {option.label}
          </button>
        ))}
      </div>

      {curriculumLoading ? (
        <LoadingSkeleton rows={5} />
      ) : (
        <LessonSelector
          units={units}
          scope={scope}
          selectedLessonIds={selectedLessonIds}
          selectedTopicIds={selectedTopicIds}
          selectedUnitId={selectedUnitId}
          setSelectedUnitId={setSelectedUnitId}
          toggleLesson={toggleLesson}
          toggleTopic={toggleTopic}
        />
      )}
    </Card>

    <aside className="flashcards-setup-side">
      <Card>
        <h3>إعدادات التوليد</h3>
        <label className="form-group">
          <span>البطاقات لكل درس</span>
          <input
            type="number"
            min={1}
            max={20}
            value={cardsPerLesson}
            onChange={(event) => setCardsPerLesson(Math.max(1, Number(event.target.value)))}
          />
        </label>
        <label className="form-group">
          <span>الصعوبة</span>
          <select value={difficulty} onChange={(event) => setDifficulty(event.target.value as FlashcardGenerationConfig['difficulty'])}>
            <option value="mixed">مختلط</option>
            <option value="easy">سهل</option>
            <option value="medium">متوسط</option>
            <option value="hard">صعب</option>
          </select>
        </label>

        <div className="form-group">
          <span>أنواع البطاقات</span>
          <div className="flashcard-type-grid">
            {cardTypeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                className={cardTypes.includes(option.value) ? 'is-active' : ''}
                onClick={() => toggleCardType(option.value)}
                aria-pressed={cardTypes.includes(option.value)}
              >
                <strong>{option.label}</strong>
                <small>{option.purpose}</small>
              </button>
            ))}
          </div>
        </div>

        {formErrors.length > 0 && (
          <div className="flashcards-form-errors" role="alert">
            {formErrors.map((item) => <span key={item}>{item}</span>)}
          </div>
        )}

        <div className="flashcards-setup-summary">
          <strong>{selectedLessonsCount} دروس مختارة</strong>
          <span>{Math.max(selectedLessonsCount, 1) * cardsPerLesson} بطاقة متوقعة</span>
          <span>سيتم حفظ الوصف والمصدر وجدولة المراجعة لكل بطاقة</span>
        </div>

        <div className="flashcards-actions">
          <Button onClick={onGenerate} disabled={selectedLessonsCount === 0 || cardTypes.length === 0}>
            توليد البطاقات
          </Button>
          <Button variant="secondary" onClick={onCancel}>إلغاء</Button>
        </div>
      </Card>
    </aside>
  </div>
);

const LessonSelector = ({
  units,
  scope,
  selectedLessonIds,
  selectedTopicIds,
  selectedUnitId,
  setSelectedUnitId,
  toggleLesson,
  toggleTopic,
}: {
  units: ReturnType<typeof useActiveCurriculum>['units'];
  scope: SetupScope;
  selectedLessonIds: string[];
  selectedTopicIds: string[];
  selectedUnitId: string;
  setSelectedUnitId: (value: string) => void;
  toggleLesson: (lessonId: string) => void;
  toggleTopic: (topicId: string) => void;
}) => {
  if (scope === 'study_plan') {
    return (
      <div className="flashcards-info-panel">
        سيتم استخدام الدروس المجدولة في خطة الدراسة الحالية عند توفرها. يمكنك أيضاً اختيار دروس محددة من القائمة.
      </div>
    );
  }
  if (scope === 'weak_topics') {
    return (
      <div className="flashcards-info-panel">
        سيتم اقتراح الدروس الأعلى صعوبة كنطاق أولي لنقاط الضعف، ويمكنك تعديل الاختيار يدوياً.
      </div>
    );
  }
  if (scope === 'unit') {
    return (
      <label className="form-group">
        <span>اختر الوحدة</span>
        <select value={selectedUnitId} onChange={(event) => setSelectedUnitId(event.target.value)}>
          <option value="">اختر وحدة</option>
          {units.map((unit) => (
            <option key={unit.id} value={String(unit.id)}>
              الوحدة {unit.unit_number} · {unit.title_ar}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <div className="flashcards-curriculum-tree">
      {units.map((unit) => (
        <section key={unit.id} className="flashcards-unit-block">
          <header>
            <strong>الوحدة {unit.unit_number}: {unit.title_ar}</strong>
            <span>{unit.chapters.length} فصول</span>
          </header>
          {unit.chapters.map((chapter) => (
            <div key={chapter.id} className="flashcards-chapter-block">
              <h3>{chapter.title_ar}</h3>
              <div className="flashcards-lesson-list">
                {chapter.lessons.map((lesson) => {
                  const lessonId = String(lesson.id);
                  const selected = selectedLessonIds.includes(lessonId);
                  return (
                    <article key={lesson.id} className={selected ? 'is-selected' : ''}>
                      <button type="button" onClick={() => toggleLesson(lessonId)} aria-pressed={selected}>
                        <span>درس {lesson.order}</span>
                        <strong>{lesson.title_ar}</strong>
                        <small>{lessonPageRange(lesson)}</small>
                      </button>
                      {selected && lesson.topics.length > 0 && (
                        <div className="flashcards-topic-row">
                          {lesson.topics.map((topic) => {
                            const topicId = String(topic.id);
                            return (
                              <button
                                key={topic.id}
                                type="button"
                                className={selectedTopicIds.includes(topicId) ? 'is-active' : ''}
                                onClick={() => toggleTopic(topicId)}
                                aria-pressed={selectedTopicIds.includes(topicId)}
                              >
                                {topic.title_ar}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
};

const FlashcardGenerationOverlay = () => (
  <Card className="flashcards-generating">
    <LoadingSkeleton rows={4} />
    <h2>يتم توليد بطاقات من محتوى الكتاب</h2>
    <p>نربط كل بطاقة بالدرس والموضوع والصفحات المصدرية ثم ننشئ حالة مراجعة متباعدة.</p>
  </Card>
);

const FlashcardDeckList = ({
  progress,
  decks,
  onCreate,
  onReview,
  onOpenDeck,
}: {
  progress: FlashcardProgressSummary;
  decks: FlashcardDeck[];
  onCreate: () => void;
  onReview: () => void;
  onOpenDeck: (deckId: number) => void;
}) => (
  <div className="flashcards-dashboard">
    {progress.totalCards > 0 && <FlashcardProgressSummaryCard progress={progress} onReview={onReview} onCreate={onCreate} />}
    <div className="section-title">
      <h2>مجموعات البطاقات</h2>
      <Button variant="secondary" onClick={onCreate}>إنشاء بطاقات</Button>
    </div>
    <div className="flashcards-deck-grid">
      {decks.map((deck) => (
        <FlashcardDeckCard key={deck.id} deck={deck} onOpen={() => onOpenDeck(deck.id)} onReview={onReview} />
      ))}
    </div>
  </div>
);

const FlashcardProgressSummaryCard = ({
  progress,
  onReview,
  onCreate,
}: {
  progress: FlashcardProgressSummary;
  onReview: () => void;
  onCreate: () => void;
}) => (
  <Card className="flashcards-progress-card">
    <div>
      <p className="eyebrow">تقدم البطاقات</p>
      <h2>{progress.masteryPercent}%</h2>
      <span>نسبة الإتقان</span>
      <ProgressBar value={progress.masteryPercent} tone="teal" />
    </div>
    <div className="flashcards-stat-grid">
      <span><strong>{progress.dueToday}</strong> مستحقة اليوم</span>
      <span><strong>{progress.newCards}</strong> جديدة</span>
      <span><strong>{progress.learningCards}</strong> قيد التعلم</span>
      <span><strong>{progress.masteredCards}</strong> متقنة</span>
      <span><strong>{progress.overdueCards}</strong> متأخرة</span>
    </div>
    <div className="flashcards-actions">
      <Button onClick={onReview}>ابدأ المراجعة</Button>
      <Button variant="secondary" onClick={onCreate}>إنشاء بطاقات</Button>
    </div>
  </Card>
);

const FlashcardDeckCard = ({ deck, onOpen, onReview }: { deck: FlashcardDeck; onOpen: () => void; onReview: () => void }) => (
  <Card className="flashcard-deck-card">
    <div>
      <StatusPill tone={deck.source === 'book_rag' ? 'teal' : 'blue'}>{deck.source === 'book_rag' ? 'من الكتاب' : 'مولدة'}</StatusPill>
      <StatusPill tone="blue">{deck.scopeType || 'lesson'}</StatusPill>
    </div>
    <h3>{deck.titleAr || deck.title}</h3>
    <p>{deck.descriptionAr || 'مجموعة بطاقات مراجعة ذكية.'}</p>
    <div className="flashcard-deck-stats">
      <span><strong>{deck.totalCards ?? deck.count}</strong> بطاقة</span>
      <span><strong>{deck.dueCards ?? 0}</strong> مستحقة</span>
      <span><strong>{deck.masteryPercent ?? 0}%</strong> إتقان</span>
    </div>
    <div className="flashcards-actions">
      <Button onClick={onOpen}>عرض المجموعة</Button>
      <Button variant="secondary" onClick={onReview}>مراجعة</Button>
    </div>
  </Card>
);

const FlashcardDeckDetail = ({
  deck,
  cards,
  onBack,
  onReview,
}: {
  deck: FlashcardDeck;
  cards: GeneratedFlashcard[];
  onBack: () => void;
  onReview: () => void;
}) => (
  <div className="flashcards-detail">
    <Card className="flashcards-detail-hero">
      <div>
        <p className="eyebrow">مجموعة بطاقات</p>
        <h2>{deck.titleAr || deck.title}</h2>
        <p>{deck.descriptionAr}</p>
      </div>
      <div className="flashcards-actions">
        <Button onClick={onReview}>ابدأ مراجعة المجموعة</Button>
        <Button variant="secondary" onClick={onBack}>العودة</Button>
      </div>
    </Card>
    <div className="flashcards-card-list">
      {cards.map((card) => (
        <Card key={card.id} className="flashcards-card-row">
          <div>
            <StatusPill tone={typeTone(card.cardType)}>{typeLabel(card.cardType)}</StatusPill>
            <StatusPill tone="gold">{card.difficulty}</StatusPill>
          </div>
          <h3>{card.front}</h3>
          <p>{card.descriptionAr}</p>
          <FlashcardSourcePanel card={card} />
        </Card>
      ))}
    </div>
  </div>
);

const FlashcardReviewSession = ({
  card,
  deck,
  index,
  total,
  revealed,
  hintVisible,
  detailsOpen,
  reviewFeedback,
  ratingPending,
  onShowHint,
  setDetailsOpen,
  onReveal,
  onRate,
  onExit,
}: {
  card: GeneratedFlashcard;
  deck: FlashcardDeck | null;
  index: number;
  total: number;
  revealed: boolean;
  hintVisible: boolean;
  detailsOpen: boolean;
  reviewFeedback: string;
  ratingPending: boolean;
  onShowHint: () => void;
  setDetailsOpen: (open: boolean) => void;
  onReveal: () => void;
  onRate: (rating: FlashcardRating) => void;
  onExit: () => void;
}) => (
  <div className="flashcards-review-layout">
    <Card className="flashcards-review-card">
      <div className="flashcards-review-head">
        <div>
          <span>البطاقة {index + 1} من {total}</span>
          <strong>{deck?.titleAr || deck?.title || 'جلسة مراجعة'}</strong>
        </div>
        <div>
          <StatusPill tone="blue">تكرار متباعد</StatusPill>
          <StatusPill tone={typeTone(card.cardType)}>{typeLabel(card.cardType)}</StatusPill>
          <StatusPill tone="gold">{card.difficulty}</StatusPill>
        </div>
      </div>
      <ProgressBar value={Math.round(((index + 1) / total) * 100)} tone="teal" />

      <FlashcardDescription card={card} />

      <div className="flashcard-study-surface">
        <p className="eyebrow">السؤال</p>
        <h2>{card.front}</h2>
      </div>

      {!revealed ? (
        <>
          {hintVisible && <FlashcardHint card={card} />}
          <div className="flashcard-pre-reveal-actions">
            <Button variant="ghost" onClick={onShowHint} disabled={hintVisible}>
              أحتاج تلميح
            </Button>
            <Button onClick={onReveal} className="flashcard-reveal-button">اعرض الإجابة</Button>
          </div>
        </>
      ) : (
        <>
          <FlashcardBack card={card} />
          <FlashcardSourcePanel card={card} />
          <FlashcardTechnicalDetails card={card} open={detailsOpen} setOpen={setDetailsOpen} />
          {reviewFeedback && <div className="flashcard-review-feedback">{reviewFeedback}</div>}
          <FlashcardReviewButtons onRate={onRate} disabled={ratingPending || Boolean(reviewFeedback)} />
        </>
      )}
      <Button variant="ghost" onClick={onExit}>إنهاء الجلسة</Button>
    </Card>
  </div>
);

const FlashcardHint = ({ card }: { card: GeneratedFlashcard }) => (
  <div className="flashcard-hint-panel">
    <strong>تلميح</strong>
    <p>{card.hintAr || 'فكّر في التعريف أو القانون المرتبط بعنوان البطاقة قبل كشف الإجابة.'}</p>
  </div>
);

const FlashcardDescription = ({ card }: { card: GeneratedFlashcard }) => (
  <div className="flashcard-description">
    <span>ما الذي تختبره؟</span>
    <p>{card.descriptionAr || 'تختبر هذه البطاقة فهماً كيميائياً من الدرس.'}</p>
    <small>
      {card.unitTitleAr || 'الكتاب'} · {card.lessonTitleAr || 'درس كيمياء'}
      {card.topicTitleAr ? ` · ${card.topicTitleAr}` : ''}
    </small>
  </div>
);

const FlashcardBack = ({ card }: { card: GeneratedFlashcard }) => (
  <div className="flashcard-answer-panel">
    <p className="eyebrow">الإجابة</p>
    <h3>{card.back}</h3>
    {card.explanationAr && <p>{card.explanationAr}</p>}
  </div>
);

const FlashcardSourcePanel = ({ card }: { card: GeneratedFlashcard }) => (
  <div className="flashcard-source-panel">
    <strong>المصدر من الكتاب</strong>
    <span>{sourcePages(card)}</span>
    {card.sourceChunkIds?.length ? <small>Chunks: {card.sourceChunkIds.join(', ')}</small> : null}
  </div>
);

const FlashcardTechnicalDetails = ({
  card,
  open,
  setOpen,
}: {
  card: GeneratedFlashcard;
  open: boolean;
  setOpen: (open: boolean) => void;
}) => (
  <div className="flashcard-technical-details">
    <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}>
      تفاصيل البطاقة
    </button>
    {open && (
      <div>
        <span>نوع البطاقة: {typeLabel(card.cardType)}</span>
        <span>الدرس: {card.lessonTitleAr || card.lessonId || 'غير محدد'}</span>
        <span>الموضوع: {card.topicTitleAr || 'كل موضوعات الدرس'}</span>
        <span>الصفحات: {sourcePages(card)}</span>
        <span>آخر مراجعة: {card.lastReviewedAt || 'لم تراجع بعد'}</span>
        <span>موعد المراجعة القادمة: {card.nextReviewAt || 'اليوم'}</span>
        {card.technicalDescription && <p>{card.technicalDescription}</p>}
      </div>
    )}
  </div>
);

const FlashcardReviewButtons = ({
  onRate,
  disabled,
}: {
  onRate: (rating: FlashcardRating) => void;
  disabled: boolean;
}) => (
  <div className="flashcard-review-buttons">
    {ratingOptions.map((option) => (
      <button
        key={option.value}
        type="button"
        className={`tone-${option.tone}`}
        disabled={disabled}
        onClick={() => onRate(option.value)}
      >
        <strong>{option.label}</strong>
        <span>{option.helper}</span>
      </button>
    ))}
  </div>
);
