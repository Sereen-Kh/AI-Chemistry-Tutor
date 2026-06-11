import 'package:get/get.dart';

import '../controllers/squad_comms_controller.dart';

class SquadCommsBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<SquadCommsController>(SquadCommsController.new);
}
