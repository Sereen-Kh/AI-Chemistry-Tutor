import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../core/controllers/explanation_style_controller.dart';
import '../controllers/pilot_profile_controller.dart';
import '../../main_nav/controllers/main_nav_controller.dart';
class PilotProfileView extends GetView<PilotProfileController> {
  const PilotProfileView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _AvatarHeroSection(),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Expanded(
                    child: Text(
                      controller.name,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  // Container(
                  //   padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  //   decoration: BoxDecoration(
                  //     color: AppColors.amber,
                  //     borderRadius: BorderRadius.circular(20),
                  //   ),
                  //   child: Text(
                  //     'Level ${controller.level}',
                  //     style: const TextStyle(
                  //       color: Colors.white,
                  //       fontSize: 12,
                  //       fontWeight: FontWeight.w700,
                  //     ),
                  //   ),
                  // ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Text(
                'pilot_member_since'.tr,
                style: TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(height: 16),
            _ProSubscriptionCard(
              planName: controller.planName,
              planExpiry: controller.planExpiry,
            ),
            const SizedBox(height: 16),
            _StatsRow(),
            const SizedBox(height: 16),
            _SettingsSection(controller: controller),
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: GestureDetector(
                onTap: controller.disconnect,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: AppColors.danger.withOpacity(0.35),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.logout_rounded, color: AppColors.danger, size: 18),
                      const SizedBox(width: 10),
                      Text(
                        'pilot_sign_out'.tr,
                        style: TextStyle(
                          color: AppColors.danger,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
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

class _AvatarHeroSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      decoration: BoxDecoration(
        color: const Color(0xFF0D0F1A),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Stack(
        children: [
          Container(
            height: 200,
            width: double.infinity,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  const Color(0xFF0D0F1A),
                  const Color(0xFF1A1030),
                ],
              ),
            ),
            child: Center(
              child: Icon(
                Icons.person,
                size: 80,
                color: AppColors.purple,
              ),
            ),
          ),
          // Positioned(
          //   bottom: 12,
          //   right: 12,
          //   child: Container(
          //     padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          //     decoration: BoxDecoration(
          //       color: const Color(0xFF1E2040),
          //       borderRadius: BorderRadius.circular(10),
          //       border: Border.all(color: AppColors.borderDefault),
          //     ),
          //     child: Row(
          //       mainAxisSize: MainAxisSize.min,
          //       children: [
          //         const Text('✏', style: TextStyle(fontSize: 11)),
          //         const SizedBox(width: 4),
          //         Text(
          //           'pilot_edit_appearance'.tr,
          //           style: TextStyle(
          //             color: AppColors.textPrimary,
          //             fontSize: 11,
          //             fontWeight: FontWeight.w600,
          //           ),
          //         ),
          //       ],
          //     ),
          //   ),
          // ),
        ],
      ),
    );
  }
}

class _ProSubscriptionCard extends StatelessWidget {
  final String planName;
  final String planExpiry;

  const _ProSubscriptionCard({
    required this.planName,
    required this.planExpiry,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF6B21A8),
            const Color(0xFF4C1D95),
          ],
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'pilot_renew'.tr,
              style: TextStyle(
                color: const Color(0xFF6B21A8),
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.star_rounded, color: Color(0xFFFBBF24), size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        planName,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  planExpiry,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: [
          Expanded(
            child: _StatBox(
              icon: Icons.my_location_rounded,
              iconColor: AppColors.green,
              value: '88%',
              label: 'pilot_accuracy'.tr,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _StatBox(
              icon: Icons.local_fire_department_rounded,
              iconColor: const Color(0xFFF97316),
              value: '12',
              label: 'pilot_streak_days'.tr,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _StatBox(
              icon: Icons.bolt_rounded,
              iconColor: const Color(0xFFFBBF24),
              value: '1,240',
              label: 'pilot_xp_points'.tr,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatBox extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String value;
  final String label;

  const _StatBox({
    required this.icon,
    required this.iconColor,
    required this.value,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        children: [
          Icon(icon, color: iconColor, size: 22),
          const SizedBox(height: 6),
          Text(
            value,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 10,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  final PilotProfileController controller;

  const _SettingsSection({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.borderDefault),
        ),
        child: Column(
          children: [
            Obx(() => _NotificationsRow(
              isOn: controller.notifications.value,
              onToggle: controller.toggleNotifications,
            )),
            Divider(height: 1, color: AppColors.borderDefault, indent: 48),
            Obx(() => _SettingDetailRow(
                  icon: Icons.school_outlined,
                  iconColor: AppColors.purple,
                  label: 'pilot_learning_method'.tr,
                  subtitle: controller.mentorSubtitle.value,
                  onTap: controller.openMentorPicker,
                )),
            Divider(height: 1, color: AppColors.borderDefault, indent: 48),
            Obx(() {
              final esc = Get.find<ExplanationStyleController>();
              esc.selectedId.value;
              return _SettingDetailRow(
                icon: Icons.psychology_outlined,
                iconColor: AppColors.cyan,
                label: 'pilot_explanation_style'.tr,
                subtitle: esc.displayLabel,
                onTap: controller.openExplanationStylePicker,
              );
            }),
          ],
        ),
      ),
    );
  }
}

class _NotificationsRow extends StatelessWidget {
  final bool isOn;
  final VoidCallback onToggle;

  const _NotificationsRow({required this.isOn, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: AppColors.purple.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(Icons.notifications_outlined, color: AppColors.purple, size: 18),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              'pilot_study_notifications'.tr,
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 14,
              ),
            ),
          ),
          Switch(
            value: isOn,
            onChanged: (_) => onToggle(),
            activeColor: AppColors.purple,
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ],
      ),
    );
  }
}

class _SettingDetailRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String label;
  final String subtitle;
  final VoidCallback? onTap;

  const _SettingDetailRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.subtitle,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: iconColor, size: 18),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 2),
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
          Icon(Icons.chevron_left, color: AppColors.textMuted, size: 18),
        ],
      ),
    ),
    );
  }
}
