import { api } from './http';
import type { QuizGenerationConfig, GeneratedQuizQuestion } from '../types';

interface BackendQuizQuestion {
  id: number;
  lesson_id?: number | null;
  topic_id?: number | null;
  question_text: string;
  question_type: string;
  options?: string[] | Record<string, string> | null;
  page_number?: number | null;
  source_id?: number | null;
  difficulty?: number | null;
  correct_answer?: string | null;
  explanation?: string | null;
  quality_status?: string | null;
  reviewed_metadata_version?: string | null;
}

interface BackendQuizGenerateResponse {
  questions: BackendQuizQuestion[];
  generated?: boolean;
  source?: string;
}

interface BackendQuizSubmitResponse {
  attempt_id: number;
  score: number;
  total: number;
  weak_topics?: unknown;
  percentage?: number;
}

export interface QuizSubmitPayload {
  topicId?: string | number | null;
  answers: Record<string, string>;
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

const normalizeQuestionType = (type: string): GeneratedQuizQuestion['questionType'] => (
  type === 'true_false'
    ? 'true_false'
    : type === 'calculation'
      ? 'calculation'
      : type === 'short_answer' || type === 'fill_blank'
        ? 'short_answer'
        : type === 'equation_balancing'
          ? 'equation_balancing'
          : 'mcq'
);

const correctOptionIndex = (options: string[] | undefined, correctAnswer?: string | null): number | undefined => {
  if (!options?.length || !correctAnswer) return undefined;
  const normalizedCorrect = String(correctAnswer).trim();
  const index = options.findIndex((option) => String(option).trim() === normalizedCorrect);
  return index >= 0 ? index : undefined;
};

const mapBackendQuestion = (question: BackendQuizQuestion): GeneratedQuizQuestion => {
  const options = optionList(question.options);
  return {
    id: String(question.id),
    lessonId: question.lesson_id == null ? 'backend' : String(question.lesson_id),
    topicId: question.topic_id == null ? undefined : String(question.topic_id),
    chapterId: 'backend',
    questionType: normalizeQuestionType(question.question_type),
    question: question.question_text,
    options,
    correctAnswer: question.correct_answer ?? '',
    correctOptionIndex: correctOptionIndex(options, question.correct_answer),
    explanation: question.explanation ?? 'راجع مصدر السؤال لمعرفة سبب الإجابة.',
    difficulty: difficultyLabel(question.difficulty),
    sourcePage: question.page_number ?? 0,
    sourceChunkId: question.source_id ? String(question.source_id) : undefined,
  };
};

const extractBackendDetail = (error: unknown): string => {
  const maybeResponse = error as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
  const detail = maybeResponse.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const payload = detail as { message?: unknown; code?: unknown; quality_status?: unknown; lesson_title?: unknown };
    return [payload.message, payload.code, payload.quality_status, payload.lesson_title]
      .filter(Boolean)
      .map(String)
      .join(' ');
  }
  if (Array.isArray(detail)) return detail.map((item) => {
    if (typeof item === 'string') return item;
    if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg);
    return '';
  }).filter(Boolean).join(' ');
  return maybeResponse.message || '';
};

export const quizGenerationErrorMessage = (error: unknown): string => {
  const maybeResponse = error as { response?: { status?: number } };
  const detail = extractBackendDetail(error);
  if (maybeResponse.response?.status === 401 || /unauthorized|forbidden|token/i.test(detail)) {
    return 'سجّل الدخول لإنشاء اختبار.';
  }
  if (/field required|required|lesson|اختر درس/i.test(detail)) {
    return 'اختر درساً واحداً على الأقل لتوليد الاختبار.';
  }
  if (/not found|لم يتم العثور/i.test(detail)) {
    return 'تعذر تحميل بيانات الدرس المحدد.';
  }
  if (/LESSON_NOT_READY_FOR_QUIZ_GENERATION|needs_review|blocked|missing_ready_content|توليد الاختبارات مسموح/i.test(detail)) {
    return 'لا يمكن توليد اختبار لهذا الدرس لأنه غير جاهز بعد.';
  }
  if (/service|unavailable|ai|llm|timeout|503/i.test(detail)) {
    return 'خدمة توليد الأسئلة غير متاحة حالياً. جرّب لاحقاً أو افتح اسأل AI.';
  }
  if (/no questions|لا توجد أسئلة|empty/i.test(detail)) {
    return 'لا توجد أسئلة كافية لهذا الدرس حالياً.';
  }
  return 'تعذر توليد الأسئلة من الخادم حالياً.';
};

export const quizzesApi = {
  async generateQuiz(config: QuizGenerationConfig): Promise<GeneratedQuizQuestion[]> {
    try {
      const { data } = await api.post<BackendQuizGenerateResponse>('/quizzes/generate', {
        topic_id: config.topicId ? Number(config.topicId) : undefined,
        lesson_id: config.lessonIds[0] ? Number(config.lessonIds[0]) : undefined,
        lesson_ids: config.lessonIds.map(Number).filter(Number.isFinite),
        topic_ids: config.topicId ? [Number(config.topicId)].filter(Number.isFinite) : [],
        source_type: 'textbook',
        difficulty: difficultyNumber(config.difficulty),
        limit: Math.min(config.totalQuestions || config.lessonIds.length * config.questionsPerLesson || 5, 30),
        question_count: Math.min(config.totalQuestions || config.lessonIds.length * config.questionsPerLesson || 5, 30),
        question_types: config.questionTypes,
      });
      const mapped = data.questions.map(mapBackendQuestion);
      if (!mapped.length) {
        throw new Error('Quiz backend returned no questions for the selected curriculum scope.');
      }
      return mapped;
    } catch (error) {
      console.warn('Quiz backend generation unavailable', error);
      throw new Error(quizGenerationErrorMessage(error), { cause: error });
    }
  },

  async submitQuizAnswer(quizId: string, questionId: string, answer: string): Promise<{ correct: boolean; explanation: string }> {
    void quizId;
    void questionId;
    void answer;
    return { correct: true, explanation: '' };
  },

  async submitQuizResult(payload: QuizSubmitPayload): Promise<BackendQuizSubmitResponse> {
    try {
      const { data } = await api.post<BackendQuizSubmitResponse>('/quizzes/submit', {
        topic_id: payload.topicId == null ? undefined : Number(payload.topicId),
        answers: payload.answers,
      });
      return data;
    } catch (error) {
      console.warn('Quiz result submission failed', error);
      throw new Error('تعذر حفظ نتيجة الاختبار. بقيت النتيجة ظاهرة محلياً.', { cause: error });
    }
  }
};
