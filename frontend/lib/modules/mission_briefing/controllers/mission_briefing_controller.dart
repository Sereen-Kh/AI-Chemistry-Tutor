import 'package:get/get.dart';

class MissionBriefingController extends GetxController {
  final missionTitle = 'The Reaction Race'.obs;
  final difficulty = 'ADVANCED'.obs;
  final timeMinutes = 25.obs;
  final objectives = [
    'Balance 5 chemical equations',
    'Achieve 80%+ accuracy',
    'Complete within time limit',
  ];
  final xpReward = 450.obs;
  final crystalReward = 120.obs;

  void accept() => Get.back();
  void skip() => Get.back();
}
