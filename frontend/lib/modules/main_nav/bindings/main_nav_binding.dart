import 'package:get/get.dart';

import '../../ask_ai/controllers/ask_ai_controller.dart';
import '../../lessons/controllers/lessons_controller.dart';
import '../../pilot_profile/controllers/pilot_profile_controller.dart';
import '../../reels/controllers/reels_controller.dart';
import '../controllers/main_nav_controller.dart';

class MainNavBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<MainNavController>(MainNavController.new);
    Get.lazyPut<ReelsController>(ReelsController.new);
    Get.lazyPut<AskAiController>(AskAiController.new);
    Get.lazyPut<PilotProfileController>(PilotProfileController.new);
    Get.lazyPut<LessonsController>(LessonsController.new);
  }
}
