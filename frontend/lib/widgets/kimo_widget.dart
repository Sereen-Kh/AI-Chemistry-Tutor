import 'dart:math';
import 'package:flutter/material.dart';
import '../app/theme/app_colors.dart';

enum KimoState { happy, thinking, celebrating, concentrating }

class KimoWidget extends StatefulWidget {
  final double size;
  final KimoState state;

  const KimoWidget({super.key, this.size = 120, this.state = KimoState.happy});

  @override
  State<KimoWidget> createState() => _KimoWidgetState();
}

class _KimoWidgetState extends State<KimoWidget> with TickerProviderStateMixin {
  late final AnimationController _floatCtrl;
  late final AnimationController _glowCtrl;
  late final Animation<double> _floatAnim;
  late final Animation<double> _glowAnim;

  @override
  void initState() {
    super.initState();
    _floatCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 3))..repeat(reverse: true);
    _glowCtrl = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat(reverse: true);
    _floatAnim = Tween<double>(begin: -6, end: 6).animate(CurvedAnimation(parent: _floatCtrl, curve: Curves.easeInOut));
    _glowAnim = Tween<double>(begin: 0.55, end: 1.0).animate(CurvedAnimation(parent: _glowCtrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _floatCtrl.dispose();
    _glowCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_floatAnim, _glowAnim]),
      builder: (_, __) => Transform.translate(
        offset: Offset(0, _floatAnim.value),
        child: SizedBox(
          width: widget.size,
          height: widget.size * 1.35,
          child: CustomPaint(
            painter: _KimoPainter(state: widget.state, glow: _glowAnim.value),
          ),
        ),
      ),
    );
  }
}

class _KimoPainter extends CustomPainter {
  final KimoState state;
  final double glow;

  const _KimoPainter({required this.state, required this.glow});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height * 0.40;
    final r = size.width * 0.38;

