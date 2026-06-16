import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../app/routes/app_routes.dart';

/// Routes the user after login or splash based on onboarding / mentor setup.
Future<void> navigateAfterLogin() async {
  final prefs = await SharedPreferences.getInstance();
  final onboarded = prefs.getBool('onboarding_done') ?? false;
  final mentorSet = prefs.getString('mentor_id') != null;

  if (!onboarded) {
    Get.offAllNamed(AppRoutes.onboarding);
  } else if (!mentorSet) {
    Get.offAllNamed(AppRoutes.mentor);
  } else {
    Get.offAllNamed(AppRoutes.mainNav);
  }
}
