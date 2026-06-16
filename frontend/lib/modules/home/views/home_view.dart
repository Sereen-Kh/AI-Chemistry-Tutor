import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/routes/app_routes.dart';
import '../../../app/theme/app_colors.dart';
import '../../../data/models/user_model.dart';
import '../../main_nav/controllers/main_nav_controller.dart';
import '../controllers/home_controller.dart';

class HomeView extends GetView<HomeController> {
  const HomeView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _HomeAppBar(controller: controller),
      body: Obx(() {
        final user = controller.user.value;
        if (user == null) {
          return Center(child: CircularProgressIndicator(color: AppColors.purple));
        }
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StatusRow()
                  .animate().fadeIn(duration: 300.ms),
              const SizedBox(height: 12),
              _GreetingSection(name: user.name)
                  .animate().fadeIn(delay: 80.ms, duration: 300.ms),
              const SizedBox(height: 16),

              // ── Mission Command ring card ───────────────────────────────
              _MissionCommandCard(user: user)
                  .animate().fadeIn(delay: 140.ms, duration: 400.ms).slideY(begin: 0.06),
              const SizedBox(height: 20),

              _PilotStatsCard(user: user)
                  .animate().fadeIn(delay: 200.ms, duration: 400.ms).slideY(begin: 0.08),
              const SizedBox(height: 14),
              _ActiveMissionCard()
                  .animate().fadeIn(delay: 260.ms, duration: 400.ms).slideY(begin: 0.08),
              const SizedBox(height: 22),
              _SectionHeader('home_quick_actions'.tr)
                  .animate().fadeIn(delay: 320.ms, duration: 300.ms),
              const SizedBox(height: 12),
              _QuickActionsGrid()
                  .animate().fadeIn(delay: 360.ms, duration: 400.ms),
              const SizedBox(height: 22),

              // ── Weekly activity ────────────────────────────────────────
              _WeeklyActivitySection()
                  .animate().fadeIn(delay: 400.ms, duration: 400.ms).slideY(begin: 0.06),
              const SizedBox(height: 22),

              // ── Achievements ───────────────────────────────────────────
              _AchievementsSection()
                  .animate().fadeIn(delay: 450.ms, duration: 400.ms).slideY(begin: 0.06),
              const SizedBox(height: 22),

              _SectionHeader('home_todays_intel'.tr)
                  .animate().fadeIn(delay: 500.ms, duration: 300.ms),
              const SizedBox(height: 12),
              _TodayIntelRow()
                  .animate().fadeIn(delay: 540.ms, duration: 400.ms),
              const SizedBox(height: 16),
            ],
          ),
        );
      }),
    );
  }
}

// ── AppBar ────────────────────────────────────────────────────────────────────
class _HomeAppBar extends StatelessWidget implements PreferredSizeWidget {
  final HomeController controller;
  const _HomeAppBar({required this.controller});

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      // backgroundColor: const Color(0xFF020408),
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.all(6),
        child: GestureDetector(
          onTap: () => Get.find<MainNavController>().openDrawer(),
          child: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Icon(Icons.menu_rounded, color: AppColors.textSecondary, size: 18),
          ),
        ),
      ),
      title: ShaderMask(
        shaderCallback: (bounds) => AppColors.gradientPurple.createShader(bounds),
        child: Text(
          'app_name'.tr,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      centerTitle: true,
      actions: [
        Padding(
          padding: const EdgeInsets.all(6),
          child: Obx(() {
            final avatarUrl = controller.user.value?.avatarUrl ?? '';
            return Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.bgCard,
                border: Border.all(color: AppColors.borderDefault),
                image: avatarUrl.isNotEmpty
                    ? DecorationImage(image: NetworkImage(avatarUrl), fit: BoxFit.cover)
                    : null,
              ),
              child: avatarUrl.isEmpty
                  ? Icon(Icons.notifications, color: AppColors.purple, size: 22)
                  : null,
            );
          }),
        ),
      ],
    );
  }
}

// ── Status row ────────────────────────────────────────────────────────────────
class _StatusRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: Color(0xFF22C55E),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                'home_status_online'.tr,
                style: TextStyle(
                  color: const Color(0xFF22C55E),
                  fontSize: 10,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.bolt, color: AppColors.amber, size: 13),
              const SizedBox(width: 4),
              Text(
                'home_daily_streak'.tr,
                style: TextStyle(
                  color: AppColors.amber,
                  fontSize: 10,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Greeting ──────────────────────────────────────────────────────────────────
class _GreetingSection extends StatelessWidget {
  final String name;
  const _GreetingSection({required this.name});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: TextSpan(
            children: [
              TextSpan(
                text: 'home_greeting'.tr,
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  height: 1.2,
                ),
              ),
              TextSpan(
                text: name,
                style: TextStyle(
                  color: AppColors.cyan,
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  height: 1.2,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'home_grade'.tr,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 12,
            letterSpacing: 0.4,
          ),
        ),
      ],
    );
  }
}

