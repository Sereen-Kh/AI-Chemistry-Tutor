import { api } from './http';
import { mockFlashcardDecks } from './mockData';
import type { FlashcardDeck } from '../types';

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
};
