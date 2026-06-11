import { api } from './http';
import { toBackendAnswerFormat, toBackendTeachingStyle } from './authApi';
import type { UserPreferences, UserProfile } from '../types';

export const userApi = {
  async updatePreferences(preferences: Partial<UserPreferences>): Promise<UserProfile> {
    const { data } = await api.patch<UserProfile>('/users/me', {
      teaching_style: preferences.teachingStyle ? toBackendTeachingStyle(preferences.teachingStyle) : undefined,
      answer_format: preferences.answerFormat ? toBackendAnswerFormat(preferences.answerFormat) : undefined,
      teaching_level: preferences.teachingLevel,
      explanation_method: preferences.explanationMethod,
      learning_modes: preferences.learningModes,
      student_interests: preferences.studentInterests,
      language: preferences.language,
    });
    return data;
  },
};
