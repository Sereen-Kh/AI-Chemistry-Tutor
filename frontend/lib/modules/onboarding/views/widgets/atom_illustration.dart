import 'dart:math';
import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';

/// Animated orbital atom illustration matching the Figma onboarding screen.
class AtomIllustration extends StatefulWidget {
  final double size;
  const AtomIllustration({super.key, this.size = 280});

  @override
  State<AtomIllustration> createState() => _AtomIllustrationState();
}

class _AtomIllustrationState extends State<AtomIllustration>
    with TickerProviderStateMixin {
  late final AnimationController _orbit1;
  late final AnimationController _orbit2;
  late final AnimationController _orbit3;
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _orbit1 = AnimationController(
        vsync: this, duration: const Duration(seconds: 6))
      ..repeat();
    _orbit2 = AnimationController(
        vsync: this, duration: const Duration(seconds: 9))
      ..repeat();
    _orbit3 = AnimationController(
        vsync: this, duration: const Duration(seconds: 12))
      ..repeat(reverse: true);
    _pulse = AnimationController(
        vsync: this, duration: const Duration(seconds: 2))
      ..repeat(reverse: true);
  }

  @override
  void dispose() {
    _orbit1.dispose();
    _orbit2.dispose();
    _orbit3.dispose();
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.size;
    return SizedBox(
      width: s,
      height: s,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Outer glow background
          AnimatedBuilder(
            animation: _pulse,
            builder: (_, __) => Container(
              width: s * 0.55,
              height: s * 0.55,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.purple
                        .withOpacity(0.15 + _pulse.value * 0.10),
                    blurRadius: 60 + _pulse.value * 20,
                    spreadRadius: 20 + _pulse.value * 10,
                  ),
                  BoxShadow(
                    color: AppColors.cyan
                        .withOpacity(0.10 + _pulse.value * 0.05),
                    blurRadius: 80,
                    spreadRadius: 30,
                  ),
                ],
              ),
            ),
          ),

          // Orbital ellipses (static rings)
          CustomPaint(
            size: Size(s, s),
            painter: _OrbitalRingsPainter(),
          ),

          // Rotating electrons
          AnimatedBuilder(
            animation: _orbit1,
            builder: (_, __) => _Electron(
              size: s,
              angle: _orbit1.value * 2 * pi,
              radiusX: s * 0.38,
              radiusY: s * 0.18,
              rotation: 0,
              color: AppColors.cyan,
            ),
          ),
          AnimatedBuilder(
            animation: _orbit2,
            builder: (_, __) => _Electron(
              size: s,
              angle: _orbit2.value * 2 * pi,
              radiusX: s * 0.38,
              radiusY: s * 0.18,
              rotation: pi / 3,
              color: AppColors.purple,
            ),
          ),
          AnimatedBuilder(
            animation: _orbit3,
            builder: (_, __) => _Electron(
              size: s,
              angle: _orbit3.value * 2 * pi,
              radiusX: s * 0.38,
              radiusY: s * 0.18,
              rotation: -pi / 3,
              color: AppColors.warning,
              electronSize: 8,
            ),
          ),

          // Nucleus
          AnimatedBuilder(
            animation: _pulse,
            builder: (_, __) => Container(
              width: s * 0.22,
              height: s * 0.22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Colors.white,
                    AppColors.purple.withOpacity(0.9),
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.white.withOpacity(0.6 + _pulse.value * 0.2),
                    blurRadius: 20 + _pulse.value * 10,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),

          // Secondary nucleus orb (purple)
          Positioned(
            left: s * 0.32,
            top: s * 0.38,
            child: Container(
              width: 16,
              height: 16,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFFE040FB),
                boxShadow: [
                  BoxShadow(
                    color: Color(0xFFE040FB),
                    blurRadius: 10,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OrbitalRingsPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;

    final paint = Paint()
      ..color = Colors.white.withOpacity(0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    void drawEllipse(double rx, double ry, double angle) {
      canvas.save();
      canvas.translate(cx, cy);
      canvas.rotate(angle);
      canvas.drawOval(
          Rect.fromCenter(center: Offset.zero, width: rx * 2, height: ry * 2),
          paint);
      canvas.restore();
    }

    // Cyan ring
    paint.color = AppColors.cyan.withOpacity(0.30);
    paint.strokeWidth = 1.2;
    drawEllipse(size.width * 0.38, size.height * 0.18, 0);

    // Purple ring
    paint.color = AppColors.purple.withOpacity(0.30);
    drawEllipse(size.width * 0.38, size.height * 0.18, pi / 3);

    // White dim ring
    paint.color = Colors.white.withOpacity(0.10);
    paint.strokeWidth = 0.8;
    drawEllipse(size.width * 0.38, size.height * 0.18, -pi / 3);

    // Outer halo
    paint.color = Colors.white.withOpacity(0.06);
    drawEllipse(size.width * 0.46, size.height * 0.46, 0);
  }

  @override
  bool shouldRepaint(_) => false;
}

class _Electron extends StatelessWidget {
  final double size;
  final double angle;
  final double radiusX;
  final double radiusY;
  final double rotation;
  final Color color;
  final double electronSize;

  const _Electron({
    required this.size,
    required this.angle,
    required this.radiusX,
    required this.radiusY,
    required this.rotation,
    required this.color,
    this.electronSize = 10,
  });

  @override
  Widget build(BuildContext context) {
    // Parametric ellipse position with orbital tilt
    final cosA = cos(angle);
    final sinA = sin(angle);
    final cosR = cos(rotation);
    final sinR = sin(rotation);

    final px = cosA * radiusX;
    final py = sinA * radiusY;

    final x = px * cosR - py * sinR;
    final y = px * sinR + py * cosR;

    return Positioned(
      left: size / 2 + x - electronSize / 2,
      top: size / 2 + y - electronSize / 2,
      child: Container(
        width: electronSize,
        height: electronSize,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
          boxShadow: [
            BoxShadow(color: color, blurRadius: 8, spreadRadius: 2),
          ],
        ),
      ),
    );
  }
}
