import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../explanation/explanation_style.dart';

class ExplanationStyleController extends GetxController {
  final selectedId = ExplanationStyles.defaultId.obs;

  @override
  void onInit() {
    super.onInit();
    load();
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    selectedId.value =
        prefs.getString(ExplanationStyles.prefsKey) ?? ExplanationStyles.defaultId;
  }

  Future<void> setStyle(String id) async {
    if (!ExplanationStyles.options.any((o) => o.id == id)) return;
    selectedId.value = id;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(ExplanationStyles.prefsKey, id);
  }

  String get displayLabel => ExplanationStyles.labelFor(selectedId.value);

  ExplanationStyleOption get current =>
      ExplanationStyles.optionFor(selectedId.value);
}
