import 'package:get/get.dart';

import '../controllers/flashcards_controller.dart';

class FlashcardsBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<FlashcardsController>(FlashcardsController.new);
}
