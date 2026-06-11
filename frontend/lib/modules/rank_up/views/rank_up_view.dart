import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/rank_up_controller.dart';

class RankUpView extends GetView<RankUpController> {
  const RankUpView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050816),
      body: Stack(
        children: [
          // Floating particles background
          const Positioned.fill(child: _ParticleBackground()),

          // Main content
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 24),

                    // Rank badge glow
                    Container(
                      width: 140,
                      height: 140,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.cyan.withOpacity(0.6),
                            blurRadius: 60,
                            spreadRadius: 10,
                          ),
                          BoxShadow(
                            color: AppColors.cyan.withOpacity(0.3),
                            blurRadius: 100,
                            spreadRadius: 30,
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Text(
                          '⚡',
                          style: TextStyle(fontSize: 80),
                        ),
                      ),
                    )
                        .animate()
                        .scale(
                          begin: const Offset(0.5, 0.5),
                          end: const Offset(1.0, 1.0),
                          duration: 600.ms,
                          curve: Curves.elasticOut,
                        )
                        .fadeIn(duration: 400.ms),

                    const SizedBox(height: 32),

                    // RANK UP! text
                    Text(
                      'RANK UP!',
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 42,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 4,
                      ),
                    )
                        .animate(delay: 300.ms)
                        .fadeIn(duration: 500.ms)
                        .slideY(
                          begin: 0.4,
                          end: 0,
                          duration: 500.ms,
                          curve: Curves.easeOut,
                        ),

                    const SizedBox(height: 12),

                    // Rank progression
                    Obx(
                      () => Text(
                        '${controller.previousRank.value} → ${controller.newRank.value}',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                        ),
                      ),
                    )
                        .animate(delay: 500.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.3, end: 0, duration: 400.ms),

                    const SizedBox(height: 20),

                    // XP gained
                    Obx(
                      () => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 24, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppColors.cyan.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(30),
                          border: Border.all(
                              color: AppColors.cyan.withOpacity(0.4)),
                        ),
                        child: Text(
                          '+${_formatNumber(controller.xpGained.value)} XP',
                          style: TextStyle(
                            color: AppColors.cyan,
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ),
                    )
                        .animate(delay: 700.ms)
                        .fadeIn(duration: 400.ms)
                        .scale(
                          begin: const Offset(0.8, 0.8),
                          end: const Offset(1.0, 1.0),
                          duration: 400.ms,
                          curve: Curves.easeOut,
                        ),

                    const SizedBox(height: 32),

                    // New perks card
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: AppColors.bgCard,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                            color: AppColors.cyan.withOpacity(0.3)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'NEW PERKS UNLOCKED',
                            style: TextStyle(
                              color: AppColors.cyan,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 2,
                            ),
                          ),
                          const SizedBox(height: 14),
                          ...controller.newPerks.asMap().entries.map(
                                (e) => _PerkRow(
                                  perk: e.value,
                                  delay: Duration(milliseconds: 900 + e.key * 150),
                                ),
                              ),
                        ],
                      ),
                    )
                        .animate(delay: 800.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.2, end: 0, duration: 400.ms),

                    const SizedBox(height: 36),

                    // CONTINUE button
                    SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: AppColors.gradientPurple,
                          borderRadius: BorderRadius.circular(27),
                        ),
                        child: ElevatedButton(
                          onPressed: controller.onContinue,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.transparent,
                            shadowColor: Colors.transparent,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(27),
                            ),
                          ),
                          child: Text(
                            'CONTINUE',
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 2,
                            ),
                          ),
                        ),
                      ),
                    )
                        .animate(delay: 1200.ms)
                        .fadeIn(duration: 400.ms)
                        .slideY(begin: 0.3, end: 0, duration: 400.ms),

                    const SizedBox(height: 24),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatNumber(int n) {
    if (n >= 1000) {
      return '${(n / 1000).toStringAsFixed(n % 1000 == 0 ? 0 : 1)}K';
    }
    return n.toString();
  }
}

// ── Perk row ──────────────────────────────────────────────────────────────────
class _PerkRow extends StatelessWidget {
  final String perk;
  final Duration delay;
  const _PerkRow({required this.perk, required this.delay});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 20,
            height: 20,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cyan.withOpacity(0.2),
              border: Border.all(color: AppColors.cyan.withOpacity(0.5)),
            ),
            child: Icon(Icons.check, color: AppColors.cyan, size: 12),
          ),
          const SizedBox(width: 12),
          Text(
            perk,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    ).animate(delay: delay).fadeIn(duration: 300.ms).slideX(
          begin: -0.2,
          end: 0,
          duration: 300.ms,
          curve: Curves.easeOut,
        );
  }
}

// ── Particle background ───────────────────────────────────────────────────────
class _ParticleBackground extends StatelessWidget {
  const _ParticleBackground();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _ParticlePainter());
  }
}

class _ParticlePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final rng = Random(42);
    final paintDot = Paint()..style = PaintingStyle.fill;

    final colors = [
      const Color(0xFF22D3EE).withOpacity(0.4),
      const Color(0xFF8B7DF8).withOpacity(0.3),
      const Color(0xFFFFFFFF).withOpacity(0.15),
    ];

    for (int i = 0; i < 80; i++) {
      final x = rng.nextDouble() * size.width;
      final y = rng.nextDouble() * size.height;
      final r = rng.nextDouble() * 2 + 0.5;
      paintDot.color = colors[i % colors.length];
      canvas.drawCircle(Offset(x, y), r, paintDot);
    }
  }

  @override
  bool shouldRepaint(_ParticlePainter old) => false;
}
