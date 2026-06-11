import 'package:get/get.dart';

import '../controllers/virtual_lab_controller.dart';

class VirtualLabBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<VirtualLabController>(VirtualLabController.new);
}
