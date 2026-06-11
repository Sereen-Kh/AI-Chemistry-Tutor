import 'package:get/get.dart';

import '../controllers/social_controller.dart';

class SocialBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<SocialController>(SocialController.new);
}
