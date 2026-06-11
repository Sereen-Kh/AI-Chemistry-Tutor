import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/inventory_controller.dart';

class InventoryView extends GetView<InventoryController> {
  const InventoryView({super.key});

  List<String> get _tabs => [
        'inventory_tab_gear'.tr,
        'inventory_tab_reagents'.tr,
        'inventory_tab_artifacts'.tr,
        'inventory_tab_boosts'.tr,
      ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          // ── Stats header ──────────────────────────────────────────────
          _StatsHeader().animate().fadeIn(duration: 350.ms),

          // ── Tab bar ───────────────────────────────────────────────────
          Obx(() => _TabBar(
                tabs: _tabs,
                selected: controller.selectedTab.value,
                onTap: controller.switchTab,
              )).animate().fadeIn(delay: 80.ms, duration: 350.ms),

          const SizedBox(height: 4),

          // ── Item grid ─────────────────────────────────────────────────
          Expanded(
            child: Obx(() => GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                    childAspectRatio: 0.88,
                  ),
                  itemCount: controller.items.length,
                  itemBuilder: (_, i) {
                    final item = controller.items[i];
                    return _ItemCard(
                      item: item,
                      onEquip: () => controller.equipItem(item),
                    )
                        .animate(delay: (i * 50).ms)
                        .fadeIn(duration: 300.ms)
                        .scale(
                            begin: const Offset(0.9, 0.9),
                            end: const Offset(1, 1));
                  },
                )),
          ),

          // ── Currency bar ──────────────────────────────────────────────
          Obx(() => _CurrencyBar(
                crystals: controller.crystals.value,
                charges: controller.charges.value,
              )).animate().fadeIn(delay: 160.ms, duration: 350.ms),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppColors.bgBase,
      elevation: 0,
      leading: IconButton(
        icon: Icon(Icons.arrow_back_ios_new_rounded,
            color: AppColors.textSecondary, size: 18),
        onPressed: () => Get.back(),
      ),
      title: Text(
        'inventory_title'.tr,
        style: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 12,
          fontWeight: FontWeight.w800,
          letterSpacing: 2,
        ),
      ),
      actions: [
        IconButton(
          icon: Icon(Icons.filter_list_rounded,
              color: AppColors.textSecondary, size: 20),
          onPressed: () {},
        ),
      ],
    );
  }
}

