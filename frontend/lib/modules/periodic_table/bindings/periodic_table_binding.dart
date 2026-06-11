import 'package:get/get.dart';

import '../controllers/periodic_table_controller.dart';

class PeriodicTableBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<PeriodicTableController>(PeriodicTableController.new);
}
