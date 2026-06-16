import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/boss_battle_controller.dart';

class BossBattleView extends GetView<BossBattleController> {
  const BossBattleView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF02040F),
      appBar: _buildAppBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // ── HP bars ───────────────────────────────────────────────
              _HpSection(controller: controller)
                  .animate()
                  .fadeIn(duration: 400.ms),

              const SizedBox(height: 20),

              // ── Boss name ─────────────────────────────────────────────
              _BossNameCard()
                  .animate()
                  .fadeIn(delay: 100.ms, duration: 400.ms)
                  .scale(
                  begin: const Offset(0.9, 0.9), end: const Offset(1, 1)),

              const SizedBox(height: 20),

              // ── Challenge card ────────────────────────────────────────
              Obx(() => _ChallengeCard(
                challenge: controller.currentChallenge.value,
                isCorrect: controller.isCorrect.value,
              )).animate().fadeIn(delay: 150.ms, duration: 400.ms),

              const SizedBox(height: 16),

              // ── Answer input ──────────────────────────────────────────
              _AnswerInput(controller: controller)
                  .animate()
                  .fadeIn(delay: 200.ms),

              const SizedBox(height: 16),

              // ── Action buttons ────────────────────────────────────────
              Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: _AttackButton(controller: controller),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: _HintButton(controller: controller),
                  ),
                ],
              ).animate().fadeIn(delay: 250.ms),

              const SizedBox(height: 20),

              // ── Bottom status row ─────────────────────────────────────
              _BottomStatus(controller: controller)
                  .animate()
                  .fadeIn(delay: 300.ms),

              const SizedBox(height: 16),

              // ── XP reward display ─────────────────────────────────────
              _XpDisplay().animate().fadeIn(delay: 350.ms),

              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF02040F),
      elevation: 0,
      leading: IconButton(
        icon: Icon(Icons.arrow_back_ios_new_rounded,
            color: AppColors.textSecondary, size: 18),
        onPressed: () => Get.back(),
      ),
      title: Text(
        'boss_battle_title'.tr,
        style: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          letterSpacing: 2.5,
        ),
      ),
      actions: [
        Obx(() => Padding(
          padding: const EdgeInsets.only(right: 14),
          child: Container(
            padding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
            decoration: BoxDecoration(
              color: controller.secondsLeft.value <= 10
                  ? AppColors.danger.withOpacity(0.15)
                  : AppColors.bgCard,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: controller.secondsLeft.value <= 10
                    ? AppColors.danger
                    : AppColors.borderDefault,
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.timer_outlined,
                    color: controller.secondsLeft.value <= 10
                        ? AppColors.danger
                        : AppColors.textSecondary,
                    size: 14),
                const SizedBox(width: 5),
                Text(
                  controller.timerLabel,
                  style: TextStyle(
                    color: controller.secondsLeft.value <= 10
                        ? AppColors.danger
                        : AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        )),
      ],
    );
  }
}

// ── HP Section ────────────────────────────────────────────────────────────────
class _HpSection extends StatelessWidget {
  final BossBattleController controller;
  const _HpSection({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Obx(() => Column(
        children: [
          _HpBar(
            label: 'boss_battle_player'.tr,
            current: controller.playerHp.value,
            max: 100,
            color: AppColors.purple,
          ),
          const SizedBox(height: 12),
          _HpBar(
            label: 'boss_battle_boss_name'.tr,
            current: controller.bossHp.value,
            max: 100,
            color: const Color(0xFFEF4444),
          ),
        ],
      )),
    );
  }
}

class _HpBar extends StatelessWidget {
  final String label;
  final int current;
  final int max;
  final Color color;

