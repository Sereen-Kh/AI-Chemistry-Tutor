import 'package:get/get.dart';

import '../controllers/mission_success_controller.dart';

class MissionSuccessBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<MissionSuccessController>(MissionSuccessController.new);
}
