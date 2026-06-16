import 'package:get/get.dart';

import '../../modules/account/bindings/account_binding.dart';
import '../../modules/account/views/account_view.dart';
import '../../modules/auth/bindings/auth_binding.dart';
import '../../modules/auth/views/auth_view.dart';
import '../../modules/auth/views/forgot_password_view.dart';
import '../../modules/auth/views/reset_password_view.dart';
import '../../modules/boss_battle/bindings/boss_battle_binding.dart';
import '../../modules/boss_battle/views/boss_battle_view.dart';
import '../../modules/collaboration/bindings/collaboration_binding.dart';
import '../../modules/collaboration/views/collaboration_view.dart';
import '../../modules/daily_challenges/bindings/daily_challenges_binding.dart';
import '../../modules/daily_challenges/views/daily_challenges_view.dart';
import '../../modules/flashcards/bindings/flashcards_binding.dart';
import '../../modules/flashcards/views/flashcards_view.dart';
import '../../modules/formula_game/bindings/formula_game_binding.dart';
import '../../modules/formula_game/views/formula_game_view.dart';
import '../../modules/global_map/bindings/global_map_binding.dart';
import '../../modules/global_map/views/global_map_view.dart';
import '../../modules/home/bindings/home_binding.dart';
import '../../modules/inventory/bindings/inventory_binding.dart';
import '../../modules/inventory/views/inventory_view.dart';
import '../../modules/leaderboard/bindings/leaderboard_binding.dart';
import '../../modules/leaderboard/views/leaderboard_view.dart';
import '../../modules/lesson_detail/bindings/lesson_detail_binding.dart';
import '../../modules/lesson_detail/views/lesson_detail_view.dart';
import '../../modules/lessons/bindings/lessons_binding.dart';
import '../../modules/main_nav/bindings/main_nav_binding.dart';
import '../../modules/main_nav/views/main_nav_view.dart';
import '../../modules/mentor/bindings/mentor_binding.dart';
import '../../modules/mentor/views/mentor_view.dart';
import '../../modules/mission_briefing/bindings/mission_briefing_binding.dart';
import '../../modules/mission_briefing/views/mission_briefing_view.dart';
import '../../modules/mission_success/bindings/mission_success_binding.dart';
import '../../modules/mission_success/views/mission_success_view.dart';
import '../../modules/mission_victory/bindings/mission_victory_binding.dart';
import '../../modules/mission_victory/views/mission_victory_view.dart';
import '../../modules/onboarding/bindings/onboarding_binding.dart';
import '../../modules/onboarding/views/onboarding_view.dart';
import '../../modules/periodic_table/bindings/periodic_table_binding.dart';
import '../../modules/periodic_table/views/periodic_table_view.dart';
import '../../modules/pilot_profile/bindings/pilot_profile_binding.dart';
import '../../modules/pilot_profile/views/pilot_profile_view.dart';
import '../../modules/plan/bindings/plan_binding.dart';
import '../../modules/plan/views/plan_view.dart';
import '../../modules/privacy/bindings/privacy_binding.dart';
import '../../modules/privacy/views/privacy_view.dart';
import '../../modules/profile/bindings/profile_binding.dart';
import '../../modules/profile/views/profile_view.dart';
import '../../modules/quiz/bindings/quiz_binding.dart';
import '../../modules/quiz/views/quiz_view.dart';
import '../../modules/rank_up/bindings/rank_up_binding.dart';
import '../../modules/rank_up/views/rank_up_view.dart';
import '../../modules/research_lab/bindings/research_lab_binding.dart';
import '../../modules/research_lab/views/research_lab_view.dart';
import '../../modules/rewards/bindings/rewards_binding.dart';
import '../../modules/rewards/views/rewards_view.dart';
import '../../modules/schedule/bindings/schedule_binding.dart';
import '../../modules/schedule/views/schedule_view.dart';
import '../../modules/social/bindings/social_binding.dart';
import '../../modules/social/views/social_view.dart';
import '../../modules/splash/bindings/splash_binding.dart';
import '../../modules/splash/views/splash_view.dart';
import '../../modules/squad_comms/bindings/squad_comms_binding.dart';
import '../../modules/squad_comms/views/squad_comms_view.dart';
import '../../modules/study_plan/bindings/study_plan_binding.dart';
import '../../modules/study_plan/views/study_plan_view.dart';
import '../../modules/synergy_sparks/bindings/synergy_sparks_binding.dart';
import '../../modules/synergy_sparks/views/synergy_sparks_view.dart';
import '../../modules/virtual_lab/bindings/virtual_lab_binding.dart';
import '../../modules/virtual_lab/views/virtual_lab_view.dart';
import 'app_routes.dart';

