import 'package:get/get.dart';

import '../controllers/lesson_detail_controller.dart';

class LessonDetailBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<LessonDetailController>(LessonDetailController.new);
}
