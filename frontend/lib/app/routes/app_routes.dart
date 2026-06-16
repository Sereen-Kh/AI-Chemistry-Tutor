abstract final class AppRoutes {
  // ── Auth flow ──────────────────────────────────────────────────────────────
  static const splash      = '/';
  static const auth        = '/auth';
  static const onboarding  = '/onboarding';
  static const mentor      = '/mentor';

  // ── Main shell ─────────────────────────────────────────────────────────────
  static const mainNav     = '/main';

  // ── Core tabs (also accessible via routes) ─────────────────────────────────
  static const home        = '/home';
  static const lessons     = '/lessons';
  static const askAi       = '/ask-ai';
  static const schedule    = '/schedule';
  static const profile     = '/profile';
  static const flashcards  = '/flashcards';
  static const lessonDetail = '/lesson-detail';
  static const quiz        = '/quiz';
  static const studyPlan   = '/study-plan';

  // ── Tools ──────────────────────────────────────────────────────────────────
  static const virtualLab    = '/virtual-lab';
  static const periodicTable = '/periodic-table';
  static const researchLab   = '/research-lab';
  static const inventory     = '/inventory';

  // ── Games ──────────────────────────────────────────────────────────────────
  static const dailyChallenges = '/daily-challenges';
  static const bossBattle      = '/boss-battle';
  static const formulaGame     = '/formula-game';

  // ── Social / Competition ───────────────────────────────────────────────────
  static const leaderboard   = '/leaderboard';
  static const globalMap     = '/global-map';
  static const squadComms    = '/squad-comms';
  static const collaboration = '/collaboration';
  static const social        = '/social';
  static const rewards       = '/rewards';

  // ── Celebrations / overlays ────────────────────────────────────────────────
  static const rankUp           = '/rank-up';
  static const missionSuccess   = '/mission-success';
  static const missionVictory   = '/mission-victory';
  static const missionBriefing  = '/mission-briefing';
  static const synergySparks    = '/synergy-sparks';

  // ── Settings / account ─────────────────────────────────────────────────────
  static const account        = '/account';
  static const forgotPassword = '/forgot-password';
  static const resetPassword  = '/reset-password';
  static const plan    = '/plan';
  static const privacy = '/privacy';
}
