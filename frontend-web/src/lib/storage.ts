import type { LearningMode, StudentInterest, UserPreferences } from '../types';

export const TOKEN_KEY = 'edumind_access_token';
export const PREFS_KEY = 'edumind_user_preferences';

export const defaultPreferences: UserPreferences = {
  interests: ['daily_life', 'laboratory'],
  teachingStyle: 'real_life',
  answerFormat: 'text',
  teachingLevel: 'standard',
  explanationMethod: 'direct',
  learningModes: ['text'],
  studentInterests: ['daily_life', 'laboratory'],
  language: 'ar',
  grade: 'grade_9',
  subject: 'chemistry',
};

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

export const loadPreferences = (): UserPreferences => {
  const raw = localStorage.getItem(PREFS_KEY);
  if (!raw) return defaultPreferences;
  try {
    const parsed = JSON.parse(raw) as Partial<UserPreferences>;
    const legacyStyle = parsed.teachingStyle;
    const legacyFormat = parsed.answerFormat;
    const teachingLevel = parsed.teachingLevel
      ?? (legacyStyle === 'simple' ? 'simple' : legacyStyle === 'exam' ? 'academic' : 'standard');
    const explanationMethod = parsed.explanationMethod
      ?? (legacyStyle === 'real_life' ? 'real_life_example' : legacyStyle === 'exam' ? 'exam_mode' : 'direct');
    const learningModes: LearningMode[] = parsed.learningModes
      ?? (legacyFormat === 'image'
        ? ['text', 'image'] as LearningMode[]
        : legacyFormat === 'audio'
          ? ['text', 'audio'] as LearningMode[]
          : legacyFormat === 'video'
            ? ['text', 'video'] as LearningMode[]
            : ['text'] as LearningMode[]);
    const studentInterests = (parsed.studentInterests ?? parsed.interests ?? defaultPreferences.studentInterests) as StudentInterest[];
    return {
      ...defaultPreferences,
      ...parsed,
      teachingLevel,
      explanationMethod,
      learningModes: learningModes.includes('text') ? learningModes : ['text', ...learningModes],
      studentInterests,
      interests: studentInterests,
    };
  } catch {
    return defaultPreferences;
  }
};

export const savePreferences = (preferences: UserPreferences): void => {
  localStorage.setItem(PREFS_KEY, JSON.stringify(preferences));
};