// ── Stats header ──────────────────────────────────────────────────────────────
class _StatsHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: AppColors.gradientCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: AppColors.gradientPurple,
              boxShadow: [
                BoxShadow(
                    color: AppColors.purple.withOpacity(0.4), blurRadius: 12),
              ],
            ),
            alignment: Alignment.center,
            child: const Text('⚗️', style: TextStyle(fontSize: 22)),
          ),
          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'inventory_pilot_name'.tr,
                      style: TextStyle(
                        color: AppColors.cyan,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        gradient: AppColors.gradientPurple,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        'inventory_level'.trParams({'level': '42'}),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                // XP bar
                Stack(
                  children: [
                    Container(
                      height: 6,
                      decoration: BoxDecoration(
                        color: AppColors.bgBase,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    Container(
                      height: 6,
                      width: (MediaQuery.of(context).size.width - 120) * 0.72,
                      decoration: BoxDecoration(
                        gradient: AppColors.gradientCyan,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'inventory_xp_progress'
                      .trParams({'percent': '72', 'next': '43'}),
                  style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Tab bar ───────────────────────────────────────────────────────────────────
class _TabBar extends StatelessWidget {
  final List<String> tabs;
  final int selected;
  final ValueChanged<int> onTap;

  const _TabBar({
    required this.tabs,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: tabs.asMap().entries.map((entry) {
          final i = entry.key;
          final label = entry.value;
          final isSelected = selected == i;
          return Expanded(
            child: GestureDetector(
              onTap: () => onTap(i),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                decoration: BoxDecoration(
                  color: isSelected ? AppColors.purple : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                alignment: Alignment.center,
                child: Text(
                  label,
                  style: TextStyle(
                    color: isSelected ? Colors.white : AppColors.textMuted,
                    fontSize: 10,
                    fontWeight:
                        isSelected ? FontWeight.w800 : FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Item card ─────────────────────────────────────────────────────────────────
class _ItemCard extends StatelessWidget {
  final GearItem item;
  final VoidCallback onEquip;

  const _ItemCard({required this.item, required this.onEquip});

  Color get _rarityColor {
    switch (item.rarity) {
      case 'LEGENDARY':
        return const Color(0xFFFBBF24);
      case 'EPIC':
        return AppColors.purple;
      default:
        return AppColors.cyan;
    }
  }

  @override
  Widget build(BuildContext context) {
    final rc = _rarityColor;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: item.isEquipped ? rc.withOpacity(0.6) : AppColors.borderDefault,
          width: item.isEquipped ? 1.5 : 1,
        ),
        boxShadow: [
          if (item.isEquipped)
            BoxShadow(color: rc.withOpacity(0.15), blurRadius: 14),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Rarity badge + lock
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: rc.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  item.rarity,
                  style: TextStyle(
                    color: rc,
                    fontSize: 8,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
              const Spacer(),
              if (item.isLocked)
                Icon(Icons.lock_rounded,
                    color: AppColors.textMuted, size: 14)
              else if (item.isEquipped)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 5, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.green.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'inventory_equipped_on'.tr,
                    style: TextStyle(
                      color: AppColors.green,
                      fontSize: 8,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
            ],
          ),

          const Spacer(),

          // Emoji icon
          Text(item.emoji, style: const TextStyle(fontSize: 28)),

          const SizedBox(height: 6),

          // Item name
          Text(
            item.name,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),

          const Spacer(),

          // Equip / locked button
          GestureDetector(
            onTap: item.isLocked ? null : onEquip,
            child: Container(
              height: 28,
              decoration: BoxDecoration(
                color: item.isLocked
                    ? AppColors.bgBase
                    : item.isEquipped
                        ? AppColors.green.withOpacity(0.1)
                        : AppColors.purple.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: item.isLocked
                      ? AppColors.borderDefault
                      : item.isEquipped
                          ? AppColors.green.withOpacity(0.5)
                          : AppColors.purple.withOpacity(0.5),
                ),
              ),
              alignment: Alignment.center,
              child: Text(
                item.isLocked
                    ? 'inventory_locked'.tr
                    : item.isEquipped
                        ? 'inventory_unequip'.tr
                        : 'inventory_equip'.tr,
                style: TextStyle(
                  color: item.isLocked
                      ? AppColors.textMuted
                      : item.isEquipped
                          ? AppColors.green
                          : AppColors.purple,
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Currency bar ──────────────────────────────────────────────────────────────
class _CurrencyBar extends StatelessWidget {
  final int crystals;
  final int charges;

  const _CurrencyBar({required this.crystals, required this.charges});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: AppColors.borderDefault)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _CurrencyChip(
            icon: '💎',
            label: 'inventory_crystals'
                .trParams({'count': _fmt(crystals)}),
            color: AppColors.cyan,
          ),
          Container(width: 1, height: 28, color: AppColors.borderDefault),
          _CurrencyChip(
            icon: '⚡',
            label: 'inventory_charges'.trParams({'count': '$charges'}),
            color: AppColors.amber,
          ),
        ],
      ),
    );
  }

  String _fmt(int v) {
    if (v >= 1000) {
      final k = v ~/ 1000;
      final r = (v % 1000).toString().padLeft(3, '0');
      return '$k,$r';
    }
    return v.toString();
  }
}

class _CurrencyChip extends StatelessWidget {
  final String icon;
  final String label;
  final Color color;

  const _CurrencyChip({
    required this.icon,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(icon, style: const TextStyle(fontSize: 18)),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 14,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}
