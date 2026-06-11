import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';

import '../../../app/theme/app_colors.dart';
import '../../../widgets/kimo_widget.dart';
import '../controllers/onboarding_controller.dart';

class OnboardingView extends GetView<OnboardingController> {
  const OnboardingView({super.key});

  static const _kimoStates = [
    KimoState.happy,
    KimoState.celebrating,
    KimoState.concentrating,
  ];

  static const _kimoMessageKeys = [
    'kimo_msg_1',
    'kimo_msg_2',
    'kimo_msg_3',
  ];

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: const Color(0xFF070A1C),
      body: Stack(
        children: [
          // Background radial glow
          Positioned(
            top: -60,
            left: 0,
            right: 0,
            child: Container(
              height: size.height * 0.60,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.3),
                  radius: 0.75,
                  colors: [
                    AppColors.purple.withOpacity(0.25),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          Column(
            children: [
              // ── Illustration area with Kimo ─────────────────────────────
              SizedBox(
                height: size.height * 0.58,
                child: PageView.builder(
                  controller: controller.pageController,
                  onPageChanged: (i) => controller.pageIndex.value = i,
                  itemCount: controller.pages.length,
                  itemBuilder: (_, i) => _OnboardingPage(
                    pageIndex: i,
                    kimoState: _kimoStates[i],
                    message: _kimoMessageKeys[i].tr,
                    illustrationIndex: i,
                  ),
                ),
              ),

              // ── Bottom sheet ────────────────────────────────────────────
              Expanded(
                child: Container(
                  width: double.infinity,
                  decoration: const BoxDecoration(
                    color: Color(0xFF0D1030),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
                  ),
                  padding: const EdgeInsets.fromLTRB(28, 28, 28, 28),
                  child: Column(
                    children: [
                      // Title
                      Obx(() => AnimatedSwitcher(
                            duration: const Duration(milliseconds: 300),
                            child: Text(
                              controller.pages[controller.pageIndex.value].title,
                              key: ValueKey(controller.pageIndex.value),
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                                height: 1.3,
                              ),
                            ),
                          )),

                      const SizedBox(height: 10),

                      // Subtitle
                      Obx(() => AnimatedSwitcher(
                            duration: const Duration(milliseconds: 300),
                            child: Text(
                              controller.pages[controller.pageIndex.value].subtitle,
                              key: ValueKey('${controller.pageIndex.value}_sub'),
                              textAlign: TextAlign.center,
                              style: TextStyle(color: AppColors.textSecondary, fontSize: 14, height: 1.6),
                            ),
                          )),

                      const SizedBox(height: 20),

                      // Page indicator
                      SmoothPageIndicator(
                        controller: controller.pageController,
                        count: controller.pages.length,
                        effect: ExpandingDotsEffect(
                          dotHeight: 6,
                          dotWidth: 6,
                          expansionFactor: 4,
                          activeDotColor: AppColors.purple,
                          dotColor: AppColors.borderDefault,
                          spacing: 6,
                        ),
                      ),

                      const Spacer(),

                      // NEXT button
                      SizedBox(
                        width: double.infinity,
                        child: GestureDetector(
                          onTap: controller.next,
                          child: Container(
                            height: 52,
                            decoration: BoxDecoration(
                              gradient: AppColors.gradientPurple,
                              borderRadius: BorderRadius.circular(30),
                            ),
                            alignment: Alignment.center,
                            child: Obx(() => Text(
                                  controller.pageIndex.value == controller.pages.length - 1
                                      ? 'onboarding_get_started'.tr
                                      : 'onboarding_next'.tr,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 1.2,
                                  ),
                                )),
                          ),
                        ),
                      ),

                      const SizedBox(height: 14),

                      GestureDetector(
                        onTap: controller.skip,
                        child: Text(
                          'onboarding_skip'.tr,
                          style: TextStyle(color: AppColors.textMuted, fontSize: 11, letterSpacing: 1.5),
                        ),
                      ),
                    ],
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

class _OnboardingPage extends StatelessWidget {
  final int pageIndex;
  final KimoState kimoState;
  final String message;
  final int illustrationIndex;

  const _OnboardingPage({
    required this.pageIndex,
    required this.kimoState,
    required this.message,
    required this.illustrationIndex,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Decorative floating icons based on page
          _FloatingIcons(index: illustrationIndex),

          const SizedBox(height: 16),

          // Kimo mascot
          KimoWidget(size: 130, state: kimoState),

          const SizedBox(height: 20),

          // Kimo speech bubble
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
              border: Border.all(color: AppColors.cyan.withOpacity(0.30)),
              boxShadow: [
                BoxShadow(
                  color: AppColors.cyan.withOpacity(0.08),
                  blurRadius: 20,
                ),
              ],
            ),
            child: Text(
              message,
              style: TextStyle(color: AppColors.textPrimary, fontSize: 13, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class _FloatingIcons extends StatelessWidget {
  final int index;
  const _FloatingIcons({required this.index});

  static const _iconSets = [
    [Icons.science_outlined, Icons.auto_awesome_outlined, Icons.biotech_outlined],
    [Icons.emoji_events_outlined, Icons.star_border_rounded, Icons.bolt_outlined],
    [Icons.smart_toy_outlined, Icons.psychology_outlined, Icons.lightbulb_outline],
  ];

  @override
  Widget build(BuildContext context) {
    final icons = _iconSets[index % _iconSets.length];
    final colors = [AppColors.cyan, AppColors.purple, AppColors.amber];

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(3, (i) {
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 8),
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: colors[i].withOpacity(0.10),
            shape: BoxShape.circle,
            border: Border.all(color: colors[i].withOpacity(0.30)),
          ),
          child: Icon(icons[i], color: colors[i], size: 20),
        );
      }),
    );
  }
}
