import 'package:get/get.dart';

import '../controllers/global_map_controller.dart';

class GlobalMapBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<GlobalMapController>(GlobalMapController.new);
}
