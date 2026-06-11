import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/flashcards_controller.dart';

class FlashcardsView extends GetView<FlashcardsController> {
  const FlashcardsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgDeep,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          const SizedBox(height: 12),

          // ── Progress pill ────────────────────────────────────────────
          Obx(() => Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text('⭐', style: TextStyle(fontSize: 13)),
                    const SizedBox(width: 6),
                    Text(
                      'flashcards_mastered'.trParams({
                        'count': '${controller.masteredCount.value}',
                      }),
                      style:  TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Container(
                      width: 1,
                      height: 14,
                      margin:  EdgeInsets.symmetric(horizontal: 10),
                      color: AppColors.borderDefault,
                    ),
                    Text(
                      'flashcards_total'.trParams({
                        'count': '${controller.totalCards}',
                      }),
                      style:  TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              )),

          const Spacer(flex: 2),

          // ── Card area with forget/mastered buttons ───────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // FORGET
                _ActionButton(
                  icon: Icons.close,
                  label: 'flashcards_forget'.tr,
                  color: const Color(0xFFEF4444),
                  onTap: controller.markForgotten,
                ),

                const SizedBox(width: 16),

                // Flashcard — subscribe to currentIndex so card content updates on swipe
                Expanded(
                  child: Obx(() {
                    controller.currentIndex.value;
                    return _FlipCard(controller: controller);
                  }),
                ),

                const SizedBox(width: 16),

                // MASTERED
                _ActionButton(
                  icon: Icons.check,
                  label: 'flashcards_mastered_btn'.tr,
                  color: AppColors.green,
                  onTap: controller.markMastered,
                ),
              ],
            ),
          ),

          const Spacer(flex: 2),

          // ── Daily progress ring ──────────────────────────────────────
          Obx(() => _DailyProgress(
                progress: controller.dailyProgress.value,
                remaining: controller.dailyGoalRemaining,
              )).animate().fadeIn(delay: 300.ms, duration: 400.ms),

          const SizedBox(height: 28),
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
      title: Row(
        children: [
          Text(
            'flashcards_title'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w800,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(width: 10),

        ],
      ),
    );
  }
}

// ── Flip card widget ──────────────────────────────────────────────────────────
class _FlipCard extends StatelessWidget {
  final FlashcardsController controller;
  const _FlipCard({required this.controller});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: controller.flip,
      child: AnimatedBuilder(
        animation: controller.flipController,
        builder: (_, __) {
          final angle = controller.flipController.value * pi;
          final showFront = controller.flipController.value < 0.5;

          return Transform(
            transform: Matrix4.identity()
              ..setEntry(3, 2, 0.001)
              ..rotateY(angle),
            alignment: Alignment.center,
            child: showFront
                ? _CardFront(card: controller.current)
                : Transform(
                    transform: Matrix4.rotationY(pi),
                    alignment: Alignment.center,
                    child: _CardBack(card: controller.current),
                  ),
          );
        },
      ),
    );
  }
}

class _CardFront extends StatelessWidget {
  final dynamic card;
  const _CardFront({required this.card});

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Header row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'flashcards_quantum_state'.trParams({'state': card.state}),
                style:  TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 9,
                  letterSpacing: 1.5,
                ),
              ),
              Row(
                children: List.generate(
                    3,
                    (i) => Container(
                          width: 6,
                          height: 6,
                          margin: const EdgeInsets.only(left: 4),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: i == 0
                                ? AppColors.purple
                                : AppColors.borderDefault,
                          ),
                        )),
              ),
            ],
          ),

          const Spacer(),

          // Concept number
          Text(
            'flashcards_concept'.trParams({
              'id': card.id.toString().padLeft(3, '0'),
            }),
            style:  TextStyle(
              color: AppColors.purple,
              fontSize: 12,
              letterSpacing: 2,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Container(
            width: 40,
            height: 1,
            color: AppColors.borderDefault,
          ),
          const SizedBox(height: 14),

          // Term
          Text(
            card.term,
            style:  TextStyle(
              color: AppColors.textPrimary,
              fontSize: 26,
              fontWeight: FontWeight.w800,
              height: 1.2,
            ),
            textAlign: TextAlign.center,
          ),

          const SizedBox(height: 14),

          // Formula
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: AppColors.bgCardAlt,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Text(
              card.formula,
              style:  TextStyle(
                color: AppColors.textSecondary,
                fontSize: 16,
              ),
            ),
          ),

          const Spacer(),

          // Flip hint
          Column(
            children: [
               Icon(Icons.sync_rounded,
                  color: AppColors.textMuted, size: 18),
              const SizedBox(height: 4),
               Text(
                'flashcards_tap_flip'.tr,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 11,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _CardBack extends StatelessWidget {
  final dynamic card;
  const _CardBack({required this.card});

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'flashcards_quantum_state'.trParams({'state': card.state}),
                style:  TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 9,
                  letterSpacing: 1.5,
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.green.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(4),
                ),
                child:  Text(
                  'flashcards_definition'.tr,
                  style: TextStyle(
                    color: AppColors.green,
                    fontSize: 8,
                    letterSpacing: 1,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),

          const Spacer(),

          Text(
            card.definition,
            style:  TextStyle(
              color: AppColors.textPrimary,
              fontSize: 15,
              height: 1.6,
            ),
            textAlign: TextAlign.center,
          ),

          const SizedBox(height: 16),

          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.bgCardAlt,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Text(
              card.example,
              style:  TextStyle(
                color: AppColors.cyan,
                fontSize: 12,
                fontFamily: 'monospace',
              ),
              textAlign: TextAlign.center,
            ),
          ),

          const Spacer(),

           Column(
            children: [
              Icon(Icons.sync_rounded,
                  color: AppColors.textMuted, size: 18),
              SizedBox(height: 4),
              Text(
                'flashcards_tap_flip'.tr,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 11,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _CardShell extends StatelessWidget {
  final Widget child;
  const _CardShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 340,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF111530),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderDefault),
        boxShadow: [
          BoxShadow(
            color: AppColors.purple.withOpacity(0.12),
            blurRadius: 30,
            spreadRadius: 0,
          ),
        ],
      ),
      child: child,
    );
  }
}

// ── Action button (FORGET / MASTERED) ────────────────────────────────────────
class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withOpacity(0.12),
              border: Border.all(color: color.withOpacity(0.4)),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: TextStyle(
              color: color.withOpacity(0.8),
              fontSize: 9,
              letterSpacing: 1,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Daily progress ring ───────────────────────────────────────────────────────
class _DailyProgress extends StatelessWidget {
  final double progress;
  final int remaining;
  const _DailyProgress({required this.progress, required this.remaining});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: 64,
          height: 64,
          child: CustomPaint(
            painter: _RingPainter(progress: progress),
            child: Center(
              child: Text(
                '${(progress * 100).toInt()}%',
                style:  TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        Text(
          'flashcards_daily_goal'.trParams({'remaining': '$remaining'}),
          style:  TextStyle(
            color: AppColors.textSecondary,
            fontSize: 13,
          ),
        ),
      ],
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
    final r = size.width / 2 - 4;

    canvas.drawCircle(
      Offset(cx, cy),
      r,
      Paint()
        ..color = AppColors.borderDefault
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4,
    );
    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: r),
      -pi / 2,
      2 * pi * progress,
      false,
      Paint()
        ..color = AppColors.purple
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_RingPainter o) => o.progress != progress;
}
