import 'package:get/get.dart';

import '../controllers/mentor_controller.dart';

class MentorBinding extends Bindings {
  @override
  void dependencies() {
    if (Get.isRegistered<MentorController>()) {
      Get.delete<MentorController>();
    }
    Get.put(MentorController());
  }
}
