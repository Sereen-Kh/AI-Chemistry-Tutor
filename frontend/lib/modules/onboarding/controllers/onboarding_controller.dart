import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../app/routes/app_routes.dart';

class OnboardingPage {
  final String titleKey;
  final String subtitleKey;
  final String illustrationAsset;

  const OnboardingPage({
    required this.titleKey,
    required this.subtitleKey,
    required this.illustrationAsset,
  });

  String get title => titleKey.tr;
  String get subtitle => subtitleKey.tr;
}

class OnboardingController extends GetxController {
  final pageIndex = 0.obs;
  late final PageController pageController;

  final pages = const [
    OnboardingPage(
      titleKey: 'onboarding_title_1',
      subtitleKey: 'onboarding_subtitle_1',
      illustrationAsset: 'atom',
    ),
    OnboardingPage(
      titleKey: 'onboarding_title_2',
      subtitleKey: 'onboarding_subtitle_2',
      illustrationAsset: 'rocket',
    ),
    OnboardingPage(
      titleKey: 'onboarding_title_3',
      subtitleKey: 'onboarding_subtitle_3',
      illustrationAsset: 'mentor',
    ),
  ];

  @override
  void onInit() {
    super.onInit();
    pageController = PageController();
  }

  @override
  void onClose() {
    pageController.dispose();
    super.onClose();
  }

  void next() {
    if (pageIndex.value < pages.length - 1) {
      pageIndex.value++;
      pageController.animateToPage(
        pageIndex.value,
        duration: const Duration(milliseconds: 400),
        curve: Curves.easeInOut,
      );
    } else {
      _finish();
    }
  }

  void skip() => _finish();

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_done', true);
    if (prefs.getString('mentor_id') == null) {
      Get.offAllNamed(AppRoutes.mentor);
    } else {
      Get.offAllNamed(AppRoutes.mainNav);
    }
  }
}
