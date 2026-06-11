import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../widgets/kimo_widget.dart';
import '../controllers/synergy_sparks_controller.dart';

class SynergySparkView extends GetView<SynergySparkController> {
  const SynergySparkView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070A1C),
      body: Stack(
        children: [
          const _StarfieldBackground(),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                children: [
                  // Close button
                  Align(
                    alignment: Alignment.centerRight,
                    child: GestureDetector(
                      onTap: Get.back,
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: AppColors.bgCard,
                          shape: BoxShape.circle,
                          border: Border.all(color: AppColors.borderDefault),
                        ),
                        child: Icon(Icons.close, color: AppColors.textSecondary, size: 18),
                      ),
                    ),
                  ),

                  const SizedBox(height: 8),

                  // SYNERGY ACHIEVED badge
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      gradient: AppColors.gradientPurple,
                    ),
                    child: const Text(
                      '⚡ SYNERGY ACHIEVED',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.8,
                      ),
                    ),
                  ).animate().fadeIn(duration: 500.ms).scale(begin: const Offset(0.8, 0.8)),

                  const SizedBox(height: 20),

                  // Kimo celebrating
                  const KimoWidget(size: 130, state: KimoState.celebrating)
                      .animate()
                      .fadeIn(delay: 200.ms, duration: 600.ms)
                      .scale(begin: const Offset(0.7, 0.7)),

                  const SizedBox(height: 8),

                  // Title
                  ShaderMask(
                    shaderCallback: (b) => AppColors.gradientPurple.createShader(b),
                    child: const Text(
                      'QUANTUM SYNERGY!',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.5,
                      ),
                    ),
                  ).animate().fadeIn(delay: 350.ms, duration: 500.ms),

                  const SizedBox(height: 6),

                  Text(
                    'synergy_subtitle'.tr,
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                    textAlign: TextAlign.center,
                  ).animate().fadeIn(delay: 450.ms, duration: 500.ms),

                  const SizedBox(height: 24),

                  // Synergy score ring
                  _SynergyRing(controller: controller)
                      .animate()
                      .fadeIn(delay: 500.ms, duration: 600.ms)
                      .scale(begin: const Offset(0.8, 0.8)),

                  const SizedBox(height: 24),

                  // XP earned
                  Obx(() => Container(
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          gradient: LinearGradient(
                            colors: [
                              AppColors.amber.withOpacity(0.15),
                              AppColors.amber.withOpacity(0.05),
                            ],
                          ),
                          border: Border.all(color: AppColors.amber.withOpacity(0.35)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Text('⭐', style: TextStyle(fontSize: 22)),
                            const SizedBox(width: 10),
                            Text(
                              '+${controller.xpEarned.value} XP EARNED',
                              style: const TextStyle(
                                color: Color(0xFFFBBF24),
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ],
                        ),
                      )).animate().fadeIn(delay: 600.ms, duration: 500.ms),

                  const SizedBox(height: 20),

                  // Players row
                  _PlayersRow(controller: controller)
                      .animate()
                      .fadeIn(delay: 700.ms, duration: 500.ms)
                      .slideY(begin: 0.1),

                  const SizedBox(height: 16),

                  // Stats grid
                  _StatsGrid(controller: controller)
                      .animate()
                      .fadeIn(delay: 800.ms, duration: 500.ms)
                      .slideY(begin: 0.1),

                  const SizedBox(height: 20),

                  // Streak bonus card
                  Obx(() => Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: AppColors.bgCard,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: AppColors.green.withOpacity(0.35)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 42,
                              height: 42,
                              decoration: BoxDecoration(
                                color: AppColors.green.withOpacity(0.12),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(Icons.local_fire_department_rounded, color: AppColors.green, size: 22),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('synergy_streak_bonus'.tr, style: TextStyle(color: AppColors.textPrimary, fontSize: 13, fontWeight: FontWeight.w700)),
                                  Text('synergy_streak_desc'.tr, style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
                                ],
                              ),
                            ),
                            Text(
                              '+${controller.streakBonus.value} XP',
                              style: TextStyle(color: AppColors.green, fontSize: 15, fontWeight: FontWeight.w800),
                            ),
                          ],
                        ),
                      )).animate().fadeIn(delay: 850.ms, duration: 500.ms),

                  const SizedBox(height: 24),

                  // Action buttons
                  _ActionButtons()
                      .animate()
                      .fadeIn(delay: 950.ms, duration: 500.ms)
                      .slideY(begin: 0.1),

                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SynergyRing extends StatelessWidget {
  final SynergySparkController controller;
  const _SynergyRing({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final score = controller.synergyScore.value / 100.0;
      return SizedBox(
        width: 140,
        height: 140,
        child: Stack(
          alignment: Alignment.center,
          children: [
            CustomPaint(
              size: const Size(140, 140),
              painter: _RingPainter(progress: score),
            ),
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${controller.synergyScore.value}%',
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  'synergy_ring_label'.tr,
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 9,
                    letterSpacing: 2,
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    });
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  const _RingPainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r = size.width / 2 - 8;

    canvas.drawCircle(Offset(cx, cy), r, Paint()
      ..color = AppColors.borderDefault
      ..style = PaintingStyle.stroke
      ..strokeWidth = 10);

    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -pi / 2,
      2 * pi * progress,
      false,
      Paint()
        ..shader = LinearGradient(
          colors: [AppColors.cyan, AppColors.purple],
        ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r))
        ..style = PaintingStyle.stroke
        ..strokeWidth = 10
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.progress != progress;
}

class _PlayersRow extends StatelessWidget {
  final SynergySparkController controller;
  const _PlayersRow({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Row(
          children: [
            Expanded(child: _PlayerCard(name: controller.userName.value, accuracy: controller.userAccuracy.value, isYou: true)),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Column(
                children: [
                  Icon(Icons.flash_on_rounded, color: AppColors.amber, size: 24),
                  Text('synergy_vs'.tr, style: TextStyle(color: AppColors.textMuted, fontSize: 9, letterSpacing: 2)),
                ],
              ),
            ),
            Expanded(child: _PlayerCard(name: controller.partnerName.value, accuracy: controller.partnerAccuracy.value, isYou: false)),
          ],
        ));
  }
}

class _PlayerCard extends StatelessWidget {
  final String name;
  final int accuracy;
  final bool isYou;
  const _PlayerCard({required this.name, required this.accuracy, required this.isYou});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isYou ? AppColors.purple.withOpacity(0.5) : AppColors.cyan.withOpacity(0.3),
        ),
      ),
      child: Column(
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: isYou ? AppColors.gradientPurple : AppColors.gradientCyan,
            ),
            child: Center(
              child: Text(
                name[0],
                style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(name, style: TextStyle(color: AppColors.textPrimary, fontSize: 12, fontWeight: FontWeight.w600), textAlign: TextAlign.center),
          const SizedBox(height: 4),
          Text('$accuracy% acc', style: TextStyle(color: isYou ? AppColors.purple : AppColors.cyan, fontSize: 11, fontWeight: FontWeight.w700)),
          if (isYou)
            Container(
              margin: const EdgeInsets.only(top: 6),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: AppColors.purple.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text('synergy_you'.tr, style: TextStyle(color: AppColors.purple, fontSize: 9, fontWeight: FontWeight.w700, letterSpacing: 1)),
            ),
        ],
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  final SynergySparkController controller;
  const _StatsGrid({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Row(
          children: [
            Expanded(child: _StatBox(label: 'synergy_time'.tr, value: controller.timeTaken.value, icon: Icons.access_time, color: AppColors.cyan)),
            const SizedBox(width: 12),
            Expanded(child: _StatBox(label: 'synergy_correct'.tr, value: '${controller.correctAnswers.value}/${controller.questionsAnswered.value}', icon: Icons.check_circle_outline, color: AppColors.green)),
          ],
        ));
  }
}