abstract final class AppPages {
  static final routes = <GetPage>[
    GetPage(
      name: AppRoutes.splash,
      page: () => const SplashView(),
      binding: SplashBinding(),
      transition: Transition.noTransition,
    ),
    GetPage(
      name: AppRoutes.auth,
      page: () => const AuthView(),
      binding: AuthBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.onboarding,
      page: () => const OnboardingView(),
      binding: OnboardingBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.mentor,
      page: () => const MentorView(),
      binding: MentorBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 350),
    ),
    GetPage(
      name: AppRoutes.mainNav,
      page: () => const MainNavView(),
      bindings: [
        MainNavBinding(),
        HomeBinding(),
        LessonsBinding(),
        ProfileBinding(),
        ScheduleBinding(),
        PilotProfileBinding(),
      ],
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.quiz,
      page: () => const QuizView(),
      binding: QuizBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.flashcards,
      page: () => const FlashcardsView(),
      binding: FlashcardsBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.schedule,
      page: () => const ScheduleView(),
      binding: ScheduleBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.profile,
      page: () => const ProfileView(),
      binding: ProfileBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.account,
      page: () => const AccountView(),
      binding: AccountBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.forgotPassword,
      page: () => const ForgotPasswordView(),
      binding: AuthBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.resetPassword,
      page: () => const ResetPasswordView(),
      binding: AuthBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.lessonDetail,
      page: () => const LessonDetailView(),
      binding: LessonDetailBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.virtualLab,
      page: () => const VirtualLabView(),
      binding: VirtualLabBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.periodicTable,
      page: () => const PeriodicTableView(),
      binding: PeriodicTableBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.bossBattle,
      page: () => const BossBattleView(),
      binding: BossBattleBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.formulaGame,
      page: () => const FormulaGameView(),
      binding: FormulaGameBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.inventory,
      page: () => const InventoryView(),
      binding: InventoryBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.leaderboard,
      page: () => const LeaderboardView(),
      binding: LeaderboardBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.globalMap,
      page: () => const GlobalMapView(),
      binding: GlobalMapBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.squadComms,
      page: () => const SquadCommsView(),
      binding: SquadCommsBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.dailyChallenges,
      page: () => const DailyChallengesView(),
      binding: DailyChallengesBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.rewards,
      page: () => const RewardsView(),
      binding: RewardsBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.collaboration,
      page: () => const CollaborationView(),
      binding: CollaborationBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.social,
      page: () => const SocialView(),
      binding: SocialBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.rankUp,
      page: () => const RankUpView(),
      binding: RankUpBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.missionSuccess,
      page: () => const MissionSuccessView(),
      binding: MissionSuccessBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.missionVictory,
      page: () => const MissionVictoryView(),
      binding: MissionVictoryBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
    GetPage(
      name: AppRoutes.missionBriefing,
      page: () => const MissionBriefingView(),
      binding: MissionBriefingBinding(),
      transition: Transition.downToUp,
      transitionDuration: const Duration(milliseconds: 350),
    ),
    GetPage(
      name: AppRoutes.researchLab,
      page: () => const ResearchLabView(),
      binding: ResearchLabBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.studyPlan,
      page: () => const StudyPlanView(),
      binding: StudyPlanBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.plan,
      page: () => const PlanView(),
      binding: PlanBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.privacy,
      page: () => const PrivacyView(),
      binding: PrivacyBinding(),
      transition: Transition.rightToLeft,
      transitionDuration: const Duration(milliseconds: 300),
    ),
    GetPage(
      name: AppRoutes.synergySparks,
      page: () => const SynergySparkView(),
      binding: SynergySparkBinding(),
      transition: Transition.fadeIn,
      transitionDuration: const Duration(milliseconds: 400),
    ),
  ];
}
