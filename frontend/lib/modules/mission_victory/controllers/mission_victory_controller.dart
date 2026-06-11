import 'package:get/get.dart';

class MissionVictoryController extends GetxController {
  final chapterName = 'Atomic Bonds'.obs;
  final nextChapterName = 'Acids & Bases'.obs;
  final achievementName = 'Bond Master'.obs;

  void viewRewards() => Get.back();

  // ignore: non_constant_identifier_names
  void nextChapter_() => Get.back();
}
