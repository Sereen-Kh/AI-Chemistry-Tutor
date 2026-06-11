import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/reels_controller.dart';

class ReelsView extends GetView<ReelsController> {
  const ReelsView({super.key});

  List<String> get _tabs => [
        'reels_tab_for_you'.tr,
        'reels_tab_trending'.tr,
        'reels_tab_saved'.tr,
      ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        children: [
          // ── Full-screen page swiper ──────────────────────────────────────
          Obx(() {
            controller.currentIndex.value;
            return PageView.builder(
              controller: controller.pageController,
              scrollDirection: Axis.vertical,
              onPageChanged: controller.onPageChanged,
              itemCount: ReelsController.reels.length,
              itemBuilder: (_, i) => _ReelPage(
                reel: ReelsController.reels[i],
                index: i,
                controller: controller,
              ),
            );
          }),

          // ── Top bar ──────────────────────────────────────────────────────
          _TopBar(tabs: _tabs, controller: controller),

          // ── Right action sidebar ─────────────────────────────────────────
          _RightSidebar(controller: controller),
        ],
      ),
    );
  }
}

// ── Single reel page ──────────────────────────────────────────────────────────
class _ReelPage extends StatelessWidget {
  final ReelItem reel;
  final int index;
  final ReelsController controller;
  const _ReelPage({required this.reel, required this.index, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        // Background gradient
        _ReelBackground(accentColor: reel.accentColor),

        // Central chemistry visual
        Center(child: _ElementCard(reel: reel, controller: controller)),

        // Bottom fade + content
        _BottomContent(reel: reel, index: index, controller: controller),
      ],
    );
  }
}

// ── Background ────────────────────────────────────────────────────────────────
class _ReelBackground extends StatelessWidget {
  final Color accentColor;
  const _ReelBackground({required this.accentColor});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        gradient: RadialGradient(
          center: const Alignment(0, -0.2),
          radius: 1.4,
          colors: [
            accentColor.withOpacity(0.12),
            const Color(0xFF050818),
            Colors.black,
          ],
          stops: const [0.0, 0.55, 1.0],
        ),
      ),
    );
  }
}

// ── Element card (center visual) ──────────────────────────────────────────────
class _ElementCard extends StatelessWidget {
  final ReelItem reel;
  final ReelsController controller;
  const _ElementCard({required this.reel, required this.controller});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller.pulseController,
      builder: (_, __) {
        final pulse = controller.pulseController.value;
        return Stack(
          alignment: Alignment.center,
          children: [
            // Outer glow ring
            Container(
              width: 200 + pulse * 20,
              height: 200 + pulse * 20,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    reel.accentColor.withOpacity(0.06 + pulse * 0.04),
                    Colors.transparent,
                  ],
                ),
              ),
            ),

            // Orbit rings
            CustomPaint(
              size: const Size(190, 190),
              painter: _OrbitPainter(color: reel.accentColor, pulse: pulse),
            ),

            // Element tile
            Container(
              width: 130,
              height: 130,
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.6),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: reel.accentColor.withOpacity(0.6 + pulse * 0.4),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: reel.accentColor.withOpacity(0.25 + pulse * 0.15),
                    blurRadius: 30,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    reel.atomicNumber.toString(),
                    style: TextStyle(
                      color: reel.accentColor.withOpacity(0.7),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(height: 2),
                  ShaderMask(
                    shaderCallback: (b) => LinearGradient(
                      colors: [reel.accentColor, Colors.white],
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                    ).createShader(b),
                    child: Text(
                      reel.symbol,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 52,
                        fontWeight: FontWeight.w900,
                        height: 1,
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    reel.element.toUpperCase(),
                    style: TextStyle(
                      color: reel.accentColor.withOpacity(0.8),
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 2,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    )
        .animate()
        .fadeIn(duration: 400.ms)
        .scale(begin: const Offset(0.85, 0.85), duration: 400.ms, curve: Curves.easeOut);
  }
}

class _OrbitPainter extends CustomPainter {
  final Color color;
  final double pulse;
  const _OrbitPainter({required this.color, required this.pulse});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final paint = Paint()
      ..color = color.withOpacity(0.3 + pulse * 0.2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final dotPaint = Paint()
      ..color = color.withOpacity(0.8)
      ..style = PaintingStyle.fill;

    for (int i = 0; i < 3; i++) {
      canvas.save();
      canvas.translate(center.dx, center.dy);
      canvas.rotate(i * pi / 3 + pulse * 0.3);
      canvas.drawOval(
        Rect.fromCenter(center: Offset.zero, width: size.width, height: size.height * 0.38),
        paint,
      );
      canvas.drawCircle(Offset(size.width / 2, 0), 4, dotPaint);
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(_OrbitPainter old) => old.pulse != pulse;
}

// ── Bottom content overlay ────────────────────────────────────────────────────
class _BottomContent extends StatelessWidget {
  final ReelItem reel;
  final int index;
  final ReelsController controller;
  const _BottomContent({required this.reel, required this.index, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Colors.transparent,
              Colors.black.withOpacity(0.7),
              Colors.black.withOpacity(0.95),
            ],
            stops: const [0, 0.4, 1],
          ),
        ),
        padding: const EdgeInsets.fromLTRB(16, 60, 72, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Tag chip + chapter
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: reel.accentColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: reel.accentColor.withOpacity(0.5)),
                  ),
                  child: Text(
                    reel.tag,
                    style: TextStyle(
                      color: reel.accentColor,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  reel.chapter,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Title
            Text(
              reel.title,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w700,
                height: 1.3,
              ),
            ),
            const SizedBox(height: 8),

            // Description box
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.08)),
              ),
              child: Text(
                reel.description,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 12,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Progress row
            Row(
              children: [
                // XP pill
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    gradient: AppColors.gradientPurple,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.bolt, color: Colors.white, size: 12),
                      const SizedBox(width: 3),
                      Text(
                        '+${reel.xpReward} XP',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),

                // Progress bar
                Expanded(
                  child: Obx(() => ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: controller.currentIndex.value == index
                              ? controller.progress
                              : 0,
                          color: reel.accentColor,
                          backgroundColor: Colors.white12,
                          minHeight: 4,
                        ),
                      )),
                ),
                const SizedBox(width: 10),

