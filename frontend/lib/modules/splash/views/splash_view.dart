import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../widgets/kimo_widget.dart';
import '../controllers/splash_controller.dart';

class SplashView extends GetView<SplashController> {
  const SplashView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070A1C),
      body: Stack(
        children: [
          // Radial purple/cyan background glow
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.2),
                  radius: 0.85,
                  colors: [
                    AppColors.purple.withOpacity(0.18),
                    AppColors.cyan.withOpacity(0.06),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.5, 1.0],
                ),
              ),
            ),
          ),

          // Starfield
          const Positioned.fill(child: _Starfield()),

          Column(
            children: [
              // ── Top spacer + Kimo ──────────────────────────────────────
              Expanded(
                flex: 60,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Kimo mascot
                      const KimoWidget(size: 150, state: KimoState.happy)
                          .animate()
                          .fadeIn(duration: 800.ms)
                          .scale(
                            begin: const Offset(0.7, 0.7),
                            duration: 800.ms,
                            curve: Curves.easeOutBack,
                          ),

                      const SizedBox(height: 28),

                      // CHEMAI wordmark with gradient
                      ShaderMask(
                        shaderCallback: (b) => AppColors.gradientPurple.createShader(b),
                        child: const Text(
                          'CHEMAI',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 34,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 8,
                          ),
                        ),
                      ).animate().fadeIn(delay: 300.ms, duration: 600.ms),

                      const SizedBox(height: 10),

                      // Tagline
                      Text(
                        'splash_tagline'.tr,
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 13,
                          letterSpacing: 1.5,
                        ),
                      ).animate().fadeIn(delay: 500.ms, duration: 600.ms),

                      const SizedBox(height: 6),

                      // Speech bubble from Kimo
                      Container(
                        margin: const EdgeInsets.only(top: 16),
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                        decoration: BoxDecoration(
                          color: AppColors.bgCard,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: AppColors.cyan.withOpacity(0.35)),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.cyan.withOpacity(0.12),
                              blurRadius: 16,
                            ),
                          ],
                        ),
                        child: Text(
                          'splash_kimo_greeting'.tr,
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ).animate().fadeIn(delay: 700.ms, duration: 500.ms).slideY(begin: 0.2),
                    ],
                  ),
                ),
              ),

              // ── Loading section ────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 48),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Obx(() => _NeuralProgressBar(value: controller.progress.value))
                        .animate()
                        .fadeIn(delay: 900.ms, duration: 500.ms),

                    const SizedBox(height: 8),

                    Obx(() => Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              controller.statusText.value,
                              style: TextStyle(
                                color: AppColors.cyan,
                                fontSize: 9,
                                letterSpacing: 1.2,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            Text(
                              '${(controller.progress.value * 100).toInt()}%',
                              style: TextStyle(
                                color: AppColors.cyan,
                                fontSize: 9,
                                letterSpacing: 1,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        )).animate().fadeIn(delay: 900.ms),
                  ],
                ),
              ),

              // ── Version footer ─────────────────────────────────────────
              Expanded(
                flex: 12,
                child: Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 24),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.science_outlined, color: AppColors.textMuted, size: 11),
                        const SizedBox(width: 6),
                        Text(
                          'splash_version'.tr,
                          style: TextStyle(
                            color: AppColors.textMuted,
                            fontSize: 9,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ],
                    ).animate().fadeIn(delay: 1000.ms),
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

// ── Starfield ──────────────────────────────────────────────────────────────────
class _Starfield extends StatelessWidget {
  const _Starfield();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _StarfieldPainter());
  }
}

class _StarfieldPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withOpacity(0.45);
    final pts = [
      const Offset(0.12, 0.08), const Offset(0.85, 0.05), const Offset(0.45, 0.12),
      const Offset(0.72, 0.18), const Offset(0.25, 0.22), const Offset(0.92, 0.30),
      const Offset(0.08, 0.40), const Offset(0.60, 0.35), const Offset(0.35, 0.50),
      const Offset(0.78, 0.55), const Offset(0.15, 0.65), const Offset(0.50, 0.70),
      const Offset(0.90, 0.72), const Offset(0.30, 0.80), const Offset(0.65, 0.88),
      const Offset(0.05, 0.92), const Offset(0.55, 0.95), const Offset(0.80, 0.90),
    ];
    for (int i = 0; i < pts.length; i++) {
      final r = (i % 3 == 0) ? 1.4 : (i % 3 == 1) ? 0.9 : 0.5;
      canvas.drawCircle(Offset(pts[i].dx * size.width, pts[i].dy * size.height), r, paint);
    }
  }

  @override
  bool shouldRepaint(_) => false;
}

// ── Progress bar ────────────────────────────────────────────────────────────────
class _NeuralProgressBar extends StatelessWidget {
  final double value;
  const _NeuralProgressBar({required this.value});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (_, constraints) {
      return Container(
        height: 3,
        width: constraints.maxWidth,
        decoration: BoxDecoration(
          color: AppColors.borderDefault,
          borderRadius: BorderRadius.circular(2),
        ),
        child: Align(
          alignment: Alignment.centerLeft,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 80),
            width: constraints.maxWidth * value.clamp(0.0, 1.0),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(2),
              gradient: LinearGradient(colors: [AppColors.cyan, AppColors.purple]),
              boxShadow: [
                BoxShadow(
                  color: AppColors.cyan.withOpacity(0.6),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}
