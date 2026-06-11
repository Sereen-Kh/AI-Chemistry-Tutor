import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/mission_victory_controller.dart';

class MissionVictoryView extends GetView<MissionVictoryController> {
  const MissionVictoryView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Radial gradient background
          Positioned.fill(
            child: DecoratedBox(
              decoration: const BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.center,
                  radius: 1.4,
                  colors: [
                    Color(0xFF1A0A3D),
                    Color(0xFF050816),
                    Color(0xFF000000),
                  ],
                  stops: [0.0, 0.6, 1.0],
                ),
              ),
            ),
          ),

          // Confetti
          const Positioned.fill(child: _ConfettiOverlay()),

          // Content
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                    horizontal: 28, vertical: 24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 20),

                    // Trophy icon
                    Container(
                      width: 130,
                      height: 130,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.amber.withOpacity(0.1),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.amber.withOpacity(0.5),
                            blurRadius: 60,
                            spreadRadius: 10,
                          ),
                          BoxShadow(
                            color: AppColors.amber.withOpacity(0.2),
                            blurRadius: 100,
                            spreadRadius: 30,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.emoji_events_rounded,
                        color: AppColors.amber,
                        size: 80,
                      ),
                    )
                        .animate()
                        .scale(
                          begin: const Offset(0.4, 0.4),
                          end: const Offset(1.0, 1.0),
                          duration: 700.ms,
                          curve: Curves.elasticOut,
                        )
                        .fadeIn(duration: 400.ms),

                    const SizedBox(height: 28),

                    // VICTORY! text
                    Text(
                      'VICTORY!',
                      style: const TextStyle(
                        color: AppColors.amber,
                        fontSize: 52,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 6,
                      ),
                    )
                        .animate(delay: 300.ms)
                        .scale(
                          begin: const Offset(0.6, 0.6),
                          end: const Offset(1.0, 1.0),
                          duration: 600.ms,
                          curve: Curves.elasticOut,
                        )
                        .fadeIn(duration: 400.ms),

                    const SizedBox(height: 12),

                    // Chapter subtitle
                    Obx(
                      () => Text(
                        'Chapter Complete: ${controller.chapterName.value}',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ).animate(delay: 500.ms).fadeIn(duration: 400.ms),

                    const SizedBox(height: 32),

                    // Achievement unlocked card
                    Obx(
                      () => Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: AppColors.amber.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                              color: AppColors.amber.withOpacity(0.35)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppColors.amber.withOpacity(0.2),
                              ),
                              child: const Center(
                                  child: Text('🏆',
                                      style: TextStyle(fontSize: 24))),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'ACHIEVEMENT UNLOCKED',
                                    style: TextStyle(
                                      color: AppColors.amber.withOpacity(0.7),
                                      fontSize: 10,
                                      letterSpacing: 1.5,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    controller.achievementName.value,
                                    style: const TextStyle(
                                      color: AppColors.amber,
                                      fontSize: 16,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    'Mastered all bond types in Chapter 2',
                                    style: TextStyle(
                                      color: AppColors.textSecondary,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                        .animate(delay: 700.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.2, end: 0, duration: 400.ms),

                    const SizedBox(height: 16),

                    // Next chapter preview
                    Obx(
                      () => Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: AppColors.bgCard,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                              color: AppColors.borderDefault),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'NEXT CHAPTER',
                              style: TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 10,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: AppColors.purple.withOpacity(0.2),
                                  ),
                                  child: Icon(Icons.science_rounded,
                                      color: AppColors.purple, size: 20),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    'Chapter 3: ${controller.nextChapterName.value}',
                                    style: TextStyle(
                                      color: AppColors.textPrimary,
                                      fontSize: 15,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                Icon(Icons.arrow_forward_ios_rounded,
                                    color: AppColors.textMuted, size: 14),
                              ],
                            ),
                          ],
                        ),
                      ),
                    )
                        .animate(delay: 900.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.2, end: 0, duration: 400.ms),

                    const SizedBox(height: 36),

                    // Buttons
                    Row(
                      children: [
                        Expanded(
                          child: SizedBox(
                            height: 52,
                            child: OutlinedButton(
                              onPressed: controller.viewRewards,
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(
                                    color: AppColors.amber.withOpacity(0.6),
                                    width: 1.5),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(26),
                                ),
                              ),
                              child: Text(
                                'VIEW REWARDS',
                                style: const TextStyle(
                                  color: AppColors.amber,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1,
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: SizedBox(
                            height: 52,
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                gradient: AppColors.gradientPurple,
                                borderRadius: BorderRadius.circular(26),
                              ),
                              child: ElevatedButton(
                                onPressed: controller.nextChapter_,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.transparent,
                                  shadowColor: Colors.transparent,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(26),
                                  ),
                                ),
                                child: Text(
                                  'NEXT CHAPTER',
                                  style: TextStyle(
                                    color: AppColors.textPrimary,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 1,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    )
                        .animate(delay: 1100.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.3, end: 0, duration: 400.ms),

                    const SizedBox(height: 28),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Confetti overlay ──────────────────────────────────────────────────────────
class _ConfettiOverlay extends StatelessWidget {
  const _ConfettiOverlay();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _ConfettiPainter());
  }
}

class _ConfettiPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final rng = Random(99);
    final colors = [
      const Color(0xFF22D3EE),
      const Color(0xFF8B7DF8),
      const Color(0xFFFBBF24),
      const Color(0xFF34D399),
    ];

    for (int i = 0; i < 100; i++) {
      final x = rng.nextDouble() * size.width;
      final y = rng.nextDouble() * size.height;
      final w = rng.nextDouble() * 7 + 3;
      final h = rng.nextDouble() * 4 + 2;
      final angle = rng.nextDouble() * pi;
      final color = colors[i % colors.length]
          .withOpacity(rng.nextDouble() * 0.5 + 0.3);

      canvas.save();
      canvas.translate(x, y);
      canvas.rotate(angle);
      canvas.drawRect(
        Rect.fromCenter(center: Offset.zero, width: w, height: h),
        Paint()..color = color,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_ConfettiPainter old) => false;
}
