import 'package:get/get.dart';

import '../controllers/study_plan_controller.dart';

class StudyPlanBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<StudyPlanController>(StudyPlanController.new);
}
