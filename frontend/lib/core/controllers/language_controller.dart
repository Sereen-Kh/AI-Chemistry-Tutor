import 'dart:ui';

import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

class LanguageController extends GetxController {
  final locale = const Locale('en').obs;

  @override
  void onInit() {
    super.onInit();
    _loadLocale();
  }

  Future<void> _loadLocale() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString('locale') ?? 'en';
    locale.value = Locale(code);
    Get.updateLocale(locale.value);
  }

  bool get isArabic => locale.value.languageCode == 'ar';

  void toggleLanguage() {
    final next = isArabic ? const Locale('en') : const Locale('ar');
    locale.value = next;
    Get.updateLocale(next);
    _save(next.languageCode);
  }

  Future<void> _save(String code) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('locale', code);
  }
}
