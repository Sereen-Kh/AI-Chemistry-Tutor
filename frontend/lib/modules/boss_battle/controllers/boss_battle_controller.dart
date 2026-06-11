import 'dart:async';

import 'package:get/get.dart';

class BossBattleController extends GetxController {
  final playerHp = 100.obs;
  final bossHp = 75.obs;
  final round = 2.obs;
  final totalRounds = 3.obs;
  final combo = 3.obs;
  final secondsLeft = 30.obs;
  final currentChallenge = 'H₂ + O₂ → H₂O'.obs;
  final answer = ''.obs;
  final isCorrect = RxnBool();

  Timer? _timer;

  @override
  void onInit() {
    super.onInit();
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    secondsLeft.value = 30;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (secondsLeft.value > 0) {
        secondsLeft.value--;
      } else {
        _onTimeUp();
      }
    });
  }

  void _onTimeUp() {
    _timer?.cancel();
    isCorrect.value = false;
    playerHp.value = (playerHp.value - 15).clamp(0, 100);
    combo.value = 0;
    Future.delayed(const Duration(milliseconds: 1200), () {
      isCorrect.value = null;
      answer.value = '';
      _startTimer();
    });
  }

  void updateAnswer(String val) {
    answer.value = val;
  }

  void submitAnswer() {
    _timer?.cancel();
    // Correct answer for H₂ + O₂ → H₂O is 2H₂ + O₂ → 2H₂O
    final trimmed = answer.value.trim();
    final correct = trimmed == '2,1,2' || trimmed == '2 1 2';
    isCorrect.value = correct;

    if (correct) {
      bossHp.value = (bossHp.value - 20).clamp(0, 100);
      combo.value = combo.value + 1;
    } else {
      playerHp.value = (playerHp.value - 10).clamp(0, 100);
      combo.value = 0;
    }

    Future.delayed(const Duration(milliseconds: 1500), () {
      isCorrect.value = null;
      answer.value = '';
      if (round.value < totalRounds.value) {
        round.value = round.value + 1;
      }
      _startTimer();
    });
  }

  void useHint() {
    Get.snackbar(
      'boss_battle_snackbar_hint_title'.tr,
      'boss_battle_snackbar_hint_body'.tr,
      snackPosition: SnackPosition.TOP,
      duration: const Duration(seconds: 3),
    );
  }

  String get timerLabel {
    final s = secondsLeft.value;
    return '${s.toString().padLeft(2, '0')}s';
  }

  @override
  void onClose() {
    _timer?.cancel();
    super.onClose();
  }
}