                // Timer
                Obx(() => Text(
                      controller.currentIndex.value == index
                          ? controller.timeLabel
                          : '${reel.durationSeconds}s',
                      style: const TextStyle(color: Colors.white54, fontSize: 11),
                    )),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── Right action sidebar ──────────────────────────────────────────────────────
class _RightSidebar extends StatelessWidget {
  final ReelsController controller;
  const _RightSidebar({required this.controller});

  String _fmt(int n) => n >= 1000 ? '${(n / 1000).toStringAsFixed(1)}K' : '$n';

  @override
  Widget build(BuildContext context) {
    return Positioned(
      right: 12,
      bottom: 140,
      child: Column(
        children: [
          // Like
          GestureDetector(
            onTap: controller.toggleLike,
            child: Column(
              children: [
                _ActionButton(
                  child: Obx(() => Icon(
                        controller.isLiked.value ? Icons.favorite : Icons.favorite_border,
                        color: controller.isLiked.value ? Colors.red : Colors.white,
                        size: 22,
                      )),
                  isActive: false,
                ),
                const SizedBox(height: 4),
                Obx(() => Text(
                      _fmt(controller.current.likes + (controller.isLiked.value ? 1 : 0)),
                      style: const TextStyle(color: Colors.white70, fontSize: 11),
                    )),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Save
          GestureDetector(
            onTap: controller.toggleSave,
            child: Column(
              children: [
                _ActionButton(
                  child: Obx(() => Icon(
                        controller.isSaved.value ? Icons.bookmark : Icons.bookmark_border,
                        color: controller.isSaved.value ? AppColors.amber : Colors.white,
                        size: 22,
                      )),
                  isActive: false,
                ),
                const SizedBox(height: 4),
                Text('reels_save'.tr, style: const TextStyle(color: Colors.white70, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Share
          Column(
            children: [
              _ActionButton(
                child: const Icon(Icons.share_outlined, color: Colors.white, size: 22),
                isActive: false,
              ),
              const SizedBox(height: 4),
              Text('reels_share'.tr, style: const TextStyle(color: Colors.white70, fontSize: 11)),
            ],
          ),
          const SizedBox(height: 20),

          // XP indicator
          Column(
            children: [
              _ActionButton(
                child: ShaderMask(
                  shaderCallback: (b) => AppColors.gradientPurple.createShader(b),
                  blendMode: BlendMode.srcIn,
                  child: const Icon(Icons.bolt, color: Colors.white, size: 22),
                ),
                isActive: true,
              ),
              const SizedBox(height: 4),
              Obx(() => Text(
                    '+${controller.current.xpReward}',
                    style: TextStyle(color: AppColors.purpleLight, fontSize: 11, fontWeight: FontWeight.w700),
                  )),
            ],
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final Widget child;
  final bool isActive;
  const _ActionButton({required this.child, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(
          color: isActive ? AppColors.purple.withOpacity(0.6) : Colors.white.withOpacity(0.15),
        ),
        boxShadow: isActive
            ? [BoxShadow(color: AppColors.purple.withOpacity(0.3), blurRadius: 12)]
            : null,
      ),
      child: Center(child: child),
    );
  }
}

// ── Top bar with tabs ─────────────────────────────────────────────────────────
class _TopBar extends StatelessWidget {
  final List<String> tabs;
  final ReelsController controller;
  const _TopBar({required this.tabs, required this.controller});

  @override
  Widget build(BuildContext context) {
    final topPad = MediaQuery.of(context).padding.top;
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: Container(
        padding: EdgeInsets.fromLTRB(12, topPad + 8, 12, 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.black.withOpacity(0.7), Colors.transparent],
          ),
        ),
        child: Row(
          children: [
            // App logo
            ShaderMask(
              shaderCallback: (b) => AppColors.gradientPurple.createShader(b),
              child: Text(
                'reels_title'.tr,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 2,
                ),
              ),
            ),
            const Spacer(),

            // Tabs
            Obx(() => Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(tabs.length, (i) {
                    final active = controller.activeTab.value == i;
                    return GestureDetector(
                      onTap: () => controller.activeTab.value = i,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.only(left: 6),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: active
                              ? AppColors.purple.withOpacity(0.25)
                              : Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: active
                                ? AppColors.purple.withOpacity(0.7)
                                : Colors.white.withOpacity(0.1),
                          ),
                        ),
                        child: Text(
                          tabs[i],
                          style: TextStyle(
                            color: active ? AppColors.purpleLight : Colors.white54,
                            fontSize: 9,
                            fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ),
                    );
                  }),
                )),

            // const SizedBox(width: 6),

            // // Search button
            // Container(
            //   width: 34,
            //   height: 34,
            //   decoration: BoxDecoration(
            //     color: Colors.white.withOpacity(0.08),
            //     shape: BoxShape.circle,
            //     border: Border.all(color: Colors.white.withOpacity(0.15)),
            //   ),
            //   child: const Icon(Icons.search, color: Colors.white70, size: 18),
            // ),
          ],
        ),
      ),
    );
  }
}
