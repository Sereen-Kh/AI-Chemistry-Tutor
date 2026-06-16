import 'package:get/get.dart';

class RankUpController extends GetxController {
  final previousRank = 'Quantum Voyager'.obs;
  final newRank = 'Cosmic Chemist'.obs;
  final xpGained = 2500.obs;
  final newPerks = [
    'Bonus XP x1.5',
    'Rare Item Drops',
    'Squad Leader Access',
  ];

  void onContinue() => Get.back();
}
