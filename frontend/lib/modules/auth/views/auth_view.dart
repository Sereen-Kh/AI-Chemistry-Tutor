import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../../../widgets/kimo_widget.dart';
import '../controllers/auth_controller.dart';

class AuthView extends GetView<AuthController> {
  const AuthView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF070A1C),
      body: Stack(
        children: [
          // Background glow
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.5),
                  radius: 0.80,
                  colors: [
                    AppColors.purple.withOpacity(0.22),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  const SizedBox(height: 24),

                  // ── Kimo + tab switcher ─────────────────────────────────
                  _KimoHeader(controller: controller)
                      .animate()
                      .fadeIn(duration: 600.ms)
                      .slideY(begin: -0.1),

                  const SizedBox(height: 24),

                  // ── Tab switcher: Login / Sign Up ───────────────────────
                  _TabBar(controller: controller)
                      .animate()
                      .fadeIn(delay: 150.ms, duration: 500.ms),

                  const SizedBox(height: 20),

                  // ── Form card ───────────────────────────────────────────
                  Obx(() => _FormCard(
                        controller: controller,
                        isLogin: controller.isLoginTab.value,
                      )).animate().fadeIn(delay: 250.ms, duration: 500.ms).slideY(begin: 0.06),

                  const SizedBox(height: 20),

                  // ── Divider ─────────────────────────────────────────────
                  Row(
                    children: [
                      Expanded(child: Divider(color: AppColors.borderDefault, height: 1)),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        child: Text('auth_or'.tr, style: TextStyle(color: AppColors.textMuted, fontSize: 10, letterSpacing: 2)),
                      ),
                      Expanded(child: Divider(color: AppColors.borderDefault, height: 1)),
                    ],
                  ).animate().fadeIn(delay: 380.ms),

                  const SizedBox(height: 18),

                  // ── Google SSO ──────────────────────────────────────────
                  GestureDetector(
                    onTap: () {},
                    child: Container(
                      width: double.infinity,
                      height: 50,
                      decoration: BoxDecoration(
                        color: AppColors.bgCard,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: AppColors.borderDefault),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text('G', style: TextStyle(color: Color(0xFF4285F4), fontSize: 18, fontWeight: FontWeight.w800)),
                          const SizedBox(width: 10),
                          Text('auth_google'.tr, style: TextStyle(color: AppColors.textPrimary, fontSize: 14, fontWeight: FontWeight.w500)),
                        ],
                      ),
                    ),
                  ).animate().fadeIn(delay: 450.ms),

                  const SizedBox(height: 24),

                  // ── Toggle link ─────────────────────────────────────────
                  Obx(() => Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            controller.isLoginTab.value ? 'auth_new_to'.tr : 'auth_already_have'.tr,
                            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                          ),
                          GestureDetector(
                            onTap: controller.toggleTab,
                            child: Text(
                              controller.isLoginTab.value ? 'auth_sign_up_link'.tr : 'auth_login_link'.tr,
                              style: TextStyle(color: AppColors.purple, fontSize: 13, fontWeight: FontWeight.w700),
                            ),
                          ),
                        ],
                      )).animate().fadeIn(delay: 500.ms),

                  const SizedBox(height: 32),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Kimo header ───────────────────────────────────────────────────────────────
class _KimoHeader extends StatelessWidget {
  final AuthController controller;
  const _KimoHeader({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Obx(() => KimoWidget(
              size: 100,
              state: controller.isLoginTab.value ? KimoState.happy : KimoState.celebrating,
            )),
        const SizedBox(height: 14),
        Obx(() => Text(
              controller.isLoginTab.value ? 'auth_welcome_back'.tr : 'auth_join_lab'.tr,
              style: TextStyle(color: Color(0xFFFFE8F3), fontSize: 20, fontWeight: FontWeight.w800),
            )),
        const SizedBox(height: 6),
        Text(
          'auth_platform'.tr,
          style: TextStyle(color: AppColors.textMuted, fontSize: 11, letterSpacing: 1.2),
        ),
      ],
    );
  }
}

