import { api } from './http';
import type {
  FlashcardCardType,
  FlashcardDeck,
  FlashcardGenerationConfig,
  FlashcardProgressSummary,
  FlashcardRating,
  GeneratedFlashcard,
} from '../types';

type BackendReviewState = {
  status?: 'new' | 'learning' | 'review' | 'mastered' | 'suspended';
  due_at?: string | null;
  last_reviewed_at?: string | null;
  repetitions?: number;
  lapses?: number;
  ease_factor?: number;
  interval_days?: number;
  next_review_at?: string | null;
  mastered?: boolean;
  review_count?: number;
};

type BackendFlashcard = {
  id: number;
  deck_id?: number | null;
  unit_id?: number | null;
  chapter_id?: number | null;
  lesson_id?: number | null;
  topic_id?: number | null;
  card_type?: FlashcardCardType | string;
  difficulty?: 'easy' | 'medium' | 'hard' | string;
  front_ar: string;
  back_ar: string;
  front_text_ar?: string | null;
  back_text_ar?: string | null;
  hint_ar?: string | null;
  description_ar?: string;
  technical_description?: string;
  explanation_ar?: string;
  source_page_start?: number | null;
  source_page_end?: number | null;
  source_chunk_ids?: Array<number | string> | null;
  metadata_json?: {
    unit_title_ar?: string;
    chapter_title_ar?: string;
    lesson_title_ar?: string;
    topic_title_ar?: string;
  } | null;
  review?: BackendReviewState | null;
  mastered?: boolean;
  review_count?: number;
  ease_factor?: number;
  interval_days?: number;
  next_review_at?: string | null;
  last_reviewed?: string | null;
};

type BackendDeck = {
  id: number;
  title_ar: string;
  description_ar: string;
  scope_type: string;
  scope_id?: string | null;
  status: string;
  source: string;
  total_cards: number;
  due_cards: number;
  new_cards: number;
  learning_cards: number;
  mastered_cards: number;
  overdue_cards: number;
  mastery_percent: number;
  cards: BackendFlashcard[];
  created_at: string;
  updated_at: string;
};

type BackendProgress = {
  total_cards: number;
  due_today: number;
  new_cards: number;
  learning_cards: number;
  mastered_cards: number;
  overdue_cards: number;
  mastery_percent: number;
};

type BackendReviewResponse = {
  card_id: number;
  new_due_at: string | null;
  status: 'new' | 'learning' | 'review' | 'mastered' | 'suspended';
  interval_days: number;
  ease_factor: number;
  repetitions: number;
  lapses: number;
};

type BackendReviewSession = {
  session_id: string;
  deck_id?: number | null;
  total_cards: number;
  cards: BackendFlashcard[];
};

const normalizeCardType = (type?: string): FlashcardCardType => {
  const map: Record<string, FlashcardCardType> = {
    term: 'term_definition',
    definition: 'term_definition',
    formula: 'equation_law',
    reaction: 'reaction_balancing',
    comparison: 'compare_contrast',
    experiment: 'experiment_result',
    common_mistake: 'concept_explanation',
  };
  return map[type || ''] || (type as FlashcardCardType) || 'concept_explanation';
};

const normalizeDifficulty = (difficulty?: string): GeneratedFlashcard['difficulty'] => {
  if (difficulty === 'easy' || difficulty === 'hard') return difficulty;
  return 'medium';
};

const mapReviewState = (card: BackendFlashcard): GeneratedFlashcard['reviewState'] => {
  const status = card.review?.status;
  if (status === 'mastered') return 'mastered';
  if (status === 'suspended') return 'suspended';
  if (status === 'learning') return 'learning';
  if (status === 'review') return 'review';
  if (card.mastered) return 'known';
  if ((card.review_count || card.review?.review_count || 0) > 0) return 'review';
  return 'new';
};

const mapBackendCard = (card: BackendFlashcard): GeneratedFlashcard => {
  const review = card.review || {};
  return {
    id: String(card.id),
    deckId: card.deck_id == null ? null : String(card.deck_id),
    unitId: card.unit_id == null ? null : String(card.unit_id),
    chapterId: card.chapter_id == null ? null : String(card.chapter_id),
    lessonId: card.lesson_id == null ? null : String(card.lesson_id),
    topicId: card.topic_id == null ? null : String(card.topic_id),
    front: card.front_text_ar || card.front_ar,
    back: card.back_text_ar || card.back_ar,
    cardType: normalizeCardType(card.card_type),
    difficulty: normalizeDifficulty(card.difficulty),
    sourcePage: card.source_page_start || 0,
    sourcePageEnd: card.source_page_end || null,
    sourceChunkId: card.source_chunk_ids?.[0] == null ? undefined : String(card.source_chunk_ids[0]),
    sourceChunkIds: card.source_chunk_ids?.map(String) || [],
    descriptionAr: card.description_ar || 'تختبر هذه البطاقة فهماً كيميائياً من الدرس.',
    technicalDescription: card.technical_description || '',
    hintAr: card.hint_ar || undefined,
    explanationAr: card.explanation_ar || card.back_text_ar || card.back_ar,
    unitTitleAr: card.metadata_json?.unit_title_ar,
    chapterTitleAr: card.metadata_json?.chapter_title_ar,
    lessonTitleAr: card.metadata_json?.lesson_title_ar,
    topicTitleAr: card.metadata_json?.topic_title_ar,
    reviewState: mapReviewState(card),
    repetitions: review.repetitions || review.review_count || card.review_count || 0,
    lapses: review.lapses || 0,
    easeFactor: review.ease_factor || card.ease_factor || 2.5,
    intervalDays: review.interval_days || card.interval_days || 0,
    nextReviewAt: review.next_review_at || card.next_review_at || review.due_at || undefined,
    dueAt: review.due_at || null,
    lastReviewedAt: review.last_reviewed_at || card.last_reviewed || null,
  };
};

