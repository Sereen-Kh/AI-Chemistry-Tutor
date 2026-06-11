import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../data/models/quiz_model.dart';
import '../controllers/quiz_controller.dart';

class QuizView extends GetView<QuizController> {
  const QuizView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: Obx(
        () => controller.hasStarted.value ? _buildQuizBody() : _buildSetupBody(),
      ),
    );
  }

  // PreferredSizeWidget _buildAppBar() {
  //   return AppBar(
  //     backgroundColor: AppColors.bgBase,
  //     elevation: 0,
  //     automaticallyImplyLeading: false,
  //     titleSpacing: 16,
  //     title: Row(
  //       children: [
  //         Container(
  //           width: 36,
  //           height: 36,
  //           decoration: BoxDecoration(
  //             color: AppColors.bgCard,
  //             borderRadius: BorderRadius.circular(10),
  //             border: Border.all(color: AppColors.borderDefault),
  //           ),
  //           alignment: Alignment.center,
  //           child: Icon(Icons.bolt, color: AppColors.amber, size: 20),
  //         ),
  //         const Spacer(),
  //         Obx(() => Container(
  //               padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
  //               decoration: BoxDecoration(
  //                 color: AppColors.bgCard,
  //                 borderRadius: BorderRadius.circular(20),
  //                 border: Border.all(color: AppColors.borderDefault),
  //               ),
  //               child: Row(
  //                 mainAxisSize: MainAxisSize.min,
  //                 children: [
  //                   Text(
  //                     controller.timerLabel,
  //                     style: TextStyle(
  //                       color: controller.secondsRemaining.value < 10
  //                           ? AppColors.warning
  //                           : AppColors.textPrimary,
  //                       fontSize: 13,
  //                       fontWeight: FontWeight.w700,
  //                       fontFamily: 'monospace',
  //                     ),
  //                   ),
  //                   const SizedBox(width: 6),
  //                   Icon(Icons.timer_rounded, color: AppColors.warning, size: 16),
  //                 ],
  //               ),
  //             )),
  //         const Spacer(),
  //         ShaderMask(
  //           shaderCallback: (bounds) =>
  //               AppColors.gradientPurple.createShader(bounds),
  //           blendMode: BlendMode.srcIn,
  //           child: const Text(
  //             'ChemAI',
  //             style: TextStyle(
  //               fontSize: 15,
  //               fontWeight: FontWeight.w800,
  //               color: Colors.white,
  //             ),
  //           ),
  //         ),
  //
  //       ],
  //     ),
  //   );
  // }
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
          const Spacer(),
          Obx(() => Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  controller.timerLabel,
                  style: TextStyle(
                    color: controller.secondsRemaining.value < 10
                        ? AppColors.warning
                        : AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'monospace',
                  ),
                ),
                const SizedBox(width: 6),
                Icon(Icons.timer_rounded, color: AppColors.warning, size: 16),
              ],
            ),
          )),
          const Spacer(),
          Text(
            'quiz_daily_title'.tr,
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
  Widget _buildQuizBody() {
    return Obx(() {
      final q = controller.current;
      final answered = controller.selectedOption.value != null;
      final correct = controller.isCorrect.value == true;

      return SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildQuestionCounter(q),
            const SizedBox(height: 16),
            _buildQuestionCard(q),
            const SizedBox(height: 14),
            ...q.options.map((opt) => _buildOptionRow(opt, q)),
            const SizedBox(height: 14),
            if (answered) _buildMascotFeedback(correct).animate().fadeIn(duration: 300.ms).slideY(begin: 0.2, end: 0),
            const SizedBox(height: 14),
            _buildNextButton(),
            const SizedBox(height: 24),
          ],
        ),
      );
    });
  }

  Widget _buildQuestionCounter(QuizQuestion q) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              '${controller.currentIndex.value + 1}/${controller.questions.length}',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 36,
                fontWeight: FontWeight.w900,
                height: 1,
              ),
            ),
            const Spacer(),
            Text(
              'quiz_question_counter'.trParams({
                'current': '${controller.currentIndex.value + 1}',
                'total': '${controller.questions.length}',
              }),
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: (controller.currentIndex.value + 1) / controller.questions.length,
            minHeight: 3,
            backgroundColor: AppColors.bgCard,
            color: AppColors.cyan,
          ),
        ),
      ],
    );
  }

  Widget _buildQuestionCard(QuizQuestion q) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Align(
            alignment: Alignment.topRight,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.purple.withOpacity(0.18),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.purple.withOpacity(0.4)),
              ),
              child: Text(
                'quiz_subject_tag'.tr,
                style: TextStyle(
                  color: AppColors.purpleLight,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            q.question,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w700,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppColors.bgCardAlt,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                alignment: Alignment.center,
                child: Text(
                  '?',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                q.hintSymbol.isNotEmpty ? q.hintSymbol : q.configLabel,
                style: TextStyle(
                  color: AppColors.cyan,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildOptionRow(QuizOption opt, QuizQuestion q) {
    return Obx(() {
      final selected = controller.selectedOption.value == opt.letter;
      final answered = controller.selectedOption.value != null;
      final isCorrectOpt = opt.letter == q.correctLetter;

      Color borderColor;
      Color bgColor;
      Color badgeBg;
      Color badgeText;

      if (!answered) {
        borderColor = AppColors.borderDefault;
        bgColor = AppColors.bgCard;
        badgeBg = AppColors.bgCardAlt;
        badgeText = AppColors.textSecondary;
      } else if (isCorrectOpt) {
        borderColor = AppColors.cyan;
        bgColor = AppColors.cyan.withOpacity(0.07);
        badgeBg = AppColors.cyan;
        badgeText = AppColors.bgBase;
      } else if (selected) {
        borderColor = Colors.red.shade400;
        bgColor = Colors.red.shade400.withOpacity(0.07);
        badgeBg = Colors.red.shade400;
        badgeText = Colors.white;
      } else {
        borderColor = AppColors.borderDefault;
        bgColor = AppColors.bgCard;
        badgeBg = AppColors.bgCardAlt;
        badgeText = AppColors.textMuted;
      }

      return GestureDetector(
        onTap: () => controller.selectOption(opt.letter),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: borderColor, width: 1.5),
          ),
          child: Row(
            children: [
              if (answered && isCorrectOpt)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Icon(Icons.check_circle, color: AppColors.cyan, size: 20),
                )
              else if (answered && selected && !isCorrectOpt)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Icon(Icons.cancel, color: Colors.red.shade400, size: 20),
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      opt.name,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    if (opt.detail.isNotEmpty)
                      Text(
                        opt.detail,
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 11,
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: badgeBg,
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text(
                  opt.letter,
                  style: TextStyle(
                    color: badgeText,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildMascotFeedback(bool correct) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: correct ? AppColors.green : Colors.red.shade400,
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: correct
                  ? AppColors.green.withOpacity(0.15)
                  : Colors.red.shade400.withOpacity(0.15),
            ),
            alignment: Alignment.center,
            child: Text(
              correct ? '🤖' : '😅',
              style: const TextStyle(fontSize: 20),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              correct
                  ? 'quiz_feedback_correct'.tr
                  : 'quiz_feedback_wrong'.tr,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNextButton() {
    return Obx(() {
      final answered = controller.selectedOption.value != null;
      return GestureDetector(
        onTap: answered ? controller.nextQuestion : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 52,
          decoration: BoxDecoration(
            gradient: answered ? AppColors.gradientPurple : null,
            color: answered ? null : AppColors.bgCard,
            borderRadius: BorderRadius.circular(14),
            border: answered
                ? null
                : Border.all(color: AppColors.borderDefault),
          ),
          alignment: Alignment.center,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'quiz_next'.tr,
                style: TextStyle(
                  color: answered
                      ? Colors.white
                      : AppColors.textMuted,
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.arrow_forward_rounded,
                color: answered ? Colors.white : AppColors.textMuted,
                size: 18,
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildSetupBody() {
    return _QuizSetupBody(controller: controller);
  }
}

class _QuizSetupBody extends StatefulWidget {
  final QuizController controller;
  const _QuizSetupBody({required this.controller});

  @override
  State<_QuizSetupBody> createState() => _QuizSetupBodyState();
}

class _QuizSetupBodyState extends State<_QuizSetupBody> {
  QuizController get c => widget.controller;

  int _questionCount = 15;
  String _difficulty = 'Medium';
  int _selectedChapter = 0;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMascotCard(),
          const SizedBox(height: 12),
          _buildSpeechBubble(),
          const SizedBox(height: 22),
          Text(
            'quiz_setup_title'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 26,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 22),
          _buildSectionLabel('quiz_choose_chapter'.tr),
          const SizedBox(height: 10),
          _buildChapterOption(
            index: 0,
            icon: Icons.science_rounded,
            title: 'Chemical Bonds',
            subtitle: 'Chapter 2 • 12 lessons',
            locked: false,
          ),
          const SizedBox(height: 8),
          _buildChapterOption(
            index: 1,
            icon: Icons.biotech_outlined,
            title: 'Organic Chemistry',
            subtitle: 'Chapter 3 • 8 lessons',
            locked: true,
          ),
          const SizedBox(height: 22),
          _buildSectionLabel('quiz_num_questions'.tr),
          const SizedBox(height: 10),
          _buildQuestionCountRow(),
          const SizedBox(height: 22),
          _buildSectionLabel('quiz_difficulty'.tr),
          const SizedBox(height: 10),
          _buildDifficultyRow(),
          const SizedBox(height: 28),
          _buildStartButton(),
          const SizedBox(height: 24),
        ],
      ),
    ).animate().fadeIn(duration: 350.ms);
  }

  Widget _buildMascotCard() {
    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.purple.withOpacity(0.35),
            AppColors.cyan.withOpacity(0.2),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      alignment: Alignment.center,
      child: const Text('🤖', style: TextStyle(fontSize: 72)),
    );
  }

  Widget _buildSpeechBubble() {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Text(
            'quiz_setup_prompt'.tr,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            textAlign: TextAlign.center,
          ),
        ),
        Positioned(
          top: -8,
          left: 0,
          right: 0,
          child: Center(
            child: CustomPaint(
              size: const Size(16, 8),
              painter: _ArrowUpPainter(color: AppColors.bgCard),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSectionLabel(String label) {
    return Text(
      label,
      style: TextStyle(
        color: AppColors.textSecondary,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 1.1,
      ),
    );
  }

  Widget _buildChapterOption({
    required int index,
    required IconData icon,
    required String title,
    required String subtitle,
    required bool locked,
  }) {
    final selected = _selectedChapter == index;
    return GestureDetector(
      onTap: locked ? null : () => setState(() => _selectedChapter = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? AppColors.cyan : AppColors.borderDefault,
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: locked
                    ? AppColors.bgCardAlt
                    : AppColors.cyan.withOpacity(0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              alignment: Alignment.center,
              child: Icon(
                locked ? Icons.lock_outline : icon,
                color: locked ? AppColors.textMuted : AppColors.cyan,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: locked
                          ? AppColors.textMuted
                          : AppColors.textPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: AppColors.textMuted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            if (!locked)
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 22,
                height: 22,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: selected ? AppColors.cyan : Colors.transparent,
                  border: Border.all(
                    color: selected ? AppColors.cyan : AppColors.borderDefault,
                    width: 2,
                  ),
                ),
                alignment: Alignment.center,
                child: selected
                    ? Icon(Icons.check, color: AppColors.bgBase, size: 13)
                    : null,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuestionCountRow() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Text(
                '$_questionCount',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'quiz_questions_label'.tr,
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: AppColors.cyan,
              inactiveTrackColor: AppColors.bgCardAlt,
              thumbColor: AppColors.cyan,
              overlayColor: AppColors.cyan.withOpacity(0.15),
              trackHeight: 3,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
            ),
            child: Slider(
              value: _questionCount.toDouble(),
              min: 5,
              max: 20,
              divisions: 15,
              onChanged: (v) => setState(() => _questionCount = v.round()),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDifficultyRow() {
    return Row(
      children: [
        _difficultyPill('Hard', 'quiz_difficulty_hard'.tr, Colors.red.shade400),
        const SizedBox(width: 8),
        _difficultyPill(
            'Medium', 'quiz_difficulty_medium'.tr, AppColors.textPrimary),
        const SizedBox(width: 8),
        _difficultyPill('Easy', 'quiz_difficulty_easy'.tr, AppColors.green),
      ],
    );
  }

  Widget _difficultyPill(String value, String label, Color color) {
    final selected = _difficulty == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _difficulty = value),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          height: 42,
          decoration: BoxDecoration(
            color: selected ? color.withOpacity(0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(21),
            border: Border.all(
              color: selected ? color : AppColors.borderDefault,
              width: selected ? 1.5 : 1,
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              color: selected ? color : AppColors.textMuted,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStartButton() {
    return GestureDetector(
      onTap: () {
        c.questionCount = _questionCount;
        c.difficulty = _difficulty;
        c.selectedChapter = _selectedChapter;
        c.startQuiz();
      },
      child: Container(
        height: 54,
        decoration: BoxDecoration(
          gradient: AppColors.gradientPurple,
          borderRadius: BorderRadius.circular(14),
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 22),
            const SizedBox(width: 8),
            Text(
              'quiz_start'.tr,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ArrowUpPainter extends CustomPainter {
  final Color color;
  const _ArrowUpPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color;
    final path = Path()
      ..moveTo(0, size.height)
      ..lineTo(size.width / 2, 0)
      ..lineTo(size.width, size.height)
      ..close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_) => false;
}