class _StatBox extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;
  const _StatBox({required this.label, required this.value, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: TextStyle(color: AppColors.textMuted, fontSize: 9, letterSpacing: 1.5)),
              const SizedBox(height: 2),
              Text(value, style: TextStyle(color: AppColors.textPrimary, fontSize: 16, fontWeight: FontWeight.w700)),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButtons extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        GestureDetector(
          onTap: () {},
          child: Container(
            width: double.infinity,
            height: 52,
            decoration: BoxDecoration(
              gradient: AppColors.gradientPurple,
              borderRadius: BorderRadius.circular(30),
            ),
            alignment: Alignment.center,
            child: Text(
              'synergy_challenge_again'.tr,
              style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700),
            ),
          ),
        ),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: () {},
          child: Container(
            width: double.infinity,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(30),
              border: Border.all(color: AppColors.borderDefault),
            ),
            alignment: Alignment.center,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.share_outlined, color: AppColors.textSecondary, size: 18),
                const SizedBox(width: 8),
                Text('synergy_share_result'.tr, style: TextStyle(color: AppColors.textSecondary, fontSize: 14)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: Get.back,
          child: Text('synergy_return_base'.tr, style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
        ),
      ],
    );
  }
}

class _StarfieldBackground extends StatelessWidget {
  const _StarfieldBackground();

  @override
  Widget build(BuildContext context) {
    final rand = Random(42);
    return CustomPaint(
      size: Size.infinite,
      painter: _StarfieldPainter(rand),
    );
  }
}

class _StarfieldPainter extends CustomPainter {
  final Random rand;
  const _StarfieldPainter(this.rand);

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = Colors.white.withOpacity(0.4);
    for (int i = 0; i < 60; i++) {
      final x = rand.nextDouble() * size.width;
      final y = rand.nextDouble() * size.height;
      final r = rand.nextDouble() * 1.2 + 0.3;
      canvas.drawCircle(Offset(x, y), r, p);
    }
  }

  @override
  bool shouldRepaint(_) => false;
}