    _drawGlow(canvas, cx, cy, r);
    _drawBody(canvas, cx, cy, r);
    _drawHighlight(canvas, cx, cy, r);
    _drawArms(canvas, cx, cy, r);
    _drawBeaker(canvas, cx, cy, r);
    _drawEyes(canvas, cx, cy, r);
    if (state == KimoState.celebrating) _drawSparkles(canvas, size, cx, cy, r);
  }

  void _drawGlow(Canvas canvas, double cx, double cy, double r) {
    canvas.drawCircle(
      Offset(cx, cy), r * 1.6,
      Paint()
        ..color = AppColors.cyan.withOpacity(0.10 * glow)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 32),
    );
    canvas.drawCircle(
      Offset(cx, cy), r * 1.2,
      Paint()
        ..color = AppColors.purple.withOpacity(0.18 * glow)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 16),
    );
  }

  void _drawBody(Canvas canvas, double cx, double cy, double r) {
    final paint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(-0.3, -0.4),
        radius: 0.85,
        colors: [const Color(0xFF1A3060), const Color(0xFF080E28)],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));
    canvas.drawCircle(Offset(cx, cy), r, paint);

    canvas.drawCircle(
      Offset(cx, cy), r,
      Paint()
        ..color = AppColors.cyan.withOpacity(0.45 * glow)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4,
    );
  }

  void _drawHighlight(Canvas canvas, double cx, double cy, double r) {
    canvas.drawCircle(
      Offset(cx - r * 0.28, cy - r * 0.32),
      r * 0.30,
      Paint()
        ..color = Colors.white.withOpacity(0.10)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
    );
  }

  void _drawEyes(Canvas canvas, double cx, double cy, double r) {
    final lx = cx - r * 0.30;
    final rx = cx + r * 0.30;
    final ey = cy - r * 0.08;

    switch (state) {
      case KimoState.happy:
        final arcPaint = Paint()
          ..color = AppColors.cyan
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.4
          ..strokeCap = StrokeCap.round;
        canvas.drawArc(Rect.fromCenter(center: Offset(lx, ey), width: r * 0.30, height: r * 0.30), pi, pi, false, arcPaint);
        canvas.drawArc(Rect.fromCenter(center: Offset(rx, ey), width: r * 0.30, height: r * 0.30), pi, pi, false, arcPaint);

      case KimoState.thinking:
        final ep = Paint()..color = AppColors.cyan..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
        canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(lx, ey), width: r * 0.26, height: r * 0.08), const Radius.circular(2)), ep);
        canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(rx, ey - r * 0.02), width: r * 0.26, height: r * 0.14), const Radius.circular(3)), ep);

      case KimoState.celebrating:
        final sp = Paint()..color = AppColors.amber..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
        canvas.drawCircle(Offset(lx, ey), r * 0.10, sp);
        canvas.drawCircle(Offset(rx, ey), r * 0.10, sp);

      case KimoState.concentrating:
        final cp = Paint()..color = AppColors.cyan.withOpacity(0.9);
        canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(lx, ey), width: r * 0.28, height: r * 0.09), const Radius.circular(2)), cp);
        canvas.drawRRect(RRect.fromRectAndRadius(Rect.fromCenter(center: Offset(rx, ey), width: r * 0.28, height: r * 0.09), const Radius.circular(2)), cp);
    }
  }

  void _drawArms(Canvas canvas, double cx, double cy, double r) {
    final border = Paint()
      ..color = AppColors.cyan.withOpacity(0.35)
      ..strokeWidth = r * 0.20
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    final fill = Paint()
      ..color = const Color(0xFF12244A)
      ..strokeWidth = r * 0.20 - 2
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final ls = Offset(cx - r * 0.72, cy + r * 0.08);
    final rs = Offset(cx + r * 0.72, cy + r * 0.08);
    late final Offset le, re;

    switch (state) {
      case KimoState.celebrating:
        le = Offset(cx - r * 1.15, cy - r * 0.82);
        re = Offset(cx + r * 1.15, cy - r * 0.82);
      case KimoState.thinking:
        le = Offset(cx - r * 1.05, cy + r * 0.38);
        re = Offset(cx + r * 0.58, cy + r * 0.52);
      default:
        le = Offset(cx - r * 1.10, cy + r * 0.22);
        re = Offset(cx + r * 1.10, cy + r * 0.22);
    }

    canvas.drawLine(ls, le, border);
    canvas.drawLine(rs, re, border);
    canvas.drawLine(ls, le, fill);
    canvas.drawLine(rs, re, fill);
  }

  void _drawBeaker(Canvas canvas, double cx, double cy, double r) {
    late final Offset tip;
    switch (state) {
      case KimoState.celebrating:
        tip = Offset(cx + r * 1.15, cy - r * 0.82);
      case KimoState.thinking:
        tip = Offset(cx + r * 0.58, cy + r * 0.52);
      default:
        tip = Offset(cx + r * 1.10, cy + r * 0.22);
    }

    final bw = r * 0.26;
    final bh = r * 0.30;
    final bx = tip.dx;
    final by = tip.dy;

    final path = Path()
      ..moveTo(bx - bw * 0.38, by - bh * 0.28)
      ..lineTo(bx - bw * 0.48, by + bh * 0.50)
      ..lineTo(bx + bw * 0.48, by + bh * 0.50)
      ..lineTo(bx + bw * 0.38, by - bh * 0.28)
      ..close();

    canvas.drawPath(path, Paint()..color = AppColors.cyan.withOpacity(0.18));
    canvas.drawPath(path, Paint()..color = AppColors.cyan.withOpacity(0.65)..style = PaintingStyle.stroke..strokeWidth = 1.6);
    canvas.drawLine(Offset(bx - bw * 0.50, by - bh * 0.28), Offset(bx + bw * 0.50, by - bh * 0.28),
        Paint()..color = AppColors.cyan.withOpacity(0.65)..strokeWidth = 1.6);

    final liquidPath = Path()
      ..moveTo(bx - bw * 0.40, by + bh * 0.12)
      ..lineTo(bx - bw * 0.48, by + bh * 0.50)
      ..lineTo(bx + bw * 0.48, by + bh * 0.50)
      ..lineTo(bx + bw * 0.40, by + bh * 0.12)
      ..close();
    canvas.drawPath(liquidPath, Paint()..color = AppColors.purple.withOpacity(0.50));

    canvas.drawCircle(Offset(bx - r * 0.04, by - r * 0.02), r * 0.035, Paint()..color = AppColors.purple.withOpacity(0.7));
    canvas.drawCircle(Offset(bx + r * 0.08, by - r * 0.06), r * 0.025, Paint()..color = AppColors.cyan.withOpacity(0.6));
  }

  void _drawSparkles(Canvas canvas, Size size, double cx, double cy, double r) {
    final sp = Paint()..color = AppColors.amber..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2);
    final pts = [
      Offset(cx - r * 1.3, cy - r * 1.1),
      Offset(cx + r * 1.4, cy - r * 0.8),
      Offset(cx - r * 0.8, cy - r * 1.5),
      Offset(cx + r * 0.9, cy - r * 1.4),
      Offset(cx - r * 1.6, cy - r * 0.3),
      Offset(cx + r * 1.5, cy + r * 0.1),
    ];
    for (final p in pts) {
      canvas.drawCircle(p, r * 0.06 * glow, sp);
    }
  }

  @override
  bool shouldRepaint(_KimoPainter old) => old.glow != glow || old.state != state;
}
