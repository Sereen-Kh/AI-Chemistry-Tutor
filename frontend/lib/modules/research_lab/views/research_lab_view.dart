import 'dart:math';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/research_lab_controller.dart';

class ResearchLabView extends GetView<ResearchLabController> {
  const ResearchLabView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Row(
          children: [
            const Text('🔬', style: TextStyle(fontSize: 18)),
            const SizedBox(width: 8),
            Text(
              'RESEARCH LAB',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.8,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.more_horiz_rounded,
                color: AppColors.textSecondary, size: 22),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Active experiment card
            Obx(() => _ExperimentCard(
                  experimentId: controller.experimentId.value,
                  experimentName: controller.experimentName.value,
                  status: controller.status.value,
                )),

            const SizedBox(height: 16),

            // Collaborators
            _SectionLabel(label: 'COLLABORATORS'),
            const SizedBox(height: 10),
            _CollaboratorsRow(collaborators: controller.collaborators),

            const SizedBox(height: 20),

            // Live data graph
            _SectionLabel(label: 'LIVE DATA'),
            const SizedBox(height: 10),
            Container(
              height: 140,
              width: double.infinity,
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.borderDefault),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: CustomPaint(
                  painter: _LineChartPainter(accentColor: AppColors.cyan),
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Stat tiles
            Obx(
              () => GridView.count(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 2,
                mainAxisSpacing: 10,
                crossAxisSpacing: 10,
                childAspectRatio: 2.2,
                children: [
                  _DataTile(
                    label: 'pH',
                    value: controller.ph.value.toStringAsFixed(1),
                    unit: '',
                    color: AppColors.green,
                  ),
                  _DataTile(
                    label: 'Volume',
                    value: controller.volume.value.toStringAsFixed(1),
                    unit: 'mL',
                    color: AppColors.cyan,
                  ),
                  _DataTile(
                    label: 'Temperature',
                    value: controller.temperature.value.toStringAsFixed(0),
                    unit: '°C',
                    color: AppColors.amber,
                  ),
                  _DataTile(
                    label: 'Concentration',
                    value: controller.concentration.value.toStringAsFixed(1),
                    unit: 'M',
                    color: AppColors.purple,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Action buttons
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 46,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: AppColors.gradientCyan,
                        borderRadius: BorderRadius.circular(23),
                      ),
                      child: ElevatedButton.icon(
                        onPressed: controller.addDataPoint,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(23),
                          ),
                        ),
                        icon: Icon(Icons.add_rounded,
                            color: AppColors.bgDeep, size: 18),
                        label: Text(
                          'ADD DATA POINT',
                          style: TextStyle(
                            color: AppColors.bgDeep,
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: SizedBox(
                    height: 46,
                    child: OutlinedButton.icon(
                      onPressed: controller.generateReport,
                      style: OutlinedButton.styleFrom(
                        side: BorderSide(
                            color: AppColors.purple.withOpacity(0.5),
                            width: 1.5),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(23),
                        ),
                      ),
                      icon: Icon(Icons.description_outlined,
                          color: AppColors.purple, size: 16),
                      label: Text(
                        'GENERATE REPORT',
                        style: TextStyle(
                          color: AppColors.purple,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.8,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 24),

            // Recent activity
            _SectionLabel(label: 'RECENT ACTIVITY'),
            const SizedBox(height: 10),
            ...controller.recentActivity.map(
              (a) => _ActivityRow(action: a.action, timestamp: a.timestamp),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

// ── Experiment card ───────────────────────────────────────────────────────────
class _ExperimentCard extends StatelessWidget {
  final String experimentId;
  final String experimentName;
  final String status;
  const _ExperimentCard({
    required this.experimentId,
    required this.experimentName,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.cyan.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cyan.withOpacity(0.1),
            ),
            child: Icon(Icons.science_rounded, color: AppColors.cyan, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Experiment #$experimentId',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 11,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  experimentName,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.amber.withOpacity(0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.amber.withOpacity(0.4)),
            ),
            child: Text(
              status,
              style: const TextStyle(
                color: AppColors.amber,
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Collaborators row ─────────────────────────────────────────────────────────
class _CollaboratorsRow extends StatelessWidget {
  final List<Map<String, dynamic>> collaborators;
  const _CollaboratorsRow({required this.collaborators});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: collaborators.map((c) {
        final color = Color(c['color'] as int);
        return Padding(
          padding: const EdgeInsets.only(right: 16),
          child: Column(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color.withOpacity(0.2),
                  border: Border.all(color: color.withOpacity(0.5), width: 2),
                ),
                child: Center(
                  child: Text(
                    c['initials'] as String,
                    style: TextStyle(
                      color: color,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 5),
              Text(
                c['name'] as String,
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

// ── Line chart painter ────────────────────────────────────────────────────────
class _LineChartPainter extends CustomPainter {
  final Color accentColor;
  const _LineChartPainter({required this.accentColor});

  @override
  void paint(Canvas canvas, Size size) {
    // Grid lines
    final gridPaint = Paint()
      ..color = const Color(0xFF1E2458).withOpacity(0.6)
      ..strokeWidth = 1;
    for (int i = 1; i < 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    // Sine-wave-like chart line
    final linePaint = Paint()
      ..color = accentColor
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..color = accentColor.withOpacity(0.08)
      ..style = PaintingStyle.fill;

    const points = 60;
    final path = Path();
    final fillPath = Path();

    for (int i = 0; i <= points; i++) {
      final x = size.width * i / points;
      final t = i / points;
      final y = size.height * 0.5 +
          sin(t * 3 * pi + 0.5) * size.height * 0.25 +
          sin(t * 7 * pi) * size.height * 0.08;

      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, linePaint);

    // Dot at last point
    final lastX = size.width.toDouble();
    final lastY = size.height * 0.5 +
        sin(1.0 * 3 * pi + 0.5) * size.height * 0.25 +
        sin(1.0 * 7 * pi) * size.height * 0.08;
    canvas.drawCircle(
      Offset(lastX, lastY),
      5,
      Paint()..color = accentColor,
    );
    canvas.drawCircle(
      Offset(lastX, lastY),
      3,
      Paint()..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(_LineChartPainter old) =>
      old.accentColor != accentColor;
}

// ── Data tile ─────────────────────────────────────────────────────────────────
class _DataTile extends StatelessWidget {
  final String label;
  final String value;
  final String unit;
  final Color color;
  const _DataTile({
    required this.label,
    required this.value,
    required this.unit,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withOpacity(0.25)),
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration:
                BoxDecoration(shape: BoxShape.circle, color: color),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '$value$unit',
                  style: TextStyle(
                    color: color,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Activity row ──────────────────────────────────────────────────────────────
class _ActivityRow extends StatelessWidget {
  final String action;
  final String timestamp;
  const _ActivityRow({required this.action, required this.timestamp});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cyan,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              action,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
              ),
            ),
          ),
          Text(
            timestamp,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Section label ─────────────────────────────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String label;
  const _SectionLabel({required this.label});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: TextStyle(
        color: AppColors.textMuted,
        fontSize: 10,
        letterSpacing: 2,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}
