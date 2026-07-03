import { api } from './http';
import { toBackendAnswerFormat, toBackendTeachingStyle } from './authApi';
import type { ExplanationMethod, LearningMode, StudentInterest, TeachingLevel, UserPreferences, UserProfile } from '../types';

export interface StudentProfileResponse {
  id: number;
  user_id: number;
  grade: string;
  subject: string;
  learning_style: string;
  teaching_level: TeachingLevel;
  explanation_method: ExplanationMethod;
  learning_modes: LearningMode[];
  student_interests: StudentInterest[];
  preferred_language: 'ar' | 'en' | string;
  goals?: string | null;
  target_exam_date?: string | null;
  onboarding_completed?: boolean;
}

export const preferencesFromProfile = (
  profile: StudentProfileResponse,
  current: UserPreferences,
): UserPreferences => {
  const learningModes = profile.learning_modes?.length ? profile.learning_modes : current.learningModes;
  const answerFormat = learningModes.includes('image')
    ? 'image'
    : learningModes.includes('audio')
      ? 'audio'
      : 'text';
  return {
    ...current,
    grade: profile.grade || current.grade,
    subject: profile.subject || current.subject,
    language: profile.preferred_language === 'en' ? 'en' : 'ar',
    teachingLevel: profile.teaching_level,
    explanationMethod: profile.explanation_method,
    learningModes,
    studentInterests: profile.student_interests ?? current.studentInterests,
    interests: profile.student_interests ?? current.studentInterests,
    teachingStyle: profile.learning_style as UserPreferences['teachingStyle'],
    answerFormat,
    goals: profile.goals ?? '',
    targetExamDate: profile.target_exam_date ?? '',
  };
};

const toStudentProfilePayload = (preferences: Partial<UserPreferences>) => ({
  grade: preferences.grade,
  subject: preferences.subject,
  learning_style: preferences.teachingStyle ? toBackendTeachingStyle(preferences.teachingStyle) : undefined,
  teaching_level: preferences.teachingLevel,
  explanation_method: preferences.explanationMethod,
  learning_modes: preferences.learningModes,
  student_interests: preferences.studentInterests,
  preferred_language: preferences.language,
  goals: preferences.goals || null,
  target_exam_date: preferences.targetExamDate || null,
});

export const userApi = {
  async getProfile(): Promise<StudentProfileResponse> {
    const { data } = await api.get<StudentProfileResponse>('/student-profile/me');
    return data;
  },

  async updateProfile(preferences: Partial<UserPreferences>): Promise<StudentProfileResponse> {
    const { data } = await api.put<StudentProfileResponse>('/student-profile/me', toStudentProfilePayload(preferences));
    return data;
  },

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
