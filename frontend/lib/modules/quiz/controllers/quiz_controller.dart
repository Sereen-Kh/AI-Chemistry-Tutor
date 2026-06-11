import 'dart:async';

import 'package:get/get.dart';

import '../../../data/models/quiz_model.dart';

class QuizController extends GetxController {
  final questions = QuizQuestion.defaults;
  final currentIndex = 0.obs;
  final selectedOption = RxnString();
  final secondsRemaining = 45.obs;
  final isCorrect = RxnBool();
  final hasStarted = false.obs;

  int questionCount = 15;
  String difficulty = 'Medium';
  int selectedChapter = 0;

  Timer? _timer;

  QuizQuestion get current => questions[currentIndex.value];

  @override
  void onInit() {
    super.onInit();
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    secondsRemaining.value = 45;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (secondsRemaining.value > 0) {
        secondsRemaining.value--;
      } else {
        _advance();
      }
    });
  }

  void selectOption(String letter) {
    if (selectedOption.value != null) return;
    selectedOption.value = letter;
    isCorrect.value = letter == current.correctLetter;
  }

  void nextQuestion() {
    _advance();
  }

  void _advance() {
    if (currentIndex.value < questions.length - 1) {
      currentIndex.value++;
      selectedOption.value = null;
      isCorrect.value = null;
      _startTimer();
    } else {
      Get.back();
    }
  }

  void startQuiz() => hasStarted.value = true;

  String get timerLabel {
    final m = secondsRemaining.value ~/ 60;
    final s = secondsRemaining.value % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  void onClose() {
    _timer?.cancel();
    super.onClose();
  }
}
