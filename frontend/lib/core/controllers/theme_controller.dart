import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../app/theme/app_colors.dart';
import '../../app/theme/app_theme.dart';

class ThemeController extends GetxController {
  final isDark = true.obs;
  final chemTheme = ChemTheme.tutor.obs;

  @override
  void onInit() {
    super.onInit();
    _load();
  }

  void toggleDark() {
    isDark.toggle();
    AppColors.isDark = isDark.value;
    Get.changeTheme(AppTheme.current);
    _save();
  }

  void setTheme(ChemTheme t) {
    chemTheme.value = t;
    AppColors.theme = t;
    Get.changeTheme(AppTheme.current);
    _save();
  }

  String get darkLabel => isDark.value ? 'DARK' : 'LIGHT';

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final dark = prefs.getBool('theme_is_dark') ?? true;
    final themeIndex = prefs.getInt('chem_theme') ?? 0;

    isDark.value = dark;
    AppColors.isDark = dark;

    final t = ChemTheme.values[themeIndex.clamp(0, ChemTheme.values.length - 1)];
    chemTheme.value = t;
    AppColors.theme = t;

    Get.changeTheme(AppTheme.current);
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('theme_is_dark', isDark.value);
    await prefs.setInt('chem_theme', chemTheme.value.index);
  }
}
