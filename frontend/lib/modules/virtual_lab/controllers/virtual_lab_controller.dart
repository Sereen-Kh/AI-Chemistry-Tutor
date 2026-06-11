import 'package:get/get.dart';

class VirtualLabController extends GetxController {
  final selectedCompound = 'H₂O'.obs;
  final temperature = 25.0.obs;
  final pressure = 1.0.obs;
  final isSimulating = false.obs;
  final moleculeCount = 24.obs;
  final bondCount = 18.obs;
  final energyLevel = 4.2.obs;

  final compounds = ['H₂O', 'NaCl', 'CO₂', 'CH₄', 'H₂SO₄'];

  void selectCompound(String c) {
    selectedCompound.value = c;
    if (isSimulating.value) {
      isSimulating.value = false;
    }
    _updateStats(c);
  }

  void _updateStats(String compound) {
    switch (compound) {
      case 'NaCl':
        moleculeCount.value = 32;
        bondCount.value = 32;
        energyLevel.value = 3.1;
        break;
      case 'CO₂':
        moleculeCount.value = 18;
        bondCount.value = 36;
        energyLevel.value = 5.7;
        break;
      case 'CH₄':
        moleculeCount.value = 20;
        bondCount.value = 40;
        energyLevel.value = 2.8;
        break;
      case 'H₂SO₄':
        moleculeCount.value = 14;
        bondCount.value = 42;
        energyLevel.value = 7.3;
        break;
      default:
        moleculeCount.value = 24;
        bondCount.value = 18;
        energyLevel.value = 4.2;
    }
  }

  void toggleSimulation() {
    isSimulating.value = !isSimulating.value;
  }
}
