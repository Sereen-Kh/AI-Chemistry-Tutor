import { api } from './http';
import { mockFlashcardDecks } from './mockData';
import { mockGenerateFlashcards } from './mockChemistryData';
import type { FlashcardDeck, FlashcardGenerationConfig, GeneratedFlashcard } from '../types';

interface BackendFlashcard {
  id: number;
  topic_id: number;
  front_ar: string;
  back_ar: string;
  created_at?: string;
  updated_at?: string;
}

interface BackendFlashcardProgress {
  mastered: boolean;
  review_count: number;
  ease_factor: number;
  interval_days: number;
  next_review_at?: string | null;
}

interface BackendDueFlashcard extends BackendFlashcard {
  mastered: boolean;
  review_count: number;
  ease_factor: number;
  interval_days: number;
  next_review_at?: string | null;
  last_reviewed?: string | null;
}

const mapBackendCard = (card: BackendFlashcard): GeneratedFlashcard => ({
  id: String(card.id),
  lessonId: `topic_${card.topic_id}`,
  chapterId: 'backend',
  front: card.front_ar,
  back: card.back_ar,
  cardType: 'definition',
  difficulty: 'medium',
  sourcePage: 0,
  reviewState: 'new',
});

const reviewQuality = (reviewState: 'new' | 'learning' | 'known' | 'review'): number => {
  if (reviewState === 'known') return 5;
  if (reviewState === 'review') return 2;
  if (reviewState === 'learning') return 3;
  return 0;
};

export const flashcardsApi = {
  async getDecks(): Promise<FlashcardDeck[]> {
    try {
      const { data } = await api.get<BackendFlashcard[]>('/flashcards');
      if (!data.length) return mockFlashcardDecks;
      return [
        {
          id: 1,
          title: 'بطاقات من قاعدة البيانات',
          topic: 'Chemistry',
          count: data.length,
          mastered: 0,
          cards: data.map((card) => ({
            id: card.id,
            front: card.front_ar,
            back: card.back_ar,
          })),
        },
      ];
    } catch {
      return mockFlashcardDecks;
    }
  },

  async generateFlashcards(config: FlashcardGenerationConfig): Promise<GeneratedFlashcard[]> {
    try {
      const { data } = await api.post<BackendFlashcard[]>('/flashcards/generate', {
        topic_id: undefined,
        lesson_id: Number(config.lessonIds[0]) || undefined,
        limit: config.cardsPerLesson || 8,
        created_by: 'generated',
      });
      return data.map(mapBackendCard);
    } catch (error) {
      console.warn('Flashcard generation backend unavailable, using local generator', error);
      return mockGenerateFlashcards(config);
    }
  },

  async getFlashcards(): Promise<GeneratedFlashcard[]> {
    try {
      const { data } = await api.get<BackendFlashcard[]>('/flashcards');
      return data.map(mapBackendCard);
    } catch (error) {
      console.warn('Flashcards backend unavailable, using local generated cards', error);
      // Fallback: generate some mock cards from lesson_1_1 as a default deck
      return mockGenerateFlashcards({
        mode: 'single_lesson',
        lessonIds: ['lesson_1_1', 'lesson_1_2'],
        cardsPerLesson: 5,
        cardTypes: ['term', 'definition', 'formula', 'experiment'],
        difficulty: 'mixed',
        includeSourcePage: true,
        spacedRepetitionEnabled: true
      });
    }
  },

  async updateFlashcardReviewState(id: string, reviewState: 'new' | 'learning' | 'known' | 'review'): Promise<{ success: boolean }> {
    try {
      await api.post<BackendFlashcardProgress>(`/flashcards/${id}/review`, {
        quality: reviewQuality(reviewState),
      });
      return { success: true };
    } catch (error) {
      console.warn('Flashcard review sync failed; keeping local state', error);
      return { success: true };
    }
  },

  async getDueFlashcards(): Promise<GeneratedFlashcard[]> {
    try {
      const { data } = await api.get<BackendDueFlashcard[]>('/flashcards/due');
      return data.map((card) => ({
        ...mapBackendCard(card),
        reviewState: card.mastered ? 'known' : card.review_count > 0 ? 'review' : 'new',
      }));
    } catch (error) {
      console.warn('Due flashcards backend unavailable, using local due cards', error);
      const allCards = await this.getFlashcards();
      return allCards.filter(c => c.reviewState !== 'known');
    }
  }
};
