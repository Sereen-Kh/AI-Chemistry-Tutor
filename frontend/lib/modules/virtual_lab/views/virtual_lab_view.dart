import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/virtual_lab_controller.dart';

class VirtualLabView extends GetView<VirtualLabController> {
  const VirtualLabView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: Stack(
        children: [
          Column(
            children: [
              // ── Molecular canvas ──────────────────────────────────────
              Expanded(
                child: Obx(() => _MolecularCanvas(
                      isSimulating: controller.isSimulating.value,
                      compound: controller.selectedCompound.value,
                    )),
              ),

              // ── Status bar ────────────────────────────────────────────
              Obx(() => _StatusBar(
                    molecules: controller.moleculeCount.value,
                    bonds: controller.bondCount.value,
                    energy: controller.energyLevel.value,
                  )).animate().fadeIn(duration: 400.ms),

              // ── Bottom panel ──────────────────────────────────────────
              _BottomPanel(controller: controller),
            ],
          ),

          // ── LAB MODE badge ────────────────────────────────────────────
          Positioned(
            top: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.purple.withOpacity(0.6)),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.purple.withOpacity(0.25),
                    blurRadius: 12,
                  ),
                ],
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('⚗️', style: TextStyle(fontSize: 13)),
                  const SizedBox(width: 6),
                  Text(
                    'virtual_lab_mode_badge'.tr,
                    style: TextStyle(
                      color: AppColors.purple,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ).animate().fadeIn(delay: 300.ms).slideX(begin: 0.2, end: 0),
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppColors.bgBase,
      elevation: 0,
      leading: IconButton(
        icon: Icon(Icons.arrow_back_ios_new_rounded,
            color: AppColors.textSecondary, size: 18),
        onPressed: () => Get.back(),
      ),
      title: Text(
        'virtual_lab_title'.tr,
        style: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          letterSpacing: 2.5,
        ),
      ),
      actions: [
        IconButton(
          icon: Icon(Icons.tune_rounded,
              color: AppColors.textSecondary, size: 20),
          onPressed: () {},
        ),
      ],
    );
  }
}

// ── Molecular canvas ──────────────────────────────────────────────────────────
class _MolecularCanvas extends StatefulWidget {
  final bool isSimulating;
  final String compound;

  const _MolecularCanvas({
    required this.isSimulating,
    required this.compound,
  });

  @override
  State<_MolecularCanvas> createState() => _MolecularCanvasState();
}

class _MolecularCanvasState extends State<_MolecularCanvas>
    with SingleTickerProviderStateMixin {
  late final AnimationController _anim;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();
  }

  @override
  void dispose() {
    _anim.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: const Color(0xFF050816),
      child: AnimatedBuilder(
        animation: _anim,
        builder: (_, __) => CustomPaint(
          size: Size.infinite,
          painter: _MolecularPainter(
            progress: _anim.value,
            isAnimating: widget.isSimulating,
            compound: widget.compound,
          ),
        ),
      ),
    );
  }
}

class _MolecularPainter extends CustomPainter {
  final double progress;
  final bool isAnimating;
  final String compound;

