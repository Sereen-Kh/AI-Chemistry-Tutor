abstract final class ApiConstants {
  static const baseUrl        = 'https://3eab-5-0-124-221.ngrok-free.app';
  static const connectTimeout = Duration(seconds: 15);
  static const receiveTimeout = Duration(seconds: 30);

  // ── Auth ───────────────────────────────────────────────────────────────────
  static const login          = '/auth/login';
  static const register       = '/auth/register';
  static const logout         = '/auth/logout';
  static const account        = '/auth/account';
  static const refresh        = '/auth/refresh';
  static const changePassword = '/auth/change-password';
  static const updateProfile  = '/auth/profile';
  static const forgotPassword = '/auth/forgot-password';
  static const resetPassword  = '/auth/reset-password';

  // ── User ───────────────────────────────────────────────────────────────────
  static const profile  = '/user/profile';
  static const progress = '/user/progress';

  // ── Content ────────────────────────────────────────────────────────────────
  static const chapters = '/chapters';
  static const lessons  = '/lessons';
  static const mentors  = '/mentors';

  // ── AI ─────────────────────────────────────────────────────────────────────
  static const askAi = '/ai/chat';
}