const mapDeck = (deck: BackendDeck): FlashcardDeck => ({
  id: deck.id,
  title: deck.title_ar,
  titleAr: deck.title_ar,
  topic: deck.scope_type,
  count: deck.total_cards,
  mastered: deck.mastered_cards,
  cards: deck.cards.map((card) => ({
    id: card.id,
    front: card.front_text_ar || card.front_ar,
    back: card.back_text_ar || card.back_ar,
  })),
  descriptionAr: deck.description_ar,
  scopeType: deck.scope_type,
  scopeId: deck.scope_id,
  status: deck.status,
  source: deck.source,
  totalCards: deck.total_cards,
  dueCards: deck.due_cards,
  newCards: deck.new_cards,
  learningCards: deck.learning_cards,
  masteredCards: deck.mastered_cards,
  overdueCards: deck.overdue_cards,
  masteryPercent: deck.mastery_percent,
  createdAt: deck.created_at,
  updatedAt: deck.updated_at,
});

const configToPayload = (config: FlashcardGenerationConfig) => {
  const lessonIds = config.lessonIds.map(Number).filter(Number.isFinite);
  const topicIds = [
    ...(config.topicIds || []).map(Number).filter(Number.isFinite),
    ...(config.topicId ? [Number(config.topicId)] : []),
  ].filter(Number.isFinite);
  const unitIds = (config.unitIds || []).map(Number).filter(Number.isFinite);
  const scopeType = config.mode === 'chapter'
    ? 'unit'
    : config.mode === 'study_plan'
      ? 'study_plan'
      : config.mode === 'weak_lessons'
        ? 'weak_topics'
        : 'lesson';

  return {
    scope_type: scopeType,
    lesson_ids: lessonIds,
    topic_ids: topicIds,
    unit_ids: unitIds,
    cards_per_lesson: config.cardsPerLesson,
    card_types: config.cardTypes.map(normalizeCardType),
    difficulty: config.difficulty,
    include_sources: config.includeSourcePage,
    title_ar: lessonIds.length === 1 ? 'بطاقات درس كيمياء' : 'بطاقات مراجعة كيمياء',
  };
};

const mapProgress = (progress: BackendProgress): FlashcardProgressSummary => ({
  totalCards: progress.total_cards,
  dueToday: progress.due_today,
  newCards: progress.new_cards,
  learningCards: progress.learning_cards,
  masteredCards: progress.mastered_cards,
  overdueCards: progress.overdue_cards,
  masteryPercent: progress.mastery_percent,
});

const qualityToRating = (reviewState: 'new' | 'learning' | 'known' | 'review'): FlashcardRating => {
  if (reviewState === 'known') return 'easy';
  if (reviewState === 'review') return 'again';
  if (reviewState === 'learning') return 'hard';
  return 'good';
};

export const flashcardsApi = {
  async getDecks(): Promise<FlashcardDeck[]> {
    const { data } = await api.get<BackendDeck[]>('/flashcards/decks');
    return data.map(mapDeck);
  },

  async getDeck(deckId: number | string): Promise<FlashcardDeck & { generatedCards: GeneratedFlashcard[] }> {
    const { data } = await api.get<BackendDeck>(`/flashcards/decks/${deckId}`);
    return {
      ...mapDeck(data),
      generatedCards: data.cards.map(mapBackendCard),
    };
  },

  async generateDeck(config: FlashcardGenerationConfig): Promise<FlashcardDeck & { generatedCards: GeneratedFlashcard[] }> {
    const { data } = await api.post<BackendDeck>('/flashcards/decks/generate', configToPayload(config));
    return {
      ...mapDeck(data),
      generatedCards: data.cards.map(mapBackendCard),
    };
  },

  async generateFlashcards(config: FlashcardGenerationConfig): Promise<GeneratedFlashcard[]> {
    const deck = await this.generateDeck(config);
    return deck.generatedCards;
  },

  async getFlashcards(): Promise<GeneratedFlashcard[]> {
    const { data } = await api.get<BackendFlashcard[]>('/flashcards');
    return data.map(mapBackendCard);
  },

  async updateFlashcardReviewState(id: string, reviewState: 'new' | 'learning' | 'known' | 'review'): Promise<{ success: boolean }> {
    await this.reviewFlashcard(id, qualityToRating(reviewState));
    return { success: true };
  },

  async reviewFlashcard(id: string | number, rating: FlashcardRating): Promise<BackendReviewResponse> {
    const { data } = await api.post<BackendReviewResponse>(`/flashcards/${id}/review`, { rating });
    return data;
  },

  async getDueFlashcards(deckId?: string | number, limit = 30): Promise<GeneratedFlashcard[]> {
    const { data } = await api.get<BackendFlashcard[]>('/flashcards/due', {
      params: { limit, ...(deckId ? { deck_id: deckId } : {}) },
    });
    return data.map(mapBackendCard);
  },

  async getProgress(): Promise<FlashcardProgressSummary> {
    const { data } = await api.get<BackendProgress>('/flashcards/progress');
    return mapProgress(data);
  },

  async createReviewSession(deckId?: string | number, limit = 20): Promise<{ sessionId: string; cards: GeneratedFlashcard[] }> {
    const { data } = await api.post<BackendReviewSession>('/flashcards/review-sessions', {
      deck_id: deckId ? Number(deckId) : undefined,
      limit,
    });
    return {
      sessionId: data.session_id,
      cards: data.cards.map(mapBackendCard),
    };
  },
};
