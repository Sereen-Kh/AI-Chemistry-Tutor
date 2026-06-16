import 'package:get/get.dart';

import '../controllers/formula_game_controller.dart';

class FormulaGameBinding extends Bindings {
  @override
  void dependencies() => Get.lazyPut<FormulaGameController>(FormulaGameController.new);
}
