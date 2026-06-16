import 'dart:math';
import 'dart:ui';

import 'package:flutter/material.dart';

/// Draws the CHEMAI Erlenmeyer-flask + neural-network logo.
class FlaskLogo extends StatelessWidget {
  final double size;
  const FlaskLogo({super.key, this.size = 80});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _FlaskPainter()),
    );
  }
}

class _FlaskPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;
    final cx = w / 2;

    // ── Flask path ─────────────────────────────────────────────────────────
    final neckW = w * 0.34;
    final bodyW = w * 0.84;
    final neckTop = h * 0.06;
    final neckBot = h * 0.30;
    final bodyBot = h * 0.93;
    final cornerR = w * 0.06;

    final flask = Path()
      ..moveTo(cx - neckW / 2, neckTop)
      ..lineTo(cx + neckW / 2, neckTop)
      ..lineTo(cx + neckW / 2, neckBot)
      ..quadraticBezierTo(
        cx + neckW / 2 + (bodyW - neckW) * 0.3,
        neckBot + h * 0.18,
        cx + bodyW / 2,
        bodyBot - cornerR,
      )
      ..arcToPoint(Offset(cx + bodyW / 2 - cornerR, bodyBot),
          radius: Radius.circular(cornerR), clockwise: true)
      ..lineTo(cx - bodyW / 2 + cornerR, bodyBot)
      ..arcToPoint(Offset(cx - bodyW / 2, bodyBot - cornerR),
          radius: Radius.circular(cornerR), clockwise: true)
      ..quadraticBezierTo(
        cx - neckW / 2 - (bodyW - neckW) * 0.3,
        neckBot + h * 0.18,
        cx - neckW / 2,
        neckBot,
      )
      ..lineTo(cx - neckW / 2, neckTop)
      ..close();

    // ── Gradient fill ──────────────────────────────────────────────────────
    final fillPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0x5500D4FF), Color(0xBB7C5CFC)],
      ).createShader(Rect.fromLTWH(0, 0, w, h));
    canvas.drawPath(flask, fillPaint);

    // ── Outline ────────────────────────────────────────────────────────────
    final stroke = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xFF00D4FF), Color(0xFF7C5CFC)],
      ).createShader(Rect.fromLTWH(0, 0, w, h))
      ..style = PaintingStyle.stroke
      ..strokeWidth = w * 0.045
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(flask, stroke);

    // ── Neural-network nodes inside body ───────────────────────────────────
    // Clip to flask body so nodes stay inside
    canvas.save();
    canvas.clipPath(flask);

    final nodes = _flaskNodes(cx, h, neckBot + h * 0.04, bodyBot - cornerR);
    final edges = _flaskEdges(nodes.length);

    final linePaint = Paint()
      ..color = const Color(0xFF00D4FF).withOpacity(0.55)
      ..strokeWidth = w * 0.018
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final dotPaint = Paint()
      ..color = const Color(0xFF00D4FF).withOpacity(0.90);

    for (final e in edges) {
      canvas.drawLine(nodes[e[0]], nodes[e[1]], linePaint);
    }
    for (final n in nodes) {
      canvas.drawCircle(n, w * 0.04, dotPaint);
    }

    canvas.restore();
  }

  List<Offset> _flaskNodes(double cx, double h, double top, double bot) {
    final span = bot - top;
    final dx = cx * 0.55; // relative horizontal spread inside flask body
    return [
      Offset(cx,        top + span * 0.10),
      Offset(cx - dx * 0.60, top + span * 0.28),
      Offset(cx + dx * 0.60, top + span * 0.28),
      Offset(cx - dx,   top + span * 0.52),
      Offset(cx,        top + span * 0.50),
      Offset(cx + dx,   top + span * 0.52),
      Offset(cx - dx * 0.45, top + span * 0.72),
      Offset(cx + dx * 0.45, top + span * 0.72),
      Offset(cx,        top + span * 0.88),
    ];
  }

  List<List<int>> _flaskEdges(int n) => const [
        [0, 1], [0, 2], [1, 2],
        [1, 3], [1, 4], [2, 4], [2, 5],
        [3, 4], [4, 5], [3, 6], [5, 7],
        [4, 6], [4, 7], [6, 7], [6, 8], [7, 8],
      ];

  @override
  bool shouldRepaint(_) => false;
}
