import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../app/routes/app_routes.dart';
import '../../../core/navigation/post_auth_navigation.dart';

class SplashController extends GetxController {
  final progress = 0.0.obs;
  final statusText = ''.obs;

  List<({double pct, String msg})> get _steps => [
    (pct: 0.20, msg: 'splash_loading'.tr),
    (pct: 0.45, msg: 'splash_calibrating'.tr),
    (pct: 0.65, msg: 'splash_init'.tr),
    (pct: 0.85, msg: 'splash_syncing'.tr),
    (pct: 1.00, msg: 'splash_online'.tr),
  ];

  @override
  void onReady() {
    super.onReady();
    _runSequence();
  }

  Future<void> _runSequence() async {
    await Future.delayed(const Duration(milliseconds: 600));

    for (final step in _steps) {
      await _animateTo(step.pct, step.msg);
    }

    await Future.delayed(const Duration(milliseconds: 500));
    _navigate();
  }

  Future<void> _animateTo(double target, String msg) async {
    statusText.value = msg;
    const steps = 30;
    final start = progress.value;
    final delta = target - start;
    for (int i = 1; i <= steps; i++) {
      progress.value = start + delta * (i / steps);
      await Future.delayed(const Duration(milliseconds: 35));
    }
    await Future.delayed(const Duration(milliseconds: 250));
  }

  Future<void> _navigate() async {
    final prefs = await SharedPreferences.getInstance();
    final loggedIn = prefs.getBool('logged_in') ?? false;

    if (!loggedIn) {
      Get.offAllNamed(AppRoutes.auth);
    } else {
      await navigateAfterLogin();
    }
  }
}
