import type { UserPreferences } from '../types';

export const TOKEN_KEY = 'edumind_access_token';
export const PREFS_KEY = 'edumind_user_preferences';

export const defaultPreferences: UserPreferences = {
  interests: ['real_life', 'experiments'],
  teachingStyle: 'real_life',
  answerFormat: 'text',
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
    return { ...defaultPreferences, ...JSON.parse(raw) };
  } catch {
    return defaultPreferences;
  }
};

export const savePreferences = (preferences: UserPreferences): void => {
  localStorage.setItem(PREFS_KEY, JSON.stringify(preferences));
};
