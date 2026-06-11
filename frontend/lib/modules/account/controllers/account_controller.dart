
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/routes/app_routes.dart';
import '../../../app/theme/app_colors.dart';
import '../../../data/models/auth_model.dart';
import '../../../services/auth_service.dart';

class AccountController extends GetxController {
  final AuthService _service = Get.find<AuthService>();

  // ── State ──────────────────────────────────────────────────────────────────
  final user           = Rxn<UserAuth>();
  final isLoading      = false.obs;
  final selectedGender = 'male'.obs;

  // ── Form controllers ───────────────────────────────────────────────────────
  final nameController        = TextEditingController();
  final oldPasswordController = TextEditingController();
  final newPasswordController = TextEditingController();
  final confirmPasswordController = TextEditingController();

  final isOldPassVisible  = false.obs;
  final isNewPassVisible  = false.obs;

  @override
  void onInit() {
    super.onInit();
    fetchAccount();
  }

  @override
  void onClose() {
    nameController.dispose();
    oldPasswordController.dispose();
    newPasswordController.dispose();
    confirmPasswordController.dispose();
    super.onClose();
  }

  // ── GET /auth/account ─────────────────────────────────────────────────────

  Future<void> fetchAccount() async {
    isLoading.value = true;
    try {
      final res = await _service.getAccount();
      if (res != null) {
        user.value = res;
        nameController.text = res.fullName;
        selectedGender.value = res.gender.isNotEmpty ? res.gender : 'male';
      }
    } catch (e) {
      _snack('error'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── PATCH /auth/profile ───────────────────────────────────────────────────

  Future<void> updateProfile() async {
    final name = nameController.text.trim();
    if (name.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    isLoading.value = true;
    try {
      final res = await _service.updateProfile(
        UpdateProfileRequest(fullName: name, gender: selectedGender.value),
      );
      if (res != null) {
        // Refresh user data from server after successful update
        await fetchAccount();
        _snack('profile_updated'.tr, res.message);
      } else {
        _snack('error'.tr, 'try_again_later'.tr);
      }
    } on Exception catch (e) {
      _snack('error'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  // ── DELETE /auth/account ──────────────────────────────────────────────────

  Future<void> deleteAccount() async {
    final confirmed = await Get.dialog<bool>(
      AlertDialog(
        backgroundColor: AppColors.bgCard,
        title: Text('account_delete_title'.tr,
            style: TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w700)),
        content: Text('account_delete_confirm'.tr,
            style: TextStyle(color: AppColors.textSecondary)),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: Text('cancel'.tr, style: TextStyle(color: AppColors.textSecondary)),
          ),
          TextButton(
            onPressed: () => Get.back(result: true),
            child: Text('account_delete_confirm_btn'.tr,
                style: TextStyle(color: AppColors.danger, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    isLoading.value = true;
    try {
      final res = await _service.deleteAccount();
      if (res != null) {
        _snack('account_deleted'.tr, res.message);
        await Future.delayed(const Duration(milliseconds: 800));
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

  // ── POST /auth/change-password ────────────────────────────────────────────

  Future<void> changePassword() async {
    final oldPass    = oldPasswordController.text;
    final newPass    = newPasswordController.text;
    final confirmPass = confirmPasswordController.text;

    if (oldPass.isEmpty || newPass.isEmpty || confirmPass.isEmpty) {
      _snack('missing_fields'.tr, 'fill_all_fields'.tr);
      return;
    }

    if (newPass != confirmPass) {
      _snack('error'.tr, 'passwords_not_match'.tr);
      return;
    }

    isLoading.value = true;
    try {
      final res = await _service.changePassword(
        ChangePasswordRequest(oldPassword: oldPass, newPassword: newPass),
      );
      if (res != null) {
        oldPasswordController.clear();
        newPasswordController.clear();
        confirmPasswordController.clear();
        _snack('auth_password_changed'.tr, res.message);
      } else {
        _snack('error'.tr, 'try_again_later'.tr);
      }
    } on Exception catch (e) {
      _snack('error'.tr, e.toString());
    } finally {
      isLoading.value = false;
    }
  }

  void toggleOldPassVisibility() => isOldPassVisible.value = !isOldPassVisible.value;
  void toggleNewPassVisibility() => isNewPassVisible.value = !isNewPassVisible.value;

  void _snack(String title, String msg) =>
      Get.snackbar(title, msg, snackPosition: SnackPosition.BOTTOM);
}