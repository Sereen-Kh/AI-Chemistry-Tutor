import 'package:get/get.dart';

class MissionSuccessController extends GetxController {
  final score = 9850.obs;
  final timeSeconds = 124.obs;
  final accuracy = 94.obs;
  final xpEarned = 350.obs;
  final starsEarned = 3.obs;
  final missionName = 'Covalent Bond Mastery'.obs;

  void claimReward() => Get.back();
  void nextMission() => Get.back();

  String get formattedTime {
    final m = timeSeconds.value ~/ 60;
    final s = timeSeconds.value % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
}
