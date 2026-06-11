import 'package:get/get.dart';

import '../controllers/boss_battle_controller.dart';

class BossBattleBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<BossBattleController>(BossBattleController.new);
}
