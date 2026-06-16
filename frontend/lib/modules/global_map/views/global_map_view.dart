import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/global_map_controller.dart';

class GlobalMapView extends GetView<GlobalMapController> {
  const GlobalMapView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF050816),
      appBar: AppBar(
        backgroundColor: const Color(0xFF050816),
        titleSpacing: 16,
        title: Text(
          'GLOBAL MISSION MAP',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
        actions: [
          Obx(() => Container(
                margin: const EdgeInsets.only(right: 12),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.cyanDim.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.cyan.withOpacity(0.4)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.cyan,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'ACTIVE MISSIONS: ${controller.activeMissions.length}',
                      style: TextStyle(
                        color: AppColors.cyan,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
      body: Column(
        children: [
          // Canvas map
          SizedBox(
            height: 220,
            child: Obx(() => CustomPaint(
                  size: const Size(double.infinity, 220),
                  painter: _MapPainter(missions: controller.missions),
                )),
          ),

          // Divider
          Container(
            height: 1,
            color: AppColors.borderDefault,
          ),

          // Mission list
          Expanded(
            child: Obx(() => ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: controller.missions.length,
                  itemBuilder: (_, i) =>
                      _MissionCard(mission: controller.missions[i]),
                )),
          ),
        ],
      ),
    );
  }
}

// ── Map painter ───────────────────────────────────────────────────────────────

class _MapPainter extends CustomPainter {
  final List<MissionPin> missions;
  _MapPainter({required this.missions});

  @override
  void paint(Canvas canvas, Size size) {
    final bgPaint = Paint()..color = const Color(0xFF050816);
    canvas.drawRect(Offset.zero & size, bgPaint);

    // Draw subtle grid lines
    final gridPaint = Paint()
      ..color = const Color(0xFF0E1A3A)
      ..strokeWidth = 1;
    const cols = 12;
    const rows = 7;
    for (int c = 0; c <= cols; c++) {
      final x = size.width * c / cols;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (int r = 0; r <= rows; r++) {
      final y = size.height * r / rows;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Draw random ambient dots
    final rng = math.Random(42);
    final dotPaint = Paint()..color = const Color(0xFF1A2255);
    for (int i = 0; i < 60; i++) {
      final x = rng.nextDouble() * size.width;
      final y = rng.nextDouble() * size.height;
      canvas.drawCircle(Offset(x, y), rng.nextDouble() * 1.5 + 0.5, dotPaint);
    }

    // Draw mission pins with glow
    for (final m in missions) {
      final x = m.lng * size.width;
      final y = m.lat * size.height;
      final isActive = m.status == 'ACTIVE';
      final color = isActive ? const Color(0xFF22D3EE) : const Color(0xFF8B7DF8);

      // Glow ring
      final glowPaint = Paint()
        ..color = color.withOpacity(0.15)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(x, y), 18, glowPaint);

      // Mid ring
      final midPaint = Paint()
        ..color = color.withOpacity(0.3)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(x, y), 10, midPaint);

      // Core dot
      final corePaint = Paint()..color = color;
      canvas.drawCircle(Offset(x, y), 5, corePaint);
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.missions != missions;
}

// ── Mission card ──────────────────────────────────────────────────────────────

class _MissionCard extends StatelessWidget {
  final MissionPin mission;
  const _MissionCard({required this.mission});

  @override
  Widget build(BuildContext context) {
    final isClaimed = mission.status == 'CLAIMED';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isClaimed
              ? AppColors.borderDefault
              : AppColors.cyan.withOpacity(0.3),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isClaimed
                  ? AppColors.bgCardAlt
                  : AppColors.cyanDim.withOpacity(0.2),
              border: Border.all(
                color: isClaimed ? AppColors.borderDefault : AppColors.cyan,
              ),
            ),
            child: Icon(
              isClaimed ? Icons.check_circle_outline : Icons.language_outlined,
              color: isClaimed ? AppColors.textMuted : AppColors.cyan,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  mission.name,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  mission.region,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '+${mission.xp} XP',
                style: TextStyle(
                  color: AppColors.cyan,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: isClaimed
                      ? AppColors.bgCardAlt
                      : AppColors.purple.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: isClaimed
                        ? AppColors.borderDefault
                        : AppColors.purple,
                  ),
                ),
                child: Text(
                  isClaimed ? 'CLAIMED' : 'JOIN MISSION',
                  style: TextStyle(
                    color: isClaimed ? AppColors.textMuted : AppColors.purple,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
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
