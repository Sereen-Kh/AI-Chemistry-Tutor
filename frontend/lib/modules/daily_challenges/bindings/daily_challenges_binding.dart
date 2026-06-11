import 'package:get/get.dart';

import '../controllers/daily_challenges_controller.dart';

class DailyChallengesBinding extends Bindings {
  @override
  void dependencies() =>
      Get.lazyPut<DailyChallengesController>(DailyChallengesController.new);
}
