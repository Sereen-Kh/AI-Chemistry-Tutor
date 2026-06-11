import 'package:get/get.dart';

import '../controllers/rewards_controller.dart';

class RewardsBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<RewardsController>(RewardsController.new);
}
