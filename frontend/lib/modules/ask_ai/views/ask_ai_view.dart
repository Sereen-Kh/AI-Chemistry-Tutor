import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../data/models/chat_message_model.dart';
import '../controllers/ask_ai_controller.dart';
import '../../main_nav/controllers/main_nav_controller.dart';

class AskAiView extends GetView<AskAiController> {
  const AskAiView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          // Messages list
          Expanded(
            child: Obx(() => ListView.builder(
                  controller: controller.scrollController,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  itemCount: controller.messages.length +
                      (controller.isTyping.value ? 1 : 0),
                  itemBuilder: (_, i) {
                    if (i == controller.messages.length &&
                        controller.isTyping.value) {
                      return const _TypingIndicator();
                    }
                    return _MessageBubble(msg: controller.messages[i]);
                  },
                )),
          ),

          // Teaching style toggle
          Container(
            color: AppColors.bgBase,
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Obx(() => Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                     Text(
                      'ask_ai_teaching_style'.tr,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 10,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(width: 12),
                    _StyleChip(
                      label: 'ask_ai_socratic'.tr,
                      icon: Icons.psychology_outlined,
                      active: controller.teachingStyle.value == 'Socratic',
                      onTap: () => controller.setStyle('Socratic'),
                    ),
                    const SizedBox(width: 8),
                    _StyleChip(
                      label: 'ask_ai_direct'.tr,
                      icon: Icons.flash_on_outlined,
                      active: controller.teachingStyle.value == 'Direct',
                      onTap: () => controller.setStyle('Direct'),
                    ),
                  ],
                )),
          ),

          // Input bar
          Container(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
            color: AppColors.bgCard,
            child: Row(
              children: [
                GestureDetector(
                  onTap: () {},
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.bgCardAlt,
                      border: Border.all(color: AppColors.borderDefault),
                    ),
                    child:  Icon(Icons.add,
                        color: AppColors.textSecondary, size: 18),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: controller.messageController,
                    style:  TextStyle(
                        color: AppColors.textPrimary, fontSize: 14),
                    decoration: InputDecoration(
                      hintText: 'ask_ai_hint'.tr,
                      hintStyle: TextStyle(
                          color: AppColors.textMuted, fontSize: 14),
                      border: InputBorder.none,
                      isDense: true,
                      contentPadding: EdgeInsets.zero,
                    ),
                    onSubmitted: (_) => controller.sendMessage(),
                  ),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTap: controller.sendMessage,
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: AppColors.gradientPurple,
                    ),
                    child: const Icon(Icons.send_rounded,
                        color: Colors.white, size: 16),
                  ),
                ),
              ],
            ),
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
        padding: const EdgeInsets.all(6),
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
          padding: const EdgeInsets.all(6),
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
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage msg;
  const _MessageBubble({required this.msg});

  @override
  Widget build(BuildContext context) {
    if (msg.isBot) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
             Text(
              'ask_ai_bot_name'.tr,
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 10,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 6),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 3,
                  height: null,
                  constraints: const BoxConstraints(minHeight: 40),
                  decoration: BoxDecoration(
                    color: AppColors.cyan,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 10),
                Flexible(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: msg.content.split('\n\n').map((part) {
                      final isFormula = part.contains('→') || part.contains('H₂');
                      if (isFormula) {
                        return Container(
                          margin: const EdgeInsets.only(top: 6),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10),
                          decoration: BoxDecoration(
                            color: AppColors.bgDeep,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                                color: AppColors.borderDefault),
                          ),
                          child: Text(
                            part,
                            style:  TextStyle(
                              color: AppColors.cyan,
                              fontSize: 15,
                              fontFamily: 'monospace',
                              letterSpacing: 1,
                            ),
                          ),
                        );
                      }
                      return Text(
                        part,
                        style:  TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 14,
                          height: 1.5,
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    }

    // User bubble
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.70,
            ),
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.purple,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Text(
              msg.content,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ),
          if (msg.isRead)
            Padding(
              padding: const EdgeInsets.only(top: 4, right: 4),
              child: Text(
                'READ ${msg.time}',
                style:  TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 10,
                  letterSpacing: 0.8,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _TypingIndicator extends StatelessWidget {
  const _TypingIndicator();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 3,
            height: 28,
            decoration: BoxDecoration(
              color: AppColors.cyan,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 10),
          const _DotRow(),
        ],
      ),
    );
  }
}

class _DotRow extends StatefulWidget {
  const _DotRow();

  @override
  State<_DotRow> createState() => _DotRowState();
}

class _DotRowState extends State<_DotRow> with SingleTickerProviderStateMixin {
  late final AnimationController _ac;

  @override
  void initState() {
    super.initState();
    _ac = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900))
      ..repeat();
  }

  @override
  void dispose() {
    _ac.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ac,
      builder: (_, __) {
        return Row(
          children: List.generate(3, (i) {
            final opacity =
                (((_ac.value * 3 - i) % 3 + 3) % 3 < 1) ? 1.0 : 0.3;
            return Padding(
              padding: const EdgeInsets.only(right: 5),
              child: Opacity(
                opacity: opacity,
                child:  CircleAvatar(
                    radius: 4, backgroundColor: AppColors.textSecondary),
              ),
            );
          }),
        );
      },
    );
  }
}

class _StyleChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  const _StyleChip({
    required this.label,
    required this.icon,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: active ? AppColors.purple : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: active ? AppColors.purple : AppColors.borderDefault,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon,
                size: 13,
                color: active
                    ? Colors.white
                    : AppColors.textMuted),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                color: active ? Colors.white : AppColors.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
