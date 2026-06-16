import 'package:get/get.dart';

class LessonDetailController extends GetxController {
  final chapterLabel = 'Chapter 2: Covalent Bonds';
  final title = 'Sharing is Caring: How Atoms Bond';
  final description =
      'Dive into the quantum mechanics of electron sharing. See how overlap creates stability in the molecular world. #Chemistry #STEM';
  final difficulty = 'Hard';
  final likes = 42900;
  final comments = 1200;

  final currentSeconds = 225.obs;
  final totalSeconds = 300;
  final isLiked = false.obs;

  final currentStep = 1.obs;
  final totalSteps = 5;
  final activeTab = 0.obs;
  final lessonTitle = 'Formation of the Covalent Bond';

  double get progress => currentSeconds.value / totalSeconds;

  String timeLabel(int secs) {
    final m = secs ~/ 60;
    final s = secs % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  String get currentTime => timeLabel(currentSeconds.value);
  String get totalTime => timeLabel(totalSeconds);

  String formatCount(int n) {
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}K';
    return '$n';
  }

  void toggleLike() => isLiked.value = !isLiked.value;

  void nextStep() {
    if (currentStep.value < totalSteps - 1) currentStep.value++;
  }

  void setTab(int i) => activeTab.value = i;

  void gotIt() {
    nextStep();
  }
}
