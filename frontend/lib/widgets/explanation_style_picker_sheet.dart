import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../app/theme/app_colors.dart';
import '../core/controllers/explanation_style_controller.dart';
import '../core/explanation/explanation_style.dart';

class ExplanationStylePickerSheet extends StatelessWidget {
  final String selectedId;
  final ValueChanged<String> onSelect;

  const ExplanationStylePickerSheet({
    super.key,
    required this.selectedId,
    required this.onSelect,
  });

  static Future<void> show({required String selectedId}) async {
    final controller = Get.find<ExplanationStyleController>();
    await Get.bottomSheet<void>(
      ExplanationStylePickerSheet(
        selectedId: selectedId,
        onSelect: (id) async {
          await controller.setStyle(id);
          Get.back();
          Get.snackbar(
            'explanation_style_saved_title'.tr,
            'explanation_style_saved_body'.tr,
            snackPosition: SnackPosition.BOTTOM,
            duration: const Duration(seconds: 2),
          );
        },
      ),
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 24),
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.textMuted.withOpacity(0.4),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'explanation_style_picker_title'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'explanation_style_picker_subtitle'.tr,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          ...ExplanationStyles.options.map((option) {
            final isSelected = option.id == selectedId;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => onSelect(option.id),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? AppColors.purple.withOpacity(0.12)
                          : AppColors.bgBase,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isSelected
                            ? AppColors.purple
                            : AppColors.borderDefault,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(option.icon,
                            color: isSelected
                                ? AppColors.purple
                                : AppColors.textSecondary,
                            size: 22),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            option.labelKey.tr,
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 15,
                              fontWeight: isSelected
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                            ),
                          ),
                        ),
                        if (isSelected)
                          Icon(Icons.check_circle_rounded,
                              color: AppColors.purple, size: 20),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
