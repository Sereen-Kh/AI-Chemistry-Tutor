import 'package:get/get.dart';

import '../controllers/lessons_controller.dart';

class LessonsBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<LessonsController>(LessonsController.new);
}
