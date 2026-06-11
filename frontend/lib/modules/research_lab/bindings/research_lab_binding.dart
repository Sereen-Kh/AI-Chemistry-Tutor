import 'package:get/get.dart';

import '../controllers/research_lab_controller.dart';

class ResearchLabBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<ResearchLabController>(ResearchLabController.new);
}
