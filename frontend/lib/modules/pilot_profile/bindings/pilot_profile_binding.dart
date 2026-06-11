import 'package:get/get.dart';

import '../controllers/pilot_profile_controller.dart';

class PilotProfileBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<PilotProfileController>(PilotProfileController.new);
}
