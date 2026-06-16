import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../app/routes/app_routes.dart';
import '../app/theme/app_colors.dart';
import '../core/controllers/language_controller.dart';
import '../core/controllers/theme_controller.dart';
import '../modules/auth/controllers/auth_controller.dart';
import '../modules/main_nav/controllers/main_nav_controller.dart';
import 'theme_picker.dart';

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: AppColors.bgDeep,
      width: 290,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _DrawerHeader(),
            const SizedBox(height: 8),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── Main navigation ──────────────────────────────
                    _SectionLabel('drawer_navigation'.tr),
                    _NavItem(Icons.home_outlined, 'drawer_home'.tr, () => _goTab(0)),
                    _NavItem(Icons.book_outlined, 'drawer_lessons'.tr, () => _goTab(1)),
                    _NavItem(Icons.video_library_outlined, 'drawer_reels'.tr, () => _goTab(2)),
                    _NavItem(Icons.smart_toy_outlined, 'drawer_chat_ai'.tr, () => _goTab(3)),
                    _NavItem(Icons.person_outline, 'drawer_profile'.tr, () => _goTab(4)),
                    _NavItem(Icons.trending_up_outlined, 'drawer_progress'.tr, () => _push(AppRoutes.profile)),
                    _NavItem(Icons.calendar_today_outlined, 'drawer_schedule'.tr, () => _push(AppRoutes.schedule)),
                    _NavItem(Icons.bar_chart_outlined, 'drawer_study_plan'.tr,
                            () => _push(AppRoutes.studyPlan)),

                    const SizedBox(height: 4),

                    // ── Tools ─────────────────────────────────────────
                    _SectionLabel('drawer_tools'.tr),
                    // _NavItem(Icons.science_outlined, 'drawer_virtual_lab'.tr,
                    //     () => _push(AppRoutes.virtualLab)),
                    _NavItem(Icons.grid_view_outlined, 'drawer_periodic_table'.tr,
                        () => _push(AppRoutes.periodicTable)),
                    // _NavItem(Icons.biotech_outlined, 'drawer_research_lab'.tr,
                    //     () => _push(AppRoutes.researchLab)),
                    // _NavItem(Icons.backpack_outlined, 'drawer_armory'.tr,
                    //     () => _push(AppRoutes.inventory)),

                    const SizedBox(height: 4),

                    // ── Games ─────────────────────────────────────────
                    _SectionLabel('drawer_games'.tr),
                    _NavItem(Icons.bolt_outlined, 'drawer_daily_challenges'.tr,
                        () => _push(AppRoutes.dailyChallenges)),
                    // _NavItem(Icons.sports_esports_outlined, 'drawer_boss_battle'.tr,
                    //     () => _push(AppRoutes.bossBattle)),
                    _NavItem(Icons.extension_outlined, 'drawer_formula_synthesis'.tr,
                        () => _push(AppRoutes.formulaGame)),
                    _NavItem(Icons.style_outlined, 'drawer_flashcards'.tr,
                        () => _push(AppRoutes.flashcards)),
                    _NavItem(Icons.quiz_outlined, 'drawer_daily_quiz'.tr,
                        () => _push(AppRoutes.quiz)),

                    const SizedBox(height: 4),

                    // ── Social ────────────────────────────────────────
                    // _SectionLabel('drawer_social'.tr),
                    // _NavItem(Icons.emoji_events_outlined, 'drawer_leaderboard'.tr,
                    //     () => _push(AppRoutes.leaderboard)),
                    // _NavItem(Icons.map_outlined, 'drawer_global_map'.tr,
                    //     () => _push(AppRoutes.globalMap)),
                    // _NavItem(Icons.group_outlined, 'drawer_squad_comms'.tr,
                    //     () => _push(AppRoutes.squadComms)),
                    // _NavItem(Icons.handshake_outlined, 'drawer_collaboration'.tr,
                    //     () => _push(AppRoutes.collaboration)),
                    // // _NavItem(Icons.share_outlined, 'drawer_social_showcase'.tr,
                    // //     () => _push(AppRoutes.social)),
                    // _NavItem(Icons.flash_on_outlined, 'drawer_synergy_sparks'.tr,
                    //     () => _push(AppRoutes.synergySparks)),
                    //
                    // const SizedBox(height: 4),

                    // ── Plan & Account ────────────────────────────────
                    _SectionLabel('drawer_plan_account'.tr),
                    _PlanCard(),
                    const SizedBox(height: 8),
                    _NavItem(Icons.workspace_premium_outlined, 'drawer_upgrade'.tr,
                        () => _push(AppRoutes.plan)),
                    _NavItem(Icons.card_giftcard_outlined, 'drawer_rewards'.tr,
                        () => _push(AppRoutes.rewards)),
                    _NavItem(Icons.bar_chart_outlined, 'drawer_study_plan'.tr,
                        () => _push(AppRoutes.studyPlan)),

                    const SizedBox(height: 4),

                    // ── Settings ──────────────────────────────────────
                    _SectionLabel('drawer_settings'.tr),
                    _NavItem(Icons.manage_accounts_outlined, 'drawer_account'.tr,
                        () => _push(AppRoutes.account)),
                    _NavItem(Icons.palette_outlined, 'drawer_theme'.tr,
                        () { Get.back(); ThemePicker.show(); }),
                    _LanguageToggleItem(),
                    _NavItem(Icons.shield_outlined, 'drawer_privacy'.tr,
                        () => _push(AppRoutes.privacy)),
                    _NavItem(Icons.notifications_outlined, 'drawer_notifications'.tr,
                        () {}),
                    _NavItem(Icons.help_outline_rounded, 'drawer_support'.tr, () {}),

                    // const SizedBox(height: 16),

                    // ── Disconnect ────────────────────────────────────
                    // _DisconnectButton(),
                    //
                    // const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _goTab(int index) {
    Get.back(); // close drawer
    try {
      Get.find<MainNavController>().changeTab(index);
    } catch (_) {
      Get.offAllNamed(AppRoutes.mainNav);
    }
  }

  void _push(String route) {
    Get.back();
    Get.toNamed(route);
  }
}

