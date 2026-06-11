import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../app/theme/app_colors.dart';
import '../core/controllers/explanation_style_controller.dart';
import '../core/explanation/explanation_style.dart';

/// Horizontal chips to switch explanation style (e.g. on lesson detail).
class ExplanationStyleChips extends StatelessWidget {
  const ExplanationStyleChips({super.key});

  @override
  Widget build(BuildContext context) {
    final esc = Get.find<ExplanationStyleController>();
    return Obx(() {
      esc.selectedId.value;
      return SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: ExplanationStyles.options.map((option) {
            final isSelected = esc.selectedId.value == option.id;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: GestureDetector(
                onTap: () => esc.setStyle(option.id),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.purple.withOpacity(0.15)
                        : AppColors.bgCard,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: isSelected
                          ? AppColors.purple
                          : AppColors.borderDefault,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        option.icon,
                        size: 16,
                        color: isSelected
                            ? AppColors.purple
                            : AppColors.textMuted,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        option.labelKey.tr,
                        style: TextStyle(
                          color: isSelected
                              ? AppColors.textPrimary
                              : AppColors.textMuted,
                          fontSize: 12,
                          fontWeight: isSelected
                              ? FontWeight.w700
                              : FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      );
    });
  }
}
