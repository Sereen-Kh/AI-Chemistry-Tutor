import 'package:get/get.dart';

class GearItem {
  final String emoji;
  final String name;
  final String rarity;
  bool isEquipped;
  final bool isLocked;

  GearItem({
    required this.emoji,
    required this.name,
    required this.rarity,
    this.isEquipped = false,
    this.isLocked = false,
  });
}

class InventoryController extends GetxController {
  final selectedTab = 0.obs;
  final items = <GearItem>[].obs;
  final crystals = 2840.obs;
  final charges = 15.obs;

  @override
  void onInit() {
    super.onInit();
    _loadItems();
  }

  void _loadItems() {
    items.assignAll([
      GearItem(
        emoji: '⚗️',
        name: 'Quantum Flask',
        rarity: 'EPIC',
        isEquipped: true,
      ),
      GearItem(
        emoji: '🔬',
        name: 'Neural Scope',
        rarity: 'RARE',
        isLocked: true,
      ),
      GearItem(
        emoji: '⭐',
        name: 'XP Multiplier x2',
        rarity: 'LEGENDARY',
        isEquipped: true,
      ),
      GearItem(
        emoji: '🛡️',
        name: 'Shield Matrix',
        rarity: 'RARE',
      ),
      GearItem(
        emoji: '🧬',
        name: 'DNA Decoder',
        rarity: 'EPIC',
      ),
      GearItem(
        emoji: '🔭',
        name: 'Spectrum Lens',
        rarity: 'RARE',
      ),
      GearItem(
        emoji: '💎',
        name: 'Crystal Core',
        rarity: 'LEGENDARY',
        isLocked: true,
      ),
      GearItem(
        emoji: '⚡',
        name: 'Charge Cell',
        rarity: 'RARE',
        isEquipped: true,
      ),
    ]);
  }

  void equipItem(GearItem item) {
    if (item.isLocked) return;
    final index = items.indexOf(item);
    if (index == -1) return;
    items[index].isEquipped = !items[index].isEquipped;
    items.refresh();
  }

  void switchTab(int i) {
    selectedTab.value = i;
  }
}
