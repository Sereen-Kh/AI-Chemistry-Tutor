import 'package:get/get.dart';

class SynergySparkController extends GetxController {
  final synergyScore = 94.obs;
  final xpEarned = 2400.obs;
  final partnerName = 'Sana K.'.obs;
  final userName = 'Ahmad K.'.obs;
  final userAccuracy = 92.obs;
  final partnerAccuracy = 96.obs;
  final timeTaken = '03:45'.obs;
  final questionsAnswered = 10.obs;
  final correctAnswers = 9.obs;
  final streakBonus = 500.obs;
  final isAnimating = false.obs;

  @override
  void onInit() {
    super.onInit();
    isAnimating.value = true;
  }
}
