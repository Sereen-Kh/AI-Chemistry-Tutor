import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../core/controllers/theme_controller.dart';
import '../../../widgets/app_drawer.dart';
import '../../ask_ai/views/ask_ai_view.dart';
import '../../home/views/home_view.dart';
import '../../lessons/views/lessons_view.dart';
import '../../pilot_profile/views/pilot_profile_view.dart';
import '../../reels/views/reels_view.dart';
import '../controllers/main_nav_controller.dart';

class MainNavView extends GetView<MainNavController> {
  const MainNavView({super.key});

  static List<Widget> get _pages => [
        HomeView(),
        LessonsView(),
        ReelsView(),
        AskAiView(),
        PilotProfileView(),
      ];

  @override
  Widget build(BuildContext context) {
    final tc = Get.find<ThemeController>();
    return Obx(() {
      tc.isDark.value; // subscribe for theme rebuilds
      return Scaffold(
        key: controller.scaffoldKey,
        backgroundColor: AppColors.bgBase,
        drawer: const AppDrawer(),
        body: IndexedStack(
          index: controller.currentIndex.value,
          children: _pages,
        ),
        bottomNavigationBar: _QuantumNavBar(
          currentIndex: controller.currentIndex.value,
          onTap: controller.changeTab,
        ),
      );
    });
  }
}

// ── Bottom navigation bar ─────────────────────────────────────────────────────
class _QuantumNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const _QuantumNavBar({required this.currentIndex, required this.onTap});

  static List<_NavItem> get _items => [
    _NavItem(Icons.home_rounded,          Icons.home_outlined,           'nav_home'.tr),
    _NavItem(Icons.book_rounded,           Icons.book_outlined,           'nav_lessons'.tr),
    _NavItem(Icons.video_library_rounded,  Icons.video_library_outlined,  'nav_reels'.tr),
    _NavItem(Icons.smart_toy_rounded,      Icons.smart_toy_outlined,      'nav_chat'.tr),
    _NavItem(Icons.person_rounded,         Icons.person_outline,          'nav_profile'.tr),
  ];

  @override
  Widget build(BuildContext context) {
    final bottomPad = MediaQuery.of(context).padding.bottom;
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgDeep,
        border: Border(
          top: BorderSide(color: AppColors.borderDefault),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 62,
          child: Row(
            children: List.generate(_items.length, (i) {
              final item = _items[i];
              final isActive = i == currentIndex;
              return Expanded(
                child: GestureDetector(
                  onTap: () => onTap(i),
                  behavior: HitTestBehavior.opaque,
                  child: _NavTabItem(
                    item: item,
                    isActive: isActive,
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}

class _NavItem {
  final IconData activeIcon;
  final IconData inactiveIcon;
  final String label;
  const _NavItem(this.activeIcon, this.inactiveIcon, this.label);
}

class _NavTabItem extends StatelessWidget {
  final _NavItem item;
  final bool isActive;
  const _NavTabItem({required this.item, required this.isActive});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Gradient top indicator
        AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
          height: 2,
          width: isActive ? 36 : 0,
          decoration: BoxDecoration(
            gradient: isActive ? AppColors.gradientPurple : null,
            borderRadius: const BorderRadius.only(
              bottomLeft: Radius.circular(2),
              bottomRight: Radius.circular(2),
            ),
          ),
        ),

        const Spacer(),

        // Icon with optional glow
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: isActive
              ? ShaderMask(
                  key: const ValueKey('active'),
                  shaderCallback: (b) =>
                      AppColors.gradientPurple.createShader(b),
                  blendMode: BlendMode.srcIn,
                  child: Icon(item.activeIcon, size: 24, color: Colors.white),
                )
              : Icon(
                  key: const ValueKey('inactive'),
                  item.inactiveIcon,
                  size: 22,
                  color: AppColors.textMuted,
                ),
        ),

        const SizedBox(height: 4),

        // Label
        AnimatedDefaultTextStyle(
          duration: const Duration(milliseconds: 200),
          style: TextStyle(
            color: isActive ? AppColors.purpleLight : AppColors.textMuted,
            fontSize: 9,
            fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
            letterSpacing: 0.4,
          ),
          child: Text(item.label),
        ),

        const Spacer(),
      ],
    );
  }
}
