import 'package:get/get.dart';
import '../controllers/synergy_sparks_controller.dart';

class SynergySparkBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<SynergySparkController>(SynergySparkController.new);
  }
}
