import 'package:get/get.dart';

import '../controllers/rank_up_controller.dart';

class RankUpBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<RankUpController>(RankUpController.new);
}
