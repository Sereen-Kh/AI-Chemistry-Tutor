import 'package:get/get.dart';

import '../controllers/ask_ai_controller.dart';

class AskAiBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<AskAiController>(AskAiController.new);
}
