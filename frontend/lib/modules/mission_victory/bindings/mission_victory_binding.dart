import 'package:get/get.dart';

import '../controllers/mission_victory_controller.dart';

class MissionVictoryBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<MissionVictoryController>(MissionVictoryController.new);
}