// ── Pilot stats card ──────────────────────────────────────────────────────────
class _PilotStatsCard extends StatelessWidget {
  final UserModel user;
  const _PilotStatsCard({required this.user});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderDefault),
        boxShadow: [
          BoxShadow(
            color: AppColors.purple.withOpacity(0.12),
            blurRadius: 24,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        children: [
          // Top row: avatar + info + level badge
          Row(
            children: [
              // Avatar
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: AppColors.gradientPurple,
                ),
                child: const Center(
                  child: Text('⚗️', style: TextStyle(fontSize: 24)),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      user.name,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'home_role'.tr,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
              // Level badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.purple.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.purple.withOpacity(0.4)),
                ),
                child: Text(
                  'LVL ${user.level}',
                  style: TextStyle(
                    color: AppColors.purple,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // XP bar
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'home_xp_progress'.tr,
                    style: TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 9,
                      letterSpacing: 1.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '${user.xp} / ${user.xpToNextLevel} XP',
                    style: TextStyle(
                      color: AppColors.cyan,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: user.progressToNextLevel,
                  minHeight: 6,
                  backgroundColor: AppColors.borderDefault,
                  valueColor: AlwaysStoppedAnimation<Color>(AppColors.cyan),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${user.xpRemaining} ${'home_xp_to_level'.tr} ${user.level + 1}',
                style: TextStyle(color: AppColors.textMuted, fontSize: 10),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Stats row
          Row(
            children: [
              _StatPill('home_streak'.tr, '7 days', AppColors.amber),
              const SizedBox(width: 8),
              _StatPill('home_accuracy'.tr, '84%', AppColors.green),
              const SizedBox(width: 8),
              _StatPill('home_total_xp'.tr, '${user.xp}', AppColors.purple),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatPill extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatPill(this.label, this.value, this.color);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.25)),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 9,
                letterSpacing: 1,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Active mission card ───────────────────────────────────────────────────────
class _ActiveMissionCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.cyan.withOpacity(0.25)),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0E2A3A), Color(0xFF081520)],
        ),
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.cyan.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: AppColors.cyan.withOpacity(0.35)),
                ),
                child: Text(
                  'home_active_protocol'.tr,
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 9,
                    letterSpacing: 1.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const Spacer(),
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Color(0xFF22C55E),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                'home_in_progress'.tr,
                style: TextStyle(
                  color: const Color(0xFF22C55E),
                  fontSize: 10,
                  letterSpacing: 1,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Text(
            'home_chapter_3'.tr,
            style: const TextStyle(
              color: Color(0xFFF0F2FF),
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'home_lesson_4'.tr,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
          ),

          const SizedBox(height: 14),

          // Progress
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'home_lesson_progress'.tr,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 9,
                  letterSpacing: 1.2,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '62%',
                style: TextStyle(
                  color: AppColors.cyan,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: 0.62,
              minHeight: 5,
              backgroundColor: AppColors.borderDefault,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.cyan),
            ),
          ),

          const SizedBox(height: 16),

          // Resume button
          GestureDetector(
            onTap: () => Get.toNamed(AppRoutes.lessonDetail),
            child: Container(
              width: double.infinity,
              height: 46,
              decoration: BoxDecoration(
                gradient: AppColors.gradientPurple,
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.purple.withOpacity(0.35),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              alignment: Alignment.center,
              child: Text(
                'home_resume_lesson'.tr,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.2,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Section header ────────────────────────────────────────────────────────────
class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 14,
          decoration: BoxDecoration(
            gradient: AppColors.gradientPurple,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 10,
            letterSpacing: 2,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

// ── Quick actions grid ────────────────────────────────────────────────────────
class _QuickActionsGrid extends StatelessWidget {
  static const _actions = [
    // _QAction(Icons.science_outlined, 'home_virtual_lab', route: AppRoutes.virtualLab),
    _QAction(Icons.grid_view_outlined, 'home_periodic_table', route: AppRoutes.periodicTable),
    // _QAction(Icons.sports_esports_outlined, 'home_boss_battle', route: AppRoutes.bossBattle),
    _QAction(Icons.style_outlined, 'home_flashcards', route: AppRoutes.flashcards),
    _QAction(Icons.bolt_outlined, 'home_challenges', route: AppRoutes.dailyChallenges),
    // _QAction(Icons.smart_toy_outlined, 'home_ai_chat', navTab: 3),
  ];

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1.1,
      ),
      itemCount: _actions.length,
      itemBuilder: (_, i) => _QuickActionItem(action: _actions[i], index: i),
    );
  }
}

class _QAction {
  final IconData icon;
  final String label;
  final String? route;
  final int? navTab;
  const _QAction(this.icon, this.label, {this.route, this.navTab});
}

class _QuickActionItem extends StatelessWidget {
  final _QAction action;
  final int index;
  const _QuickActionItem({required this.action, required this.index});

  static const _colors = [
    Color(0xFF7C3AED),
    Color(0xFF0EA5E9),
    Color(0xFFEF4444),
    Color(0xFFF59E0B),
    Color(0xFF10B981),
    Color(0xFF8B5CF6),
  ];

  void _onTap() {
    if (action.navTab != null) {
      Get.find<MainNavController>().changeTab(action.navTab!);
    } else if (action.route != null) {
      Get.toNamed(action.route!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _colors[index % _colors.length];
    return GestureDetector(
      onTap: _onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.25)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: color.withOpacity(0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(action.icon, color: color, size: 20),
            ),
            const SizedBox(height: 8),
            Text(
              action.label.tr,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 8,
                letterSpacing: 0.6,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    )
        .animate(delay: Duration(milliseconds: 50 * index))
        .fadeIn(duration: 300.ms)
        .scale(begin: const Offset(0.9, 0.9), duration: 300.ms, curve: Curves.easeOut);
  }
}

// ── Today's intel row ─────────────────────────────────────────────────────────
class _TodayIntelRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _IntelCard('home_lessons_label'.tr, '3', 'home_completed_today'.tr, Icons.book_outlined, AppColors.purple),
        const SizedBox(width: 10),
        _IntelCard('home_time_label'.tr, '42m', 'home_studied_today'.tr, Icons.timer_outlined, AppColors.cyan),
        const SizedBox(width: 10),
        _IntelCard('home_xp_earned'.tr, '+240', 'home_today'.tr, Icons.star_border_rounded, AppColors.amber),
      ],
    );
  }
}

class _IntelCard extends StatelessWidget {
  final String label;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color color;
  const _IntelCard(this.label, this.value, this.subtitle, this.icon, this.color);

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.borderDefault),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 16),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 8,
                letterSpacing: 1,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              subtitle,
              style: TextStyle(color: AppColors.textMuted, fontSize: 9),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Mission Command card ──────────────────────────────────────────────────────
class _MissionCommandCard extends StatelessWidget {
  final UserModel user;
  const _MissionCommandCard({required this.user});

  @override
  Widget build(BuildContext context) {
    final completion = user.progressToNextLevel;
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.cyan.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: AppColors.cyan.withOpacity(0.08),
            blurRadius: 24,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          // MASTER CHEMIST badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.bgCardAlt,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.military_tech_outlined, color: AppColors.cyan, size: 14),
                const SizedBox(width: 6),
                Text(
                  'home_master_chemist'.tr,
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Glowing completion ring
          SizedBox(
            width: 180,
            height: 180,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CustomPaint(
                  size: const Size(180, 180),
                  painter: _GlowRingPainter(progress: completion, color: AppColors.cyan),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${(completion * 100).toInt()}%',
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 42,
                        fontWeight: FontWeight.w900,
                        height: 1,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'home_completion'.tr,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 10,
                        letterSpacing: 2,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // XP + Streak row
          Row(
            children: [
              Expanded(
                child: Column(
                  children: [
                    Text(
                      'home_xp_earned_label'.tr,
                      style: TextStyle(color: AppColors.textMuted, fontSize: 10, letterSpacing: 1),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_fmtNum(user.xp)} XP',
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 20,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              Container(width: 1, height: 36, color: AppColors.borderDefault),
              Expanded(
                child: Column(
                  children: [
                    Text(
                      'home_current_streak'.tr,
                      style: TextStyle(color: AppColors.textMuted, fontSize: 10, letterSpacing: 1),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '14 ${'home_days'.tr}',
                      style: TextStyle(color: AppColors.cyan, fontSize: 20, fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  static String _fmtNum(int n) {
    final s = n.toString();
    if (s.length > 3) return '${s.substring(0, s.length - 3)},${s.substring(s.length - 3)}';
    return s;
  }
}

class _GlowRingPainter extends CustomPainter {
  final double progress;
  final Color color;
  const _GlowRingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2 - 14;
    const strokeW = 12.0;

    canvas.drawCircle(
      Offset(cx, cy),
      r,
      Paint()
        ..color = const Color(0xFF0D1B2A)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeW,
    );

    // Outer glow
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -pi / 2,
      2 * pi * progress,
      false,
      Paint()
        ..color = color.withOpacity(0.25)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeW + 8
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );

    // Main arc
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -pi / 2,
      2 * pi * progress,
      false,
      Paint()
        ..shader = SweepGradient(
          startAngle: -pi / 2,
          endAngle: -pi / 2 + 2 * pi * progress,
          colors: [color.withOpacity(0.6), color],
          tileMode: TileMode.clamp,
        ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r))
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeW
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_GlowRingPainter old) => old.progress != progress;
}

// ── Weekly activity bars ───────────────────────────────────────────────────────
class _WeeklyActivitySection extends StatelessWidget {
  static const _heights = [0.4, 0.6, 0.8, 1.0, 0.3, 0.25, 0.55];

  List<String> get _days => [
    'profile_mon'.tr, 'profile_tue'.tr, 'profile_wed'.tr,
    'profile_thu'.tr, 'profile_fri'.tr, 'profile_sat'.tr, 'profile_sun'.tr,
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'home_weekly_activity'.tr,
              style: TextStyle(color: AppColors.textPrimary, fontSize: 17, fontWeight: FontWeight.w700),
            ),
            Text(
              'home_last_7_days'.tr,
              style: TextStyle(color: AppColors.textMuted, fontSize: 11),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Column(
            children: [
              SizedBox(
                height: 70,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: List.generate(7, (i) {
                    final isTop = i == 3;
                    return Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: AnimatedContainer(
                          duration: Duration(milliseconds: 300 + i * 60),
                          curve: Curves.easeOut,
                          height: 70 * _heights[i],
                          decoration: BoxDecoration(
                            color: isTop
                                ? AppColors.cyan
                                : AppColors.cyan.withOpacity(0.3 + _heights[i] * 0.3),
                            borderRadius: BorderRadius.circular(6),
                            boxShadow: isTop
                                ? [BoxShadow(color: AppColors.cyan.withOpacity(0.45), blurRadius: 10)]
                                : null,
                          ),
                        ),
                      ),
                    );
                  }),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: List.generate(7, (i) => Expanded(
                  child: Text(
                    _days[i],
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: i == 3 ? AppColors.cyan : AppColors.textMuted,
                      fontSize: 9,
                      fontWeight: i == 3 ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                )),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.bolt, color: AppColors.amber, size: 14),
                  const SizedBox(width: 6),
                  Flexible(
                    child: RichText(
                      text: TextSpan(
                        children: [
                          TextSpan(
                            text: 'home_activity_insight'.tr,
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                          TextSpan(
                            text: 'profile_thu'.tr,
                            style: TextStyle(
                              color: AppColors.cyan,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: '.',
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Achievements 2×2 grid ─────────────────────────────────────────────────────
class _AchievementsSection extends StatelessWidget {
  static const _items = [
    _AchievData(Icons.grid_view_rounded,   'home_achievement_periodic',  'home_achievement_periodic_sub',  Color(0xFFFBBF24), true),
    _AchievData(Icons.science_outlined,    'home_achievement_reactant',  'home_achievement_reactant_sub',  Color(0xFF22D3EE), true),
    _AchievData(Icons.calculate_outlined,  'home_achievement_stoich',    'home_achievement_stoich_sub',    Color(0xFF8B5CF6), true),
    _AchievData(Icons.lock_outline,        'home_achievement_organic',   'home_achievement_organic_sub',   Color(0xFF475569), false),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'profile_achievements'.tr,
          style: TextStyle(color: AppColors.textPrimary, fontSize: 17, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 14),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 0.95,
          children: _items.map((a) => _AchievCard(data: a)).toList(),
        ),
      ],
    );
  }
}

class _AchievData {
  final IconData icon;
  final String titleKey;
  final String subKey;
  final Color color;
  final bool unlocked;
  const _AchievData(this.icon, this.titleKey, this.subKey, this.color, this.unlocked);
}

class _AchievCard extends StatelessWidget {
  final _AchievData data;
  const _AchievCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: data.unlocked ? data.color.withOpacity(0.3) : AppColors.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: data.color.withOpacity(data.unlocked ? 0.12 : 0.06),
              border: Border.all(color: data.color.withOpacity(data.unlocked ? 0.5 : 0.2)),
            ),
            child: Icon(data.icon, color: data.unlocked ? data.color : AppColors.textMuted, size: 24),
          ),
          const SizedBox(height: 12),
          Text(
            data.titleKey.tr,
            style: TextStyle(
              color: data.unlocked ? AppColors.textPrimary : AppColors.textMuted,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            data.subKey.tr,
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
