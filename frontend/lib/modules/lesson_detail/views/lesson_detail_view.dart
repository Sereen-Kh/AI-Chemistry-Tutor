import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../core/controllers/explanation_style_controller.dart';
import '../../../widgets/explanation_style_chips.dart';
import '../controllers/lesson_detail_controller.dart';
import '../../main_nav/controllers/main_nav_controller.dart';
class LessonDetailView extends GetView<LessonDetailController> {
  const LessonDetailView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgDeep,
      appBar: _buildAppBar(),
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: const EdgeInsets.only(bottom: 100),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 12),
                _buildTabBar(),
                const SizedBox(height: 12),
                _buildTitleRow(),
                const SizedBox(height: 8),
                _buildProgressBar(),
                const SizedBox(height: 12),
                _buildExplanationStyleSection(),
                const SizedBox(height: 16),
                _buildStepCards(),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: _buildGotItButton(),
          ),
        ],
      ),
    );
  }
  PreferredSizeWidget _buildAppBar() {
    final avatarUrl =
        '';
    return AppBar(
      // backgroundColor: const Color(0xFF020408),
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.all( 5),
        child: GestureDetector(
          onTap: () => Get.find<MainNavController>().openDrawer(),
          child: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Icon(Icons.menu_rounded, color: AppColors.textSecondary, size: 18),
          ),
        ),
      ),
      title: ShaderMask(
        shaderCallback: (bounds) => AppColors.gradientPurple.createShader(bounds),
        child: Text(
          'app_name'.tr,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      centerTitle: true,
      actions: [
        Padding(
          padding: const EdgeInsets.all(5),
          child:

          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.bgCard,
              border: Border.all(color: AppColors.borderDefault),
              image: avatarUrl.isNotEmpty
                  ? DecorationImage(image: NetworkImage(avatarUrl), fit: BoxFit.cover)
                  : null,
            ),
            child: avatarUrl.isEmpty
                ? Icon(Icons.account_circle_outlined, color: AppColors.purple, size: 22)
                : null,
          )
          ,
        ),
      ],
    );
  }
  // AppBar _buildAppBar() {
  //   return AppBar(
  //     backgroundColor: AppColors.bgDeep,
  //     elevation: 0,
  //     automaticallyImplyLeading: false,
  //     leading: Padding(
  //       padding: const EdgeInsets.all(10),
  //       child: Container(
  //         decoration: BoxDecoration(
  //           color: AppColors.bgCard,
  //           borderRadius: BorderRadius.circular(10),
  //         ),
  //         child: const Icon(Icons.bolt, color: Colors.white, size: 20),
  //       ),
  //     ),
  //     title: ShaderMask(
  //       shaderCallback: (bounds) => LinearGradient(
  //         colors: [AppColors.purple, AppColors.cyan],
  //       ).createShader(bounds),
  //       child: const Text(
  //         'ChemAI',
  //         style: TextStyle(
  //           color: Colors.white,
  //           fontSize: 18,
  //           fontWeight: FontWeight.w800,
  //           letterSpacing: 0.5,
  //         ),
  //       ),
  //     ),
  //     centerTitle: true,
  //     actions: [
  //       Padding(
  //         padding: const EdgeInsets.only(right: 12),
  //         child: Container(
  //           width: 36,
  //           height: 36,
  //           decoration: BoxDecoration(
  //             shape: BoxShape.circle,
  //             color: AppColors.bgCard,
  //           ),
  //           child: const Icon(Icons.person_outline, color: Colors.white70, size: 20),
  //         ),
  //       ),
  //     ],
  //   );
  // }

  Widget _buildTabBar() {
    final tabs = [
      'lesson_detail_tab_steps'.tr,
      'lesson_detail_tab_equations'.tr,
      'lesson_detail_tab_visual'.tr,
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Obx(() => Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(30),
            ),
            child: Row(
              children: List.generate(tabs.length, (i) {
                final isActive = controller.activeTab.value == i;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => controller.setTab(i),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: isActive ? Colors.white : Colors.transparent,
                        borderRadius: BorderRadius.circular(26),
                      ),
                      child: Text(
                        tabs[i],
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: isActive ? AppColors.bgDeep : AppColors.textMuted,
                          fontSize: 13,
                          fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                );
              }),
            ),
          )),
    );
  }

  Widget _buildTitleRow() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Obx(() => Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  controller.lessonTitle,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.purple,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'lesson_detail_step_counter'.trParams({
                    'current': '${controller.currentStep.value + 1}',
                    'total': '${controller.totalSteps}',
                  }),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          )),
    );
  }

  Widget _buildExplanationStyleSection() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'lesson_detail_explanation_mode'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 8),
          const ExplanationStyleChips(),
        ],
      ),
    );
  }

  Widget _buildProgressBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Obx(() => ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (controller.currentStep.value + 1) / controller.totalSteps,
              minHeight: 3,
              backgroundColor: AppColors.bgCard,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.purple),
            ),
          )),
    );
  }

  Widget _buildStepCards() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          _buildPastStepCard(
            stepNumber: 1,
            text: 'The two hydrogen atoms approach each other due to attractive forces.',
          ).animate().fadeIn(duration: 300.ms),
          const SizedBox(height: 12),
          _buildActiveStepCard().animate().fadeIn(duration: 400.ms, delay: 100.ms),
          const SizedBox(height: 12),
          _buildUpcomingStepCard(
            stepNumber: 3,
            text: 'Atoms reaching maximum stability...',
          ).animate().fadeIn(duration: 300.ms, delay: 200.ms),
        ],
      ),
    );
  }

  Widget _buildPastStepCard({required int stepNumber, required String text}) {
    return Opacity(
      opacity: 0.5,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                text,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.textMuted.withOpacity(0.3),
              ),
              child: Center(
                child: Text(
                  '$stepNumber',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveStepCard() {
    final esc = Get.find<ExplanationStyleController>();
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white, width: 1.5),
      ),
      child: Obx(() {
        final style = esc.selectedId.value;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildActiveStepHeader(),
            const SizedBox(height: 10),
            ..._buildActiveStepBody(style),
          ],
        );
      }),
    );
  }

  Widget _buildActiveStepHeader() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            'Orbital Overlap',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.cyan,
            boxShadow: [
              BoxShadow(
                color: AppColors.cyan.withOpacity(0.4),
                blurRadius: 10,
                spreadRadius: 2,
              ),
            ],
          ),
          child: const Center(
            child: Text(
              '2',
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildActiveStepBody(String style) {
    const bodyText =
        'The electron cloud of each atom begins to overlap with the other\'s, increasing the probability of electrons existing in the region between the nuclei.';

    switch (style) {
      case 'reel':
        return [
          _buildReelPlayer(),
          const SizedBox(height: 12),
          _buildKemoAdviceCard(),
        ];
      case 'voice':
        return [
          _buildVoicePlayer(),
          const SizedBox(height: 12),
          Text(
            bodyText,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 12),
          _buildKemoAdviceCard(),
        ];
      case 'visual':
        return [
          _buildImageCarousel(height: 200),
          const SizedBox(height: 12),
          _buildKemoAdviceCard(),
        ];
      case 'text':
      default:
        return [
          Text(
            bodyText,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 12),
          _buildKemoAdviceCard(),
        ];
    }
  }

  Widget _buildReelPlayer() {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: LinearGradient(
          colors: [
            AppColors.purple.withOpacity(0.7),
            AppColors.bgDeep,
          ],
        ),
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Icon(Icons.play_circle_fill_rounded,
              color: Colors.white.withOpacity(0.9), size: 56),
          Positioned(
            bottom: 10,
            left: 12,
            right: 12,
            child: Text(
              'lesson_detail_reel_caption'.tr,
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVoicePlayer() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgDeep,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.cyan.withOpacity(0.35)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.cyan.withOpacity(0.15),
            ),
            child: Icon(Icons.play_arrow_rounded, color: AppColors.cyan, size: 28),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'lesson_detail_voice_title'.tr,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: 0.35,
                    minHeight: 4,
                    backgroundColor: AppColors.bgCard,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(AppColors.cyan),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKemoAdviceCard() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0A1628),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.cyan.withOpacity(0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Center(
              child: Text('🧬', style: TextStyle(fontSize: 24)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'lesson_detail_kemo_tip'.tr,
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '"Imagine them sharing an umbrella on a rainy day!"',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImageCarousel({double height = 160}) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.purple.withOpacity(0.6), AppColors.cyan.withOpacity(0.4)],
        ),
      ),
      child: Stack(
        children: [
          Center(
            child: Text(
              '⚛',
              style: TextStyle(
                fontSize: 64,
                color: Colors.white.withOpacity(0.8),
                shadows: [
                  Shadow(
                    color: AppColors.cyan.withOpacity(0.8),
                    blurRadius: 20,
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            bottom: 10,
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildDot(false),
                const SizedBox(width: 5),
                _buildDot(false),
                const SizedBox(width: 5),
                _buildDot(true),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDot(bool isActive) {
    return Container(
      width: 6,
      height: 6,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: isActive ? Colors.white : AppColors.textMuted,
      ),
    );
  }

  Widget _buildUpcomingStepCard({required int stepNumber, required String text}) {
    return Opacity(
      opacity: 0.4,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                text,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 13,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.textMuted.withOpacity(0.3),
              ),
              child: Center(
                child: Text(
                  '$stepNumber',
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGotItButton() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
      color: AppColors.bgDeep,
      child: SizedBox(
        height: 56,
        width: double.infinity,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF84CC16), Color(0xFF4ADE80)],
              begin: Alignment.centerLeft,
              end: Alignment.centerRight,
            ),
            borderRadius: BorderRadius.circular(16),
          ),
          child: TextButton.icon(
            onPressed: controller.gotIt,
            icon: const Icon(Icons.check_circle_outline, color: Colors.black, size: 20),
            label: Text(
              'lesson_detail_got_it'.tr,
              style: const TextStyle(
                color: Colors.black,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            style: TextButton.styleFrom(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
            ),
          ),
        ),
      ),
    ).animate().slideY(begin: 1, end: 0, duration: 400.ms, curve: Curves.easeOut);
  }
}
