import { api } from './http';
import { mockFlashcardDecks } from './mockData';
import { mockGenerateFlashcards } from './mockChemistryData';
import type { FlashcardDeck, FlashcardGenerationConfig, GeneratedFlashcard } from '../types';

interface BackendFlashcard {
  id: number;
  topic_id: number;
  front_ar: string;
  back_ar: string;
}

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
      const { data } = await api.post<GeneratedFlashcard[]>('/flashcards/generate', config);
      return data;
    } catch {
      // Fallback to local mock generator
      return mockGenerateFlashcards(config);
    }
  },

  async getFlashcards(): Promise<GeneratedFlashcard[]> {
    try {
      const { data } = await api.get<GeneratedFlashcard[]>('/flashcards');
      return data;
    } catch {
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
      const { data } = await api.patch<{ success: boolean }>(`/flashcards/${id}/review`, { reviewState });
      return data;
    } catch {
      return { success: true };
    }
  },

  async getDueFlashcards(): Promise<GeneratedFlashcard[]> {
    try {
      const { data } = await api.get<GeneratedFlashcard[]>('/flashcards/due');
      return data;
    } catch {
      // Fallback: return cards that might be due (we filter the default cards)
      const allCards = await this.getFlashcards();
      return allCards.filter(c => c.reviewState !== 'known');
    }
  }
};
