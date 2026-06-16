import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../../app/routes/app_routes.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../main_nav/controllers/main_nav_controller.dart';

class _Action {
  final IconData icon;
  final String label;
  final String? route;
  final int? navTab; // switch main nav tab instead of pushing route
  const _Action(this.icon, this.label, {this.route, this.navTab});
}

const _actions = [
  _Action(Icons.quiz_outlined, 'DAILY QUIZ', route: AppRoutes.quiz),
  _Action(Icons.calendar_today_outlined, 'SCHEDULE', navTab: 3),
  _Action(Icons.style_outlined, 'CARDS', route: AppRoutes.flashcards),
  _Action(Icons.psychology_outlined, 'AI HELP', navTab: 2),
];

class QuickActionGrid extends StatelessWidget {
  const QuickActionGrid({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: List.generate(
        _actions.length,
        (i) => _ActionItem(action: _actions[i], index: i),
      ),
    );
  }
}

class _ActionItem extends StatelessWidget {
  final _Action action;
  final int index;
  const _ActionItem({required this.action, required this.index});

  void _onTap() {
    if (action.navTab != null) {
      Get.find<MainNavController>().changeTab(action.navTab!);
    } else if (action.route != null) {
      Get.toNamed(action.route!);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        GestureDetector(
          onTap: _onTap,
          child: Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Icon(action.icon,
                color: AppColors.textSecondary, size: 22),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          action.label,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 9,
            letterSpacing: 0.8,
          ),
        ),
      ],
    )
        .animate(delay: Duration(milliseconds: 60 * index))
        .fadeIn(duration: 300.ms)
        .slideY(begin: 0.2, duration: 300.ms);
  }
}
