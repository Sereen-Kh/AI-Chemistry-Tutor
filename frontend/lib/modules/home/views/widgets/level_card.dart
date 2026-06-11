import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../data/models/user_model.dart';

class LevelCard extends StatelessWidget {
  final UserModel user;
  const LevelCard({super.key, required this.user});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      padding:  EdgeInsets.all(20),
      child: Column(
        children: [
          // Level ring
          SizedBox(
            width: 110,
            height: 110,
            child: CustomPaint(
              painter: _RingPainter(progress: user.progressToNextLevel),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                     Text(
                      'Level',
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 11),
                    ),
                    Text(
                      '${user.level}',
                      style:  TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 32,
                        fontWeight: FontWeight.w800,
                        height: 1,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
              .animate()
              .fadeIn(duration: 500.ms)
              .scale(begin:  Offset(0.8, 0.8), duration: 600.ms,
                  curve: Curves.elasticOut),

           SizedBox(height: 14),

          Text(
            '${(user.progressToNextLevel * 100).toInt()}% to next XP Milestone',
            style:  TextStyle(
              color: AppColors.textPrimary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),

           SizedBox(height: 4),

          Text(
            '${user.xpRemaining} XP remaining for Level ${user.level + 1}',
            style:  TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  const _RingPainter({required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final radius = size.width / 2 - 8;
    const strokeW = 7.0;

    // Track
    canvas.drawCircle(
      Offset(cx, cy),
      radius,
      Paint()
        ..color = AppColors.borderDefault
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeW,
    );

    // Filled arc
    final arcPaint = Paint()
      ..shader =  SweepGradient(
        colors: [AppColors.purple, AppColors.cyan],
        startAngle: 0,
        endAngle: 2 * pi,
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeW
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: radius),
      -pi / 2,
      2 * pi * progress,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.progress != progress;
}