// ── Drawer header ─────────────────────────────────────────────────────────────
class _DrawerHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppColors.borderDefault),
        ),
      ),
      child: Row(
        children: [
          // App logo / avatar
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: AppColors.gradientPurple,
              boxShadow: [
                BoxShadow(
                  color: AppColors.purple.withOpacity(0.4),
                  blurRadius: 12,
                ),
              ],
            ),
            child: const Center(
              child: Text('⚗️', style: TextStyle(fontSize: 22)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'CHEMAI',
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2,
                  ),
                ),
                Text(
                  'drawer_quantum_engine'.tr,
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                    letterSpacing: 1.2,
                  ),
                ),
              ],
            ),
          ),
          GestureDetector(
            onTap: () => Get.back(),
            child: Icon(Icons.close, color: AppColors.textMuted, size: 20),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 300.ms);
  }
}

// ── Section label ─────────────────────────────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 16, 0, 6),
      child: Text(
        text,
        style: TextStyle(
          color: AppColors.textMuted,
          fontSize: 9,
          letterSpacing: 2,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

// ── Navigation item ───────────────────────────────────────────────────────────
class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _NavItem(this.icon, this.label, this.onTap);

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          child: Row(
            children: [
              Icon(icon, color: AppColors.textSecondary, size: 18),
              const SizedBox(width: 14),
              Text(
                label,
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 14,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Language toggle item ──────────────────────────────────────────────────────
class _LanguageToggleItem extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final lc = Get.find<LanguageController>();
    return Obx(() => Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: lc.toggleLanguage,
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
              child: Row(
                children: [
                  Icon(Icons.language_outlined,
                      color: AppColors.textSecondary, size: 18),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      'drawer_language'.tr,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.purple.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.purple.withOpacity(0.35)),
                    ),
                    child: Text(
                      lc.isArabic ? 'EN' : 'ع',
                      style: TextStyle(
                        color: AppColors.purple,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ));
  }
}

// ── Plan card ─────────────────────────────────────────────────────────────────
class _PlanCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFFFBBF24).withOpacity(0.4),
        ),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.bgCard,
            const Color(0xFFFBBF24).withOpacity(0.05),
          ],
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.workspace_premium_rounded,
              color: Color(0xFFFBBF24), size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'drawer_chemai_pro'.tr,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'drawer_elite_access'.tr,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Disconnect button ─────────────────────────────────────────────────────────
class _DisconnectButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Get.back();
        Get.find<AuthController>().logout();
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.danger.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.danger.withOpacity(0.35)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.logout_rounded, color: AppColors.danger, size: 18),
            const SizedBox(width: 10),
            Text(
              'drawer_disconnect'.tr,
              style: TextStyle(
                color: AppColors.danger,
                fontSize: 12,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