  const _MolecularPainter({
    required this.progress,
    required this.isAnimating,
    required this.compound,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final bondPaint = Paint()
      ..color = AppColors.purple.withOpacity(0.35)
      ..strokeWidth = 1.8
      ..style = PaintingStyle.stroke;

    final nodePaint = Paint()
      ..color = AppColors.cyan.withOpacity(0.8)
      ..style = PaintingStyle.fill;

    final glowPaint = Paint()
      ..color = AppColors.purple.withOpacity(0.15)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

    final offset = isAnimating ? sin(progress * 2 * pi) * 6 : 0.0;

    final nodes = [
      Offset(size.width * 0.20 + offset, size.height * 0.30),
      Offset(size.width * 0.40 - offset * 0.5, size.height * 0.55),
      Offset(size.width * 0.58 + offset * 0.3, size.height * 0.25),
      Offset(size.width * 0.72 - offset, size.height * 0.60),
      Offset(size.width * 0.33 + offset * 0.6, size.height * 0.72),
      Offset(size.width * 0.82 + offset * 0.4, size.height * 0.38),
      Offset(size.width * 0.50 - offset * 0.2, size.height * 0.42),
    ];

    const edges = [
      [0, 1], [1, 2], [2, 3], [1, 4], [2, 6], [3, 5], [6, 4], [0, 6],
    ];

    for (final e in edges) {
      canvas.drawLine(nodes[e[0]], nodes[e[1]], bondPaint);
    }

    for (final n in nodes) {
      canvas.drawCircle(n, 10, glowPaint);
      canvas.drawCircle(n, 5, nodePaint);

      // Label
      final tp = TextPainter(
        text: TextSpan(
          text: compound.substring(0, 1),
          style: TextStyle(
            color: AppColors.textPrimary.withOpacity(0.6),
            fontSize: 8,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, n.translate(-tp.width / 2, -tp.height / 2));
    }
  }

  @override
  bool shouldRepaint(_MolecularPainter old) =>
      old.progress != progress || old.isAnimating != isAnimating;
}

// ── Status bar ────────────────────────────────────────────────────────────────
class _StatusBar extends StatelessWidget {
  final int molecules;
  final int bonds;
  final double energy;

  const _StatusBar({
    required this.molecules,
    required this.bonds,
    required this.energy,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _StatChip(label: 'virtual_lab_molecules'.tr, value: molecules.toString()),
          _Divider(),
          _StatChip(label: 'virtual_lab_bonds'.tr, value: bonds.toString()),
          _Divider(),
          _StatChip(
              label: 'virtual_lab_energy'.tr,
              value: '${energy.toStringAsFixed(1)} eV'),
        ],
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label;
  final String value;
  const _StatChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: TextStyle(
            color: AppColors.cyan,
            fontSize: 16,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 9,
            letterSpacing: 1.2,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(width: 1, height: 28, color: AppColors.borderDefault);
  }
}

// ── Bottom panel ──────────────────────────────────────────────────────────────
class _BottomPanel extends StatelessWidget {
  final VirtualLabController controller;
  const _BottomPanel({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: AppColors.borderDefault)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Compound selector
          Text(
            'virtual_lab_select_compound'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 9,
              letterSpacing: 1.5,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          Obx(() => SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: controller.compounds.map((c) {
                    final selected = controller.selectedCompound.value == c;
                    return GestureDetector(
                      onTap: () => controller.selectCompound(c),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: selected
                              ? AppColors.purple.withOpacity(0.2)
                              : AppColors.bgBase,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: selected
                                ? AppColors.purple
                                : AppColors.borderDefault,
                            width: selected ? 1.5 : 1,
                          ),
                        ),
                        child: Text(
                          c,
                          style: TextStyle(
                            color: selected
                                ? AppColors.purple
                                : AppColors.textSecondary,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              )),

          const SizedBox(height: 16),

          // Sliders
          _SliderRow(
            label: 'virtual_lab_temperature'.tr,
            unit: '°C',
            value: controller.temperature,
            min: -100,
            max: 500,
            activeColor: AppColors.amber,
          ),
          const SizedBox(height: 10),
          _SliderRow(
            label: 'virtual_lab_pressure'.tr,
            unit: 'atm',
            value: controller.pressure,
            min: 0.1,
            max: 10.0,
            activeColor: AppColors.cyan,
          ),

          const SizedBox(height: 18),

          // Start simulation button
          Obx(() => GestureDetector(
                onTap: controller.toggleSimulation,
                child: Container(
                  width: double.infinity,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: controller.isSimulating.value
                        ? LinearGradient(
                            colors: [
                              AppColors.danger,
                              AppColors.danger.withRed(200),
                            ],
                          )
                        : AppColors.gradientPurple,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: (controller.isSimulating.value
                                ? AppColors.danger
                                : AppColors.purple)
                            .withOpacity(0.35),
                        blurRadius: 14,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    controller.isSimulating.value
                        ? 'virtual_lab_stop'.tr
                        : 'virtual_lab_start'.tr,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),
              )),
        ],
      ),
    );
  }
}

class _SliderRow extends StatelessWidget {
  final String label;
  final String unit;
  final RxDouble value;
  final double min;
  final double max;
  final Color activeColor;

  const _SliderRow({
    required this.label,
    required this.unit,
    required this.value,
    required this.min,
    required this.max,
    required this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Obx(() => Row(
          children: [
            SizedBox(
              width: 82,
              child: Text(
                label,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 9,
                  letterSpacing: 1,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Expanded(
              child: SliderTheme(
                data: SliderThemeData(
                  trackHeight: 3,
                  thumbShape:
                      const RoundSliderThumbShape(enabledThumbRadius: 7),
                  activeTrackColor: activeColor,
                  inactiveTrackColor: AppColors.borderDefault,
                  thumbColor: activeColor,
                  overlayColor: activeColor.withOpacity(0.15),
                ),
                child: Slider(
                  value: value.value,
                  min: min,
                  max: max,
                  onChanged: (v) => value.value = v,
                ),
              ),
            ),
            SizedBox(
              width: 60,
              child: Text(
                '${value.value.toStringAsFixed(1)} $unit',
                style: TextStyle(
                  color: activeColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
                textAlign: TextAlign.right,
              ),
            ),
          ],
        ));
  }
}
