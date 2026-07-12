import { api } from '../../../api/http';
import { allowDemoFallbacks } from '../../../config/demoFallbacks';
import type { CompanionMessageResponse, CompanionSuggestionResponse, LearningContext } from '../types';
import { buildCompanionMessage, buildCompanionSuggestions } from '../companionLogic';

type CompanionRequest = {
  message?: string;
  context: LearningContext;
  preferred_language?: 'ar' | 'en';
  response_mode?: 'text' | 'action';
};

const fallbackSuggestion = (context: LearningContext): CompanionSuggestionResponse => ({
  message: buildCompanionMessage(context),
  suggestedActions: buildCompanionSuggestions(context),
});

export const aiCompanionApi = {
  async getCompanionSuggestions(context: LearningContext): Promise<CompanionSuggestionResponse> {
    try {
      const { data } = await api.post<CompanionSuggestionResponse>('/ai/companion/suggest', {
        context,
        preferred_language: 'ar',
        response_mode: 'action',
      } satisfies CompanionRequest);
      return data;
    } catch (error) {
      if (!allowDemoFallbacks) throw error;
      return fallbackSuggestion(context);
    }
  },

  async sendCompanionMessage(message: string, context: LearningContext): Promise<CompanionMessageResponse> {
    try {
      const { data } = await api.post<CompanionMessageResponse>('/ai/companion/message', {
        message,
        context,
        preferred_language: 'ar',
        response_mode: 'text',
      } satisfies CompanionRequest);
      return data;
    } catch (error) {
      if (!allowDemoFallbacks) throw error;
      return {
        message: message.trim()
          ? `سأربط سؤالك بالسياق الحالي: ${buildCompanionMessage(context)}`
          : buildCompanionMessage(context),
        suggestedActions: buildCompanionSuggestions(context),
        responseMode: 'text',
      };
    }
  },

  async explainCurrentLesson(context: LearningContext): Promise<CompanionSuggestionResponse> {
    return {
      message: `سأفتح لك شرحاً موجهاً لدرس ${context.activeLessonTitleAr || 'الدرس الحالي'}.`,
      suggestedActions: buildCompanionSuggestions(context),
      targetRoute: `/ask-ai?question=${encodeURIComponent(`اشرح لي درس ${context.activeLessonTitleAr || 'الكيمياء الحالي'} من الكتاب`)}${context.activeLessonId ? `&lessonId=${context.activeLessonId}` : ''}`,
    };
  },

  async generateQuizFromContext(context: LearningContext): Promise<CompanionSuggestionResponse> {
    return {
      message: 'سأجهز اختباراً قصيراً من سياقك الحالي.',
      suggestedActions: buildCompanionSuggestions(context),
      targetRoute: `/quiz${context.activeLessonId ? `?lessonId=${context.activeLessonId}` : ''}`,
    };
  },

  async generateFlashcardsFromContext(context: LearningContext): Promise<CompanionSuggestionResponse> {
    return {
      message: 'سأفتح البطاقات لتراجع المفاهيم المرتبطة بالسياق الحالي.',
      suggestedActions: buildCompanionSuggestions(context),
      targetRoute: `/flashcards${context.activeLessonId ? `?lessonId=${context.activeLessonId}` : ''}`,
    };
  },
};