  const _HpBar({
    required this.label,
    required this.current,
    required this.max,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final fraction = (current / max).clamp(0.0, 1.0);
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 10,
                letterSpacing: 1.5,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              'boss_battle_hp'.trParams({
                'current': '$current',
                'max': '$max',
              }),
              style: TextStyle(
                color: color,
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
              height: 10,
              decoration: BoxDecoration(
                color: AppColors.bgBase,
                borderRadius: BorderRadius.circular(5),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeOut,
              height: 10,
              width: MediaQuery.of(context).size.width * fraction * 0.75,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(5),
                boxShadow: [
                  BoxShadow(color: color.withOpacity(0.5), blurRadius: 6),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// ── Boss name card ────────────────────────────────────────────────────────────
class _BossNameCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          'boss_battle_chapter_boss'.tr,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 10,
            letterSpacing: 2,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        ShaderMask(
          shaderCallback: (bounds) => LinearGradient(
            colors: [const Color(0xFFEF4444), const Color(0xFFFB923C)],
          ).createShader(bounds),
          child: Text(
            'boss_battle_boss_name'.tr,
            style: TextStyle(
              color: Colors.white,
              fontSize: 30,
              fontWeight: FontWeight.w900,
              letterSpacing: 3,
            ),
          ),
        ),
      ],
    );
  }
}

// ── Challenge card ────────────────────────────────────────────────────────────
class _ChallengeCard extends StatelessWidget {
  final String challenge;
  final bool? isCorrect;

  const _ChallengeCard({required this.challenge, required this.isCorrect});

  @override
  Widget build(BuildContext context) {
    Color borderColor = AppColors.borderDefault;
    if (isCorrect == true) borderColor = AppColors.green;
    if (isCorrect == false) borderColor = AppColors.danger;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor, width: 1.5),
        boxShadow: [
          if (isCorrect == true)
            BoxShadow(color: AppColors.green.withOpacity(0.2), blurRadius: 16),
          if (isCorrect == false)
            BoxShadow(
                color: AppColors.danger.withOpacity(0.2), blurRadius: 16),
        ],
      ),
      child: Column(
        children: [
          Text(
            'boss_battle_balance_equation'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 9,
              letterSpacing: 2,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '__ $challenge',
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              fontFamily: 'monospace',
              letterSpacing: 1,
            ),
            textAlign: TextAlign.center,
          ),
          if (isCorrect == true) ...[
            const SizedBox(height: 10),
            Text('boss_battle_correct'.tr,
                style: TextStyle(
                    color: AppColors.green,
                    fontSize: 13,
                    fontWeight: FontWeight.w800)),
          ],
          if (isCorrect == false) ...[
            const SizedBox(height: 10),
            Text('boss_battle_wrong'.tr,
                style: TextStyle(
                    color: AppColors.danger,
                    fontSize: 13,
                    fontWeight: FontWeight.w800)),
          ],
        ],
      ),
    );
  }
}

// ── Answer input ──────────────────────────────────────────────────────────────
class _AnswerInput extends StatelessWidget {
  final BossBattleController controller;
  const _AnswerInput({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: TextField(
        onChanged: controller.updateAnswer,
        style: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 15,
          fontFamily: 'monospace',
        ),
        keyboardType: TextInputType.text,
        decoration: InputDecoration(
          hintText: 'boss_battle_hint_coefficients'.tr,
          hintStyle: TextStyle(color: AppColors.textMuted, fontSize: 13),
          prefixIcon:
          Icon(Icons.edit_rounded, color: AppColors.textMuted, size: 18),
          border: InputBorder.none,
          contentPadding:
          const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
        ),
      ),
    );
  }
}

// ── Attack button ─────────────────────────────────────────────────────────────
class _AttackButton extends StatelessWidget {
  final BossBattleController controller;
  const _AttackButton({required this.controller});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: controller.submitAnswer,
      child: Container(
        height: 52,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFFEF4444), Color(0xFFDC2626)],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFEF4444).withOpacity(0.4),
              blurRadius: 14,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Text(
          'boss_battle_attack'.tr,
          style: TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }
}

// ── Hint button ───────────────────────────────────────────────────────────────
class _HintButton extends StatelessWidget {
  final BossBattleController controller;
  const _HintButton({required this.controller});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: controller.useHint,
      child: Container(
        height: 52,
        decoration: BoxDecoration(
          color: AppColors.cyan.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.cyan, width: 1.5),
        ),
        alignment: Alignment.center,
        child: Text(
          'boss_battle_hint_btn'.tr,
          style: TextStyle(
            color: AppColors.cyan,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 1,
          ),
        ),
      ),
    );
  }
}

// ── Bottom status ─────────────────────────────────────────────────────────────
class _BottomStatus extends StatelessWidget {
  final BossBattleController controller;
  const _BottomStatus({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(
          () => Row(
        children: [
          _StatusPill(
            label: 'boss_battle_combo'.tr,
            value: 'x${controller.combo.value}',
            color: AppColors.amber,
          ),
          const SizedBox(width: 10),
          _StatusPill(
            label: 'boss_battle_round'.tr,
            value:
            '${controller.round.value}/${controller.totalRounds.value}',
            color: AppColors.purple,
          ),
          const SizedBox(width: 10),
          _StatusPill(
            label: 'boss_battle_time'.tr,
            value: controller.timerLabel,
            color: controller.secondsLeft.value <= 10
                ? AppColors.danger
                : AppColors.cyan,
          ),
        ],
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  const _StatusPill(
      {required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.35)),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: TextStyle(
                color: color,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 9,
                letterSpacing: 1.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── XP display ────────────────────────────────────────────────────────────────
class _XpDisplay extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.purple.withOpacity(0.4)),
        boxShadow: [
          BoxShadow(
            color: AppColors.purple.withOpacity(0.1),
            blurRadius: 12,
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('⭐', style: TextStyle(fontSize: 18)),
          const SizedBox(width: 8),
          Text(
            'boss_battle_xp_reward'.tr,
            style: TextStyle(
              color: AppColors.amber,
              fontSize: 20,
              fontWeight: FontWeight.w900,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'boss_battle_reward_label'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
              letterSpacing: 1.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
