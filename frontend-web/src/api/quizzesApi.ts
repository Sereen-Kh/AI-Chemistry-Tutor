import { api } from './http';
import type { QuizGenerationConfig, GeneratedQuizQuestion } from '../types';

interface BackendQuizQuestion {
  id: number;
  question_text: string;
  question_type: string;
  options?: string[] | Record<string, string> | null;
  page_number?: number | null;
  source_id?: number | null;
  difficulty?: number | null;
  correct_answer?: string | null;
  explanation?: string | null;
}

interface BackendQuizGenerateResponse {
  questions: BackendQuizQuestion[];
}

interface BackendQuizSubmitResponse {
  attempt_id: number;
  score: number;
  total: number;
  weak_topics?: unknown;
  percentage?: number;
}

const difficultyNumber = (difficulty: QuizGenerationConfig['difficulty']): number | undefined => {
  if (difficulty === 'easy') return 1;
  if (difficulty === 'medium') return 3;
  if (difficulty === 'hard') return 5;
  return undefined;
};

const difficultyLabel = (difficulty?: number | null): GeneratedQuizQuestion['difficulty'] => {
  if (!difficulty || difficulty <= 2) return 'easy';
  if (difficulty >= 4) return 'hard';
  return 'medium';
};

const optionList = (options?: string[] | Record<string, string> | null): string[] | undefined => {
  if (!options) return undefined;
  if (Array.isArray(options)) return options.map(String);
  return Object.values(options).map(String);
};

const mapBackendQuestion = (question: BackendQuizQuestion): GeneratedQuizQuestion => ({
  id: String(question.id),
  lessonId: 'backend',
  chapterId: 'backend',
  questionType: question.question_type === 'true_false'
    ? 'true_false'
    : question.question_type === 'calculation'
      ? 'calculation'
      : question.question_type === 'short_answer'
        ? 'short_answer'
        : 'mcq',
  question: question.question_text,
  options: optionList(question.options),
  correctAnswer: question.correct_answer ?? '',
  correctOptionIndex: undefined,
  explanation: question.explanation ?? 'راجع مصدر السؤال لمعرفة سبب الإجابة.',
  difficulty: difficultyLabel(question.difficulty),
  sourcePage: question.page_number ?? 0,
  sourceChunkId: question.source_id ? String(question.source_id) : undefined,
});

export const quizzesApi = {
  async generateQuiz(config: QuizGenerationConfig): Promise<GeneratedQuizQuestion[]> {
    try {
      const { data } = await api.post<BackendQuizGenerateResponse>('/quizzes/generate', {
        topic_id: undefined,
        source_type: 'textbook',
        difficulty: difficultyNumber(config.difficulty),
        limit: Math.min(config.totalQuestions || config.lessonIds.length * config.questionsPerLesson || 5, 30),
      });
      const mapped = data.questions.map(mapBackendQuestion);
      if (!mapped.length) {
        throw new Error('Quiz backend returned no questions for the selected curriculum scope.');
      }
      return mapped;
    } catch (error) {
      console.warn('Quiz backend generation unavailable', error);
      throw error;
    }
  },

  async submitQuizAnswer(quizId: string, questionId: string, answer: string): Promise<{ correct: boolean; explanation: string }> {
    void quizId;
    void questionId;
    void answer;
    return { correct: true, explanation: '' };
  },

  async submitQuizResult(quizId: string, score: number, total: number): Promise<BackendQuizSubmitResponse | { success: true }> {
    try {
      const { data } = await api.post<BackendQuizSubmitResponse>('/quizzes/submit', {
        topic_id: 1,
        answers: {
          quiz_id: quizId,
          score: String(score),
          total: String(total),
        },
      });
      return data;
    } catch (error) {
      console.warn('Quiz result submission failed; keeping local result only', error);
      return { success: true };
    }
  }
};
