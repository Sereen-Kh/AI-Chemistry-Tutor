import 'package:get/get.dart';

import '../controllers/collaboration_controller.dart';

class CollaborationBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<CollaborationController>(CollaborationController.new);
}
