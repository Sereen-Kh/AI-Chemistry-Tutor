import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../app/routes/app_routes.dart';
import '../../../data/models/auth_model.dart';
import '../../../services/auth_service.dart';

class AuthController extends GetxController {
  final AuthService _service = Get.find<AuthService>();

  // ── Form controllers ───────────────────────────────────────────────────────
  final emailController    = TextEditingController();
  final passwordController = TextEditingController();
  final nameController     = TextEditingController();

  // Forgot / reset password
  final resetTokenController   = TextEditingController();
  final newPasswordController  = TextEditingController();

  // ── State ──────────────────────────────────────────────────────────────────
  final gender            = 'female'.obs;
  final isPasswordVisible = false.obs;
  final rememberMe        = false.obs;
  final isLoading         = false.obs;
  final isLoginTab        = true.obs;

  void toggleTab()               => isLoginTab.value = !isLoginTab.value;
  void setGender(String g)       => gender.value = g;
  void togglePasswordVisibility() => isPasswordVisible.value = !isPasswordVisible.value;
  void toggleRememberMe()         => rememberMe.value = !rememberMe.value;

  @override
  void onClose() {
    emailController.dispose();
    passwordController.dispose();
    nameController.dispose();
    resetTokenController.dispose();
    newPasswordController.dispose();
    super.onClose();
  }

  // ── Register ────────────────────────────────────────────────────────────────

  Future<void> register() async {
    final name  = nameController.text.trim();
    final email = emailController.text.trim();
    final pass  = passwordController.text;

    if (name.isEmpty || email.isEmpty || pass.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    isLoading.value = true;

    try {
      final res = await _service.register(RegisterRequest(
        fullName: name,
        email:    email,
        password: pass,
        gender:   gender.value,
      ));

      if (res == null) {
        _snack('register_failed'.tr, 'try_again_later'.tr);
        return;
      }
      // Account created — show success then switch to Login tab
      Get.offAllNamed(AppRoutes.onboarding);
      _snack('register_success'.tr, res.accessToken);
      passwordController.clear();
      nameController.clear();
      isLoginTab.value = true;
    } on Exception catch (e) {
      _snack('register_failed'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── Login ────────────────────────────────────────────────────────────────

  Future<void> login() async {
    final email = emailController.text.trim();
    final pass  = passwordController.text;

    if (email.isEmpty || pass.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    isLoading.value = true;

    try {
      final res = await _service.login(LoginRequest(email: email, password: pass));

      if (res == null) {
        _snack('login_failed'.tr, 'try_again_later'.tr);
        return;
      }
      await _saveToken(res.accessToken);
      Get.offAllNamed(AppRoutes.onboarding);
    } on Exception catch (e) {
      _snack('login_failed'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── Logout ───────────────────────────────────────────────────────────────

  Future<void> logout() async {
    isLoading.value = true;
    await _service.logout();
    await _clearSession();
    isLoading.value = false;
    Get.offAllNamed(AppRoutes.auth);
  }

  // ── Forgot password ───────────────────────────────────────────────────────

  Future<void> forgotPassword() async {
    final email = emailController.text.trim();

    if (email.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    isLoading.value = true;

    try {
      final res = await _service.forgotPassword(ForgotPasswordRequest(email: email));
      if (res != null) {
        _snack('auth_email_sent'.tr, res.message);
        Get.back();
      } else {
        _snack('error'.tr, 'try_again_later'.tr);
      }
    } on Exception catch (e) {
      _snack('error'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── Reset password ─────────────────────────────────────────────────────────

  Future<void> resetPassword() async {
    final token   = resetTokenController.text.trim();
    final newPass = newPasswordController.text;

    if (token.isEmpty || newPass.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    isLoading.value = true;

    try {
      final res = await _service.resetPassword(
        ResetPasswordRequest(token: token, newPassword: newPass),
      );
      if (res != null) {
        _snack('auth_password_reset'.tr, res.message);
        Get.offAllNamed(AppRoutes.auth);
      } else {
        _snack('error'.tr, 'try_again_later'.tr);
      }
    } on Exception catch (e) {
      _snack('error'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('logged_in', true);
    await prefs.setString('access_token', token);
  }

  Future<void> _clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('logged_in');
    await prefs.remove('access_token');
  }

  void _snack(String title, String msg) =>
      Get.snackbar(title, msg, snackPosition: SnackPosition.BOTTOM);
}