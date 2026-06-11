import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../app/theme/app_colors.dart';
import '../core/controllers/theme_controller.dart';

class ThemePicker extends StatelessWidget {
  const ThemePicker({super.key});

  static void show() {
    Get.bottomSheet(
      const ThemePicker(),
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    final tc = Get.find<ThemeController>();
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: AppColors.borderDefault),
      ),
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.textMuted,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 20),

          // Title
          Text(
            'theme_picker_title'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 17,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 20),

          // Theme cards row
          Obx(() => Row(
                children: [
                  _ThemeCard(
                    name: 'theme_tutor_name'.tr,
                    desc: 'theme_tutor_desc'.tr,
                    accentA: AppColors.tutorPreviewDark,
                    accentB: const Color(0xFF22D3EE),
                    bgColor: AppColors.tutorPreviewLight,
                    selected: tc.chemTheme.value == ChemTheme.tutor,
                    onTap: () => tc.setTheme(ChemTheme.tutor),
                  ),
                  const SizedBox(width: 12),
                  _ThemeCard(
                    name: 'theme_luna_name'.tr,
                    desc: 'theme_luna_desc'.tr,
                    accentA: AppColors.lunaPreviewPink,
                    accentB: const Color(0xFFFF9EC5),
                    bgColor: AppColors.lunaPreviewDeep,
                    selected: tc.chemTheme.value == ChemTheme.luna,
                    onTap: () => tc.setTheme(ChemTheme.luna),
                  ),
                  const SizedBox(width: 12),
                  _ThemeCard(
                    name: 'theme_milo_name'.tr,
                    desc: 'theme_milo_desc'.tr,
                    accentA: AppColors.miloPreviewGreen,
                    accentB: const Color(0xFF22D3EE),
                    bgColor: AppColors.miloPreviewDeep,
                    selected: tc.chemTheme.value == ChemTheme.milo,
                    onTap: () => tc.setTheme(ChemTheme.milo),
                  ),
                ],
              )),

          const SizedBox(height: 20),

          // Dark / Light toggle row
          Obx(() => Container(
                decoration: BoxDecoration(
                  color: AppColors.bgCardAlt,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                child: Row(
                  children: [
                    _ModeBtn(
                      icon: Icons.dark_mode_rounded,
                      label: 'theme_dark_label'.tr,
                      active: tc.isDark.value,
                      onTap: () { if (!tc.isDark.value) tc.toggleDark(); },
                    ),
                    _ModeBtn(
                      icon: Icons.light_mode_rounded,
                      label: 'theme_light_label'.tr,
                      active: !tc.isDark.value,
                      onTap: () { if (tc.isDark.value) tc.toggleDark(); },
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

class _ThemeCard extends StatelessWidget {
  final String name;
  final String desc;
  final Color accentA;
  final Color accentB;
  final Color bgColor;
  final bool selected;
  final VoidCallback onTap;

  const _ThemeCard({
    required this.name,
    required this.desc,
    required this.accentA,
    required this.accentB,
    required this.bgColor,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selected ? accentA : AppColors.borderDefault,
              width: selected ? 2.5 : 1,
            ),
            boxShadow: selected
                ? [BoxShadow(color: accentA.withOpacity(0.4), blurRadius: 12)]
                : [],
          ),
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Mini palette preview
              Row(
                children: [
                  _Dot(accentA),
                  const SizedBox(width: 6),
                  _Dot(accentB),
                  const Spacer(),
                  if (selected)
                    Icon(Icons.check_circle_rounded, color: accentA, size: 16),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                name,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                desc,
                style: const TextStyle(
                  color: Colors.white60,
                  fontSize: 10,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  final Color color;
  const _Dot(this.color);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 16,
      height: 16,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

class _ModeBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _ModeBtn({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.purple;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.all(4),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: active ? accent.withOpacity(0.15) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon,
                  size: 16,
                  color: active ? accent : AppColors.textSecondary),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: active ? accent : AppColors.textSecondary,
                  fontSize: 13,
                  fontWeight: active ? FontWeight.w700 : FontWeight.w400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
