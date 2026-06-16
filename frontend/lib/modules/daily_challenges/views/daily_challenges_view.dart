import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/daily_challenges_controller.dart';

class DailyChallengesView extends GetView<DailyChallengesController> {
  const DailyChallengesView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Text(
          'DAILY CHALLENGES',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
        actions: [
          // Streak counter
          Obx(() => Container(
                margin: const EdgeInsets.only(right: 12),
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.amber.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: AppColors.amber.withOpacity(0.4)),
                ),
                child: Text(
                  '🔥 ${controller.streak.value} day streak',
                  style: TextStyle(
                    color: AppColors.amber,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              )),
        ],
      ),
      body: Column(
        children: [
          // Countdown timer
          _CountdownBanner(controller: controller),

          // Challenges list
          Expanded(
            child: Obx(() => ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  itemCount: controller.challenges.length,
                  itemBuilder: (_, i) =>
                      _ChallengeCard(challenge: controller.challenges[i]),
                )),
          ),

          // Daily bonus footer
          _DailyBonusFooter(controller: controller),
        ],
      ),
    );
  }
}

// ── Countdown banner ──────────────────────────────────────────────────────────

class _CountdownBanner extends StatelessWidget {
  final DailyChallengesController controller;
  const _CountdownBanner({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Container(
          margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.hourglass_bottom_outlined,
                  color: AppColors.textMuted, size: 14),
              const SizedBox(width: 8),
              Text(
                'RESETS IN:  ',
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 11,
                  letterSpacing: 1.5,
                ),
              ),
              Text(
                '${_pad(controller.hoursLeft.value)}:${_pad(controller.minutesLeft.value)}:${_pad(controller.secondsLeft.value)}',
                style: TextStyle(
                  color: AppColors.cyan,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 2,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ),
        ));
  }

  String _pad(int v) => v.toString().padLeft(2, '0');
}

// ── Challenge card ────────────────────────────────────────────────────────────

class _ChallengeCard extends StatelessWidget {
  final DailyChallenge challenge;
  const _ChallengeCard({required this.challenge});

  Color get _diffColor {
    switch (challenge.difficulty) {
      case 'QUICK':
        return AppColors.green;
      case 'STANDARD':
        return AppColors.cyan;
      case 'HARDCORE':
        return AppColors.danger;
      default:
        return AppColors.textMuted;
    }
  }

  IconData get _diffIcon {
    switch (challenge.difficulty) {
      case 'QUICK':
        return Icons.bolt_outlined;
      case 'STANDARD':
        return Icons.speed_outlined;
      case 'HARDCORE':
        return Icons.local_fire_department_outlined;
      default:
        return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final completed = challenge.isCompleted;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: completed
              ? AppColors.green.withOpacity(0.4)
              : AppColors.borderDefault,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              Expanded(
                child: Text(
                  challenge.title,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              // Difficulty badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: _diffColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: _diffColor.withOpacity(0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(_diffIcon, color: _diffColor, size: 11),
                    const SizedBox(width: 4),
                    Text(
                      challenge.difficulty,
                      style: TextStyle(
                        color: _diffColor,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            challenge.description,
            style: TextStyle(
                color: AppColors.textSecondary, fontSize: 12, height: 1.4),
          ),
          const SizedBox(height: 10),
          // Progress bar (0% or 100%)
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: LinearProgressIndicator(
              value: completed ? 1.0 : 0.0,
              minHeight: 4,
              backgroundColor: AppColors.bgCardAlt,
              valueColor: AlwaysStoppedAnimation(
                  completed ? AppColors.green : AppColors.bgCardAlt),
            ),
          ),
          const SizedBox(height: 10),
          // Footer row
          Row(
            children: [
              Icon(Icons.timer_outlined,
                  color: AppColors.textMuted, size: 13),
              const SizedBox(width: 4),
              Text(
                '${challenge.durationMin} min',
                style: TextStyle(
                    color: AppColors.textMuted, fontSize: 11),
              ),
              const Spacer(),
              Text(
                '+${challenge.xp} XP',
                style: TextStyle(
                  color: AppColors.amber,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 10),
              // Action button
              GestureDetector(
                onTap: completed ? null : () {},
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 7),
                  decoration: BoxDecoration(
                    gradient:
                        completed ? null : AppColors.gradientPurple,
                    color: completed ? AppColors.bgCardAlt : null,
                    borderRadius: BorderRadius.circular(10),
                    border: completed
                        ? Border.all(color: AppColors.borderDefault)
                        : null,
                  ),
                  child: Text(
                    completed ? 'COMPLETED' : 'START',
                    style: TextStyle(
                      color: completed
                          ? AppColors.textMuted
                          : Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Daily bonus footer ────────────────────────────────────────────────────────

class _DailyBonusFooter extends StatelessWidget {
  final DailyChallengesController controller;
  const _DailyBonusFooter({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final completedCount =
          controller.challenges.where((c) => c.isCompleted).length;
      return Container(
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.amber.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.amber.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Text('⭐', style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                'DAILY BONUS: Complete all 3 for 500 bonus XP!',
                style: TextStyle(
                  color: AppColors.amber,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Text(
              '$completedCount / 3',
              style: TextStyle(
                color: AppColors.amber,
                fontSize: 16,
                fontWeight: FontWeight.w900,
              ),
            ),
          ],
        ),
      );
    });
  }
}
