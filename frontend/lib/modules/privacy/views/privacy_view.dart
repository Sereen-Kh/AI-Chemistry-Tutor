import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/privacy_controller.dart';

class PrivacyView extends GetView<PrivacyController> {
  const PrivacyView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        title: Text(
          'privacy_title'.tr,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 12,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.8,
          ),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios, color: AppColors.textSecondary, size: 18),
          onPressed: Get.back,
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.purple.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.shield_outlined, color: AppColors.purple, size: 24),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('privacy_settings'.tr,
                        style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 18,
                            fontWeight: FontWeight.w700)),
                    Text('privacy_subtitle'.tr,
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 12)),
                  ],
                ),
              ],
            ).animate().fadeIn(duration: 400.ms),

            const SizedBox(height: 24),

            // Social privacy
            _SectionHeader('privacy_social'.tr),
            Obx(() => _ToggleRow(
                  icon: Icons.bar_chart_outlined,
                  title: 'privacy_share_progress'.tr,
                  subtitle: 'privacy_share_progress_sub'.tr,
                  value: controller.shareProgress.value,
                  onChanged: (_) => controller.toggle(controller.shareProgress),
                )),
            Obx(() => _ToggleRow(
                  icon: Icons.emoji_events_outlined,
                  title: 'privacy_leaderboard'.tr,
                  subtitle: 'privacy_leaderboard_sub'.tr,
                  value: controller.showInLeaderboard.value,
                  onChanged: (_) =>
                      controller.toggle(controller.showInLeaderboard),
                )),
            Obx(() => _ToggleRow(
                  icon: Icons.group_add_outlined,
                  title: 'privacy_squad_invites'.tr,
                  subtitle: 'privacy_squad_invites_sub'.tr,
                  value: controller.allowSquadInvites.value,
                  onChanged: (_) =>
                      controller.toggle(controller.allowSquadInvites),
                )),
            Obx(() => _ToggleRow(
                  icon: Icons.share_outlined,
                  title: 'privacy_share_achievements'.tr,
                  subtitle: 'privacy_share_achievements_sub'.tr,
                  value: controller.shareAchievements.value,
                  onChanged: (_) =>
                      controller.toggle(controller.shareAchievements),
                )),

            const SizedBox(height: 8),

            // Data & analytics
            _SectionHeader('privacy_data_analytics'.tr),
            Obx(() => _ToggleRow(
                  icon: Icons.analytics_outlined,
                  title: 'privacy_analytics'.tr,
                  subtitle: 'privacy_analytics_sub'.tr,
                  value: controller.analyticsEnabled.value,
                  onChanged: (_) =>
                      controller.toggle(controller.analyticsEnabled),
                )),
            Obx(() => _ToggleRow(
                  icon: Icons.bug_report_outlined,
                  title: 'privacy_crash_reports'.tr,
                  subtitle: 'privacy_crash_reports_sub'.tr,
                  value: controller.crashReportsEnabled.value,
                  onChanged: (_) =>
                      controller.toggle(controller.crashReportsEnabled),
                )),

            const SizedBox(height: 24),

            // Data management
            _SectionHeader('privacy_data_management'.tr),
            _ActionRow(
              icon: Icons.download_outlined,
              title: 'privacy_export_data'.tr,
              subtitle: 'privacy_export_data_sub'.tr,
              onTap: () => Get.snackbar('privacy_export_data'.tr, 'privacy_export_requested'.tr,
                  snackPosition: SnackPosition.BOTTOM),
            ),
            _ActionRow(
              icon: Icons.delete_outline,
              title: 'account_delete_title'.tr,
              subtitle: 'privacy_delete_sub'.tr,
              isDestructive: true,
              onTap: controller.deleteAccount,
            ),

            const SizedBox(height: 24),

            // Legal links
            _SectionHeader('privacy_legal'.tr),
            _LinkRow('privacy_policy'.tr, () {}),
            _LinkRow('privacy_terms'.tr, () {}),
            _LinkRow('privacy_cookies'.tr, () {}),

            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String text;
  const _SectionHeader(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Text(
        text,
        style: TextStyle(
          color: AppColors.textMuted,
          fontSize: 10,
          letterSpacing: 1.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _ToggleRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppColors.textSecondary, size: 18),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w500)),
                Text(subtitle,
                    style: TextStyle(
                        color: AppColors.textSecondary, fontSize: 11)),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: AppColors.purple,
          ),
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool isDestructive;
  final VoidCallback onTap;

  const _ActionRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.isDestructive = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final color = isDestructive ? AppColors.danger : AppColors.textSecondary;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: isDestructive
              ? AppColors.danger.withOpacity(0.05)
              : AppColors.bgCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: isDestructive
                  ? AppColors.danger.withOpacity(0.3)
                  : AppColors.borderDefault),
        ),
        child: Row(
          children: [
            Icon(icon, color: color, size: 18),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: TextStyle(
                          color: isDestructive
                              ? AppColors.danger
                              : AppColors.textPrimary,
                          fontSize: 14)),
                  Text(subtitle,
                      style: TextStyle(
                          color: AppColors.textSecondary, fontSize: 11)),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: AppColors.textMuted, size: 18),
          ],
        ),
      ),
    );
  }
}

class _LinkRow extends StatelessWidget {
  final String title;
  final VoidCallback onTap;
  const _LinkRow(this.title, this.onTap);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.borderDefault),
        ),
        child: Row(
          children: [
            Expanded(
                child: Text(title,
                    style: TextStyle(
                        color: AppColors.textPrimary, fontSize: 14))),
            Icon(Icons.open_in_new, color: AppColors.textMuted, size: 16),
          ],
        ),
      ),
    );
  }
}
