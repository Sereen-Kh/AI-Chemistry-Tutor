import { api } from './http';
import { mockGenerateQuiz } from './mockChemistryData';
import type { QuizGenerationConfig, GeneratedQuizQuestion } from '../types';

export const quizzesApi = {
  async generateQuiz(config: QuizGenerationConfig): Promise<GeneratedQuizQuestion[]> {
    try {
      const { data } = await api.post<GeneratedQuizQuestion[]>('/quizzes/generate', config);
      return data;
    } catch {
      // Fallback to local mock generator
      return mockGenerateQuiz(config);
    }
  },

  async getQuizzes(): Promise<any[]> {
    try {
      const { data } = await api.get<any[]>('/quizzes');
      return data;
    } catch {
      return [];
    }
  },

  async getQuizById(id: string): Promise<any> {
    try {
      const { data } = await api.get<any>(`/quizzes/${id}`);
      return data;
    } catch {
      return null;
    }
  },

  async submitQuizAnswer(quizId: string, questionId: string, answer: string): Promise<{ correct: boolean; explanation: string }> {
    try {
      const { data } = await api.post<{ correct: boolean; explanation: string }>(`/quizzes/${quizId}/submit`, { questionId, answer });
      return data;
    } catch {
      return { correct: true, explanation: '' };
    }
  },

  async submitQuizResult(quizId: string, score: number, total: number): Promise<any> {
    try {
      const { data } = await api.post<any>(`/quizzes/${quizId}/result`, { score, total });
      return data;
    } catch {
      return { success: true };
    }
  }
};
