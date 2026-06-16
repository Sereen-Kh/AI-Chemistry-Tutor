import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/mission_briefing_controller.dart';

class MissionBriefingView extends GetView<MissionBriefingController> {
  const MissionBriefingView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgDeep.withOpacity(0.95),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                    color: AppColors.cyan.withOpacity(0.3), width: 1.5),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.cyan.withOpacity(0.08),
                    blurRadius: 40,
                    spreadRadius: 5,
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Container(
                    padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
                    decoration: BoxDecoration(
                      color: AppColors.cyan.withOpacity(0.06),
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(23),
                        topRight: Radius.circular(23),
                      ),
                      border: Border(
                        bottom: BorderSide(
                            color: AppColors.borderDefault),
                      ),
                    ),
                    child: Row(
                      children: [
                        const Text('⚗️', style: TextStyle(fontSize: 22)),
                        const SizedBox(width: 10),
                        Text(
                          'MISSION BRIEFING',
                          style: TextStyle(
                            color: AppColors.cyan,
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 2,
                          ),
                        ),
                      ],
                    ),
                  ),

                  Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Difficulty + title
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Obx(
                                () => Text(
                                  'Stoichiometry Challenge:\n${controller.missionTitle.value}',
                                  style: TextStyle(
                                    color: AppColors.textPrimary,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800,
                                    height: 1.3,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Obx(
                              () => Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 5),
                                decoration: BoxDecoration(
                                  color: AppColors.danger.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                      color: AppColors.danger.withOpacity(0.4)),
                                ),
                                child: Text(
                                  controller.difficulty.value,
                                  style: TextStyle(
                                    color: AppColors.danger,
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 1.5,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 24),

                        // Objectives
                        Text(
                          'OBJECTIVES',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                            letterSpacing: 2,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        ...controller.objectives.asMap().entries.map(
                              (e) => _ObjectiveRow(
                                objective: e.value,
                                index: e.key + 1,
                              ),
                            ),

                        const SizedBox(height: 24),

                        // Time limit
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                          decoration: BoxDecoration(
                            color: AppColors.purple.withOpacity(0.08),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: AppColors.purple.withOpacity(0.25)),
                          ),
                          child: Obx(
                            () => Row(
                              children: [
                                const Text('⏱',
                                    style: TextStyle(fontSize: 18)),
                                const SizedBox(width: 10),
                                Text(
                                  'Time Limit:',
                                  style: TextStyle(
                                    color: AppColors.textSecondary,
                                    fontSize: 13,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  '${controller.timeMinutes.value.toString().padLeft(2, '0')}:00',
                                  style: TextStyle(
                                    color: AppColors.textPrimary,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),

                        const SizedBox(height: 24),

                        // Rewards
                        Text(
                          'REWARDS',
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 10,
                            letterSpacing: 2,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Obx(
                          () => Row(
                            children: [
                              _RewardChip(
                                icon: Icons.bolt_rounded,
                                color: AppColors.amber,
                                label: '+${controller.xpReward.value} XP',
                              ),
                              const SizedBox(width: 10),
                              _RewardChip(
                                icon: Icons.diamond_rounded,
                                color: AppColors.cyan,
                                label:
                                    '+${controller.crystalReward.value} Crystals',
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 32),

                        // Accept button
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              gradient: AppColors.gradientPurple,
                              borderRadius: BorderRadius.circular(26),
                            ),
                            child: ElevatedButton(
                              onPressed: controller.accept,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.transparent,
                                shadowColor: Colors.transparent,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(26),
                                ),
                              ),
                              child: Text(
                                'ACCEPT MISSION',
                                style: TextStyle(
                                  color: AppColors.textPrimary,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1.5,
                                ),
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 8),

                        // Skip button
                        Center(
                          child: TextButton(
                            onPressed: controller.skip,
                            child: Text(
                              'SKIP',
                              style: TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                letterSpacing: 1,
                              ),
                            ),
                          ),
                        ),

                        const SizedBox(height: 4),
                      ],
                    ),
                  ),
                ],
              ),
            )
                .animate()
                .scale(
                  begin: const Offset(0.92, 0.92),
                  end: const Offset(1.0, 1.0),
                  duration: 350.ms,
                  curve: Curves.easeOut,
                )
                .fadeIn(duration: 300.ms),
          ),
        ),
      ),
    );
  }
}

// ── Objective row ─────────────────────────────────────────────────────────────
class _ObjectiveRow extends StatelessWidget {
  final String objective;
  final int index;
  const _ObjectiveRow({required this.objective, required this.index});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cyan.withOpacity(0.2),
            ),
            child: Center(
              child: Container(
                width: 7,
                height: 7,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.cyan,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              objective,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Reward chip ───────────────────────────────────────────────────────────────
class _RewardChip extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  const _RewardChip(
      {required this.icon, required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 16),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
