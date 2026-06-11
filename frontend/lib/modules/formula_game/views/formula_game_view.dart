import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/formula_game_controller.dart';

class FormulaGameView extends GetView<FormulaGameController> {
  const FormulaGameView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 12),

              // ── Score + streak row ────────────────────────────────────
              Obx(() => Row(
                    children: [
                      _ScoreBadge(score: controller.score.value),
                      const SizedBox(width: 10),
                      _StreakBadge(streak: controller.streak.value),
                    ],
                  )).animate().fadeIn(duration: 350.ms),

              const SizedBox(height: 14),

              // ── Level progress bar ────────────────────────────────────
              Obx(() => _LevelProgressBar(
                    level: controller.level.value,
                    progress: controller.levelProgress.value,
                  )).animate().fadeIn(delay: 80.ms, duration: 350.ms),

              const SizedBox(height: 18),

              // ── Challenge card ────────────────────────────────────────
              Obx(() => _ChallengeCard(
                    target: controller.currentTarget.value,
                  )).animate().fadeIn(delay: 120.ms, duration: 350.ms),

              const SizedBox(height: 18),

              // ── Formula builder area ──────────────────────────────────
              Obx(() => _FormulaBuilder(
                    formula: controller.currentFormula.value,
                    onClear: controller.clearFormula,
                    onBackspace: controller.removeLastElement,
                  )).animate().fadeIn(delay: 160.ms, duration: 350.ms),

              const Spacer(),

              // ── Element palette ───────────────────────────────────────
              _ElementPalette(controller: controller)
                  .animate()
                  .fadeIn(delay: 200.ms, duration: 350.ms)
                  .slideY(begin: 0.15, end: 0),

              const SizedBox(height: 14),

              // ── Submit button ─────────────────────────────────────────
              _SubmitButton(controller: controller)
                  .animate()
                  .fadeIn(delay: 240.ms),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppColors.bgBase,
      elevation: 0,
      leading: IconButton(
        icon: Icon(Icons.arrow_back_ios_new_rounded,
            color: AppColors.textSecondary, size: 18),
        onPressed: () => Get.back(),
      ),
      title: Row(
        children: [
          Text(
            'formula_game_title'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(width: 10),
          Obx(() => Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  gradient: AppColors.gradientPurple,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'formula_game_level_badge'
                      .trParams({'level': '${controller.level.value}'}),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

// ── Score badge ───────────────────────────────────────────────────────────────
class _ScoreBadge extends StatelessWidget {
  final int score;
  const _ScoreBadge({required this.score});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.star_rounded, color: AppColors.amber, size: 16),
          const SizedBox(width: 6),
          Text(
            _formatScore(score),
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'formula_game_pts'.tr,
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
        ],
      ),
    );
  }

  String _formatScore(int s) {
    if (s >= 1000) {
      final k = s ~/ 1000;
      final r = (s % 1000).toString().padLeft(3, '0');
      return '$k,$r';
    }
    return s.toString();
  }
}

// ── Streak badge ──────────────────────────────────────────────────────────────
class _StreakBadge extends StatelessWidget {
  final int streak;
  const _StreakBadge({required this.streak});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: streak > 0
            ? const Color(0xFFEF4444).withOpacity(0.1)
            : AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: streak > 0
              ? const Color(0xFFEF4444).withOpacity(0.4)
              : AppColors.borderDefault,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('🔥', style: TextStyle(fontSize: 14)),
          const SizedBox(width: 6),
          Text(
            streak.toString(),
            style: TextStyle(
              color: streak > 0
                  ? const Color(0xFFEF4444)
                  : AppColors.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(width: 4),
          Text(
            'formula_game_streak'.tr,
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

// ── Level progress bar ────────────────────────────────────────────────────────
class _LevelProgressBar extends StatelessWidget {
  final int level;
  final double progress;
  const _LevelProgressBar({required this.level, required this.progress});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'formula_game_level_progress'.trParams({'level': '$level'}),
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 9,
                letterSpacing: 1.5,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              '${(progress * 100).toInt()}%',
              style: TextStyle(
                color: AppColors.purple,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Stack(
          children: [
            Container(
              height: 6,
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: AppColors.borderDefault),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 500),
              curve: Curves.easeOut,
              height: 6,
              width: (MediaQuery.of(context).size.width - 36) * progress,
              decoration: BoxDecoration(
                gradient: AppColors.gradientPurple,
                borderRadius: BorderRadius.circular(3),
                boxShadow: [
                  BoxShadow(
                      color: AppColors.purple.withOpacity(0.4), blurRadius: 6),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ── Challenge card ────────────────────────────────────────────────────────────
class _ChallengeCard extends StatelessWidget {
  final String target;
  const _ChallengeCard({required this.target});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.cyan.withOpacity(0.4)),
        boxShadow: [
          BoxShadow(
              color: AppColors.cyan.withOpacity(0.06), blurRadius: 16),
        ],
      ),
      child: Column(
        children: [
          Text(
            'formula_game_build_for'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 9,
              letterSpacing: 2,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'formula_game_target_name'.tr,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            target,
            style: TextStyle(
              color: AppColors.cyan,
              fontSize: 32,
              fontWeight: FontWeight.w900,
              letterSpacing: 2,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Formula builder area ──────────────────────────────────────────────────────
class _FormulaBuilder extends StatelessWidget {
  final String formula;
  final VoidCallback onClear;
  final VoidCallback onBackspace;

  const _FormulaBuilder({
    required this.formula,
    required this.onClear,
    required this.onBackspace,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: formula.isNotEmpty
              ? AppColors.purple.withOpacity(0.5)
              : AppColors.borderDefault,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: formula.isEmpty
                ? Text(
                    'formula_game_empty_hint'.tr,
                    style: TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 14,
                      fontStyle: FontStyle.italic,
                    ),
                  )
                : Text(
                    formula,
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      fontFamily: 'monospace',
                      letterSpacing: 2,
                    ),
                  ),
          ),
          if (formula.isNotEmpty) ...[
            GestureDetector(
              onTap: onBackspace,
              child: Icon(Icons.backspace_outlined,
                  color: AppColors.textSecondary, size: 20),
            ),
            const SizedBox(width: 10),
            GestureDetector(
              onTap: onClear,
              child: Icon(Icons.close_rounded,
                  color: AppColors.danger, size: 20),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Element palette ───────────────────────────────────────────────────────────
class _ElementPalette extends StatelessWidget {
  final FormulaGameController controller;
  const _ElementPalette({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'formula_game_palette'.tr,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 9,
            letterSpacing: 1.5,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: controller.availableElements.map((el) {
            return GestureDetector(
              onTap: () => controller.addElement(el),
              child: Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.purple.withOpacity(0.5)),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.purple.withOpacity(0.12),
                      blurRadius: 8,
                    ),
                  ],
                ),
                alignment: Alignment.center,
                child: Text(
                  el,
                  style: TextStyle(
                    color: AppColors.purple,
                    fontSize: 16,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}

// ── Submit button ─────────────────────────────────────────────────────────────
class _SubmitButton extends StatelessWidget {
  final FormulaGameController controller;
  const _SubmitButton({required this.controller});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: controller.submitFormula,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          gradient: AppColors.gradientPurple,
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: AppColors.purple.withOpacity(0.35),
              blurRadius: 14,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Text(
          'formula_game_submit'.tr,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 15,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }
}
