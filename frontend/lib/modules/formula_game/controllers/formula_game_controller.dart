import 'package:get/get.dart';

class FormulaGameController extends GetxController {
  final currentTarget = 'H₂SO₄'.obs;
  final currentFormula = ''.obs;
  final score = 1240.obs;
  final streak = 5.obs;
  final level = 7.obs;
  final levelProgress = 0.62.obs;

  final availableElements = ['H', 'S', 'O', 'N', 'C', 'Cl', 'Na'];

  void addElement(String el) {
    currentFormula.value = currentFormula.value + el;
  }

  void removeLastElement() {
    final f = currentFormula.value;
    if (f.isEmpty) return;
    // Remove last character (simple backspace)
    currentFormula.value = f.substring(0, f.length - 1);
  }

  void clearFormula() {
    currentFormula.value = '';
  }

  void submitFormula() {
    checkFormula();
  }

  void checkFormula() {
    final input = currentFormula.value.trim();
    // Normalize by stripping unicode subscripts for comparison
    final normalized = _normalizeFormula(input);
    final target = _normalizeFormula(currentTarget.value);

    if (normalized == target) {
      score.value = score.value + 100 + (streak.value * 20);
      streak.value = streak.value + 1;
      levelProgress.value = (levelProgress.value + 0.08).clamp(0.0, 1.0);
      Get.snackbar(
        'formula_game_correct_title'.tr,
        'formula_game_correct_body'.trParams({
          'pts': '${100 + streak.value * 20}',
          'streak': '${streak.value}',
        }),
        snackPosition: SnackPosition.TOP,
        duration: const Duration(seconds: 2),
      );
      currentFormula.value = '';
    } else {
      streak.value = 0;
      Get.snackbar(
        'formula_game_incorrect_title'.tr,
        'formula_game_incorrect_body'.trParams({
          'formula': currentTarget.value,
        }),
        snackPosition: SnackPosition.TOP,
        duration: const Duration(seconds: 2),
      );
    }
  }

  String _normalizeFormula(String f) {
    return f
        .replaceAll('₂', '2')
        .replaceAll('₃', '3')
        .replaceAll('₄', '4')
        .replaceAll('₅', '5')
        .replaceAll('₆', '6')
        .toLowerCase();
  }
}
