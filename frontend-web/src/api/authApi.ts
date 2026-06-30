import { api } from './http';
import { mockInterests } from './mockData';
import { setToken } from '../lib/storage';
import type { InterestCategory, TeachingStyle, UserPreferences, UserProfile } from '../types';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  firstName: string;
  lastName: string;
  email: string;
  password: string;
  grade: string;
  subject: string;
}

const toBackendTeachingStyle = (style: UserPreferences['teachingStyle']): string =>
  ({
    real_life: 'real_life_examples',
    visual: 'visual',
    exam: 'academic',
    simple: 'beginner',
    beginner: 'beginner',
    step_by_step: 'step_by_step',
    academic: 'academic',
    fast_summary: 'fast_summary',
    real_life_examples: 'real_life_examples',
  } satisfies Record<TeachingStyle, string>)[style ?? 'real_life'];

const toBackendAnswerFormat = (format: UserPreferences['answerFormat']): string =>
  ({
    text: 'text',
    audio: 'audio',
    image: 'images',
    video: 'video',
  })[format ?? 'text'];

export const authApi = {
  async login(email: string, password: string): Promise<string> {
    const { data } = await api.post<LoginResponse>('/auth/login', { email, password });
    setToken(data.access_token);
    return data.access_token;
  },

  async register(payload: RegisterPayload): Promise<UserProfile> {
    const { data } = await api.post<UserProfile>('/auth/register', {
      first_name: payload.firstName,
      last_name: payload.lastName,
      email: payload.email,
      password: payload.password,
    });
    return data;
  },

  async me(): Promise<UserProfile> {
    const { data } = await api.get<UserProfile>('/auth/me');
    return data;
  },

  async interests(): Promise<InterestCategory[]> {
    try {
      const { data } = await api.get<InterestCategory[]>('/auth/interests');
      return data.length ? data : mockInterests;
    } catch {
      return mockInterests;
    }
  },

  async completeOnboarding(preferences: UserPreferences, interestIds: number[]): Promise<UserProfile> {
    const { data } = await api.patch<UserProfile>('/auth/onboarding', {
      grade: preferences.grade,
      teaching_style: toBackendTeachingStyle(preferences.teachingStyle),
      answer_format: toBackendAnswerFormat(preferences.answerFormat),
      teaching_level: preferences.teachingLevel,
      explanation_method: preferences.explanationMethod,
      learning_modes: preferences.learningModes,
      student_interests: preferences.studentInterests,
      language: preferences.language,
      interest_ids: interestIds,
    });
    return data;
  },
};

export { toBackendAnswerFormat, toBackendTeachingStyle };
