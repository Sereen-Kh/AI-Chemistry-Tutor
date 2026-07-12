import axios from 'axios';
import { clearToken, getToken } from '../lib/storage';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
export const AUTH_EXPIRED_EVENT = 'edumind:auth-expired';
export const AUTH_EXPIRED_MESSAGE = 'انتهت جلسة تسجيل الدخول. سجّل الدخول من جديد ثم أعد المحاولة.';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const isAuthEntryRequest = (url?: string): boolean =>
  Boolean(url && ['/auth/login', '/auth/register'].some((path) => url.startsWith(path)));

const isAuthExpiredResponse = (error: unknown): boolean =>
  axios.isAxiosError(error) && error.response?.status === 401 && !isAuthEntryRequest(error.config?.url);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isAuthExpiredResponse(error)) {
      clearToken();
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent(AUTH_EXPIRED_EVENT, {
            detail: { message: AUTH_EXPIRED_MESSAGE },
          }),
        );
      }
    }
    return Promise.reject(error);
  },
);

export const toErrorMessage = (error: unknown, fallback = 'Request failed'): string => {
  if (axios.isAxiosError(error)) {
    if (isAuthExpiredResponse(error)) {
      return AUTH_EXPIRED_MESSAGE;
    }
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message)) {
      return 'استغرق طلب الذكاء وقتاً أطول من المتوقع. جرّب إعادة المحاولة أو تضييق نطاق السؤال إلى درس محدد.';
    }
    const detail = error.response?.data?.detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg ?? JSON.stringify(item)).join(', ');
    }
    if (detail && typeof detail === 'object') {
      const payload = detail as { message?: unknown; code?: unknown };
      if (typeof payload.message === 'string') return payload.message;
      if (typeof payload.code === 'string') return payload.code;
    }
    if (typeof detail === 'string') return detail;
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return fallback;
};