// ── Login / Sign Up tab bar ───────────────────────────────────────────────────
class _TabBar extends StatelessWidget {
  final AuthController controller;
  const _TabBar({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Container(
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Row(
            children: [
              _Tab(label: 'auth_login'.tr, active: controller.isLoginTab.value, onTap: () => controller.isLoginTab.value = true),
              _Tab(label: 'auth_signup'.tr, active: !controller.isLoginTab.value, onTap: () => controller.isLoginTab.value = false),
            ],
          ),
        ));
  }
}

class _Tab extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;
  const _Tab({required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            gradient: active ? AppColors.gradientPurple : null,
            borderRadius: BorderRadius.circular(10),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              color: active ? Colors.white : AppColors.textSecondary,
              fontSize: 14,
              fontWeight: active ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}

// ── Form card ─────────────────────────────────────────────────────────────────
class _FormCard extends StatelessWidget {
  final AuthController controller;
  final bool isLogin;
  const _FormCard({required this.controller, required this.isLogin});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isLogin) ...[
            _FieldLabel('auth_fullname'.tr),
            const SizedBox(height: 8),
            _InputField(
              controller: controller.nameController,
              hint: 'Marie Curie',
              icon: Icons.person_outline,
            ),
            const SizedBox(height: 18),
          ],

          _FieldLabel('auth_email'.tr),
          const SizedBox(height: 8),
          _InputField(
            controller: controller.emailController,
            hint: 'scientist@chem.ai',
            icon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
          ),

          const SizedBox(height: 18),

          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _FieldLabel('auth_password'.tr),
              if (isLogin)
                GestureDetector(
                  onTap: () {},
                  child: Text('auth_forgot'.tr, style: const TextStyle(color: Color(0xFFFBBF24), fontSize: 12, fontWeight: FontWeight.w600)),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Obx(() => _InputField(
                controller: controller.passwordController,
                hint: '•••••••••••',
                icon: Icons.lock_outline,
                obscure: !controller.isPasswordVisible.value,
                suffix: GestureDetector(
                  onTap: controller.togglePasswordVisibility,
                  child: Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: Icon(
                      controller.isPasswordVisible.value ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      color: AppColors.textSecondary,
                      size: 18,
                    ),
                  ),
                ),
              )),

          if (isLogin) ...[
            const SizedBox(height: 16),
            Obx(() => GestureDetector(
                  onTap: controller.toggleRememberMe,
                  child: Row(
                    children: [
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 18,
                        height: 18,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: controller.rememberMe.value ? AppColors.purple : AppColors.borderDefault),
                          color: controller.rememberMe.value ? AppColors.purple : Colors.transparent,
                        ),
                        child: controller.rememberMe.value ? const Icon(Icons.check, size: 12, color: Colors.white) : null,
                      ),
                      const SizedBox(width: 10),
                      Text('auth_remember_me'.tr, style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                    ],
                  ),
                )),
          ],

          const SizedBox(height: 22),

          Obx(() => GestureDetector(
                onTap: controller.isLoading.value ? controller.login : controller.register,
                child: Container(
                  width: double.infinity,
                  height: 52,
                  decoration: BoxDecoration(
                    gradient: AppColors.gradientPurple,
                    borderRadius: BorderRadius.circular(30),
                  ),
                  alignment: Alignment.center,
                  child: controller.isLoading.value
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : Text(
                          isLogin ? 'auth_enter_lab'.tr : 'auth_create_account'.tr,
                          style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700),
                        ),
                ),
              )),
        ],
      ),
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String text;
  const _FieldLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(text, style: TextStyle(color: AppColors.textSecondary, fontSize: 12, fontWeight: FontWeight.w600));
  }
}

class _InputField extends StatelessWidget {
  final TextEditingController controller;
  final String hint;
  final IconData icon;
  final bool obscure;
  final Widget? suffix;
  final TextInputType? keyboardType;

  const _InputField({
    required this.controller,
    required this.hint,
    required this.icon,
    this.obscure = false,
    this.suffix,
    this.keyboardType,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.bgCardAlt,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscure,
        keyboardType: keyboardType,
        style: TextStyle(color: AppColors.textPrimary, fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(color: AppColors.textMuted, fontSize: 14),
          prefixIcon: Icon(icon, color: AppColors.textSecondary, size: 18),
          suffixIcon: suffix,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
        ),
      ),
    );
  }
}
