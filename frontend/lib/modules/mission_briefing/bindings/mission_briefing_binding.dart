import 'package:get/get.dart';

import '../controllers/mission_briefing_controller.dart';

class MissionBriefingBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<MissionBriefingController>(MissionBriefingController.new);
}
