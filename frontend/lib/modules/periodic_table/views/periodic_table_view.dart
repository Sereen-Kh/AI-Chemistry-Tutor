import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/periodic_table_controller.dart';

String _periodicCategoryLabel(String key) {
  switch (key) {
    case 'Non-metal':
      return 'periodic_table_cat_nonmetal'.tr;
    case 'Noble Gas':
      return 'periodic_table_cat_noble_gas'.tr;
    case 'Alkali Metal':
      return 'periodic_table_cat_alkali'.tr;
    case 'Transition Metal':
      return 'periodic_table_cat_transition'.tr;
    case 'Halogen':
      return 'periodic_table_cat_halogen'.tr;
    case 'Alkaline Earth':
      return 'periodic_table_cat_alkaline'.tr;
    default:
      return key;
  }
}

class PeriodicTableView extends GetView<PeriodicTableController> {
  const PeriodicTableView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          // ── Search bar ────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.borderDefault),
              ),
              child: TextField(
                onChanged: controller.updateSearch,
                style: TextStyle(color: AppColors.textPrimary, fontSize: 14),
                decoration: InputDecoration(
                  hintText: 'periodic_table_search_hint'.tr,
                  hintStyle:
                      TextStyle(color: AppColors.textMuted, fontSize: 13),
                  prefixIcon: Icon(Icons.search_rounded,
                      color: AppColors.textMuted, size: 20),
                  border: InputBorder.none,
                  contentPadding:
                      const EdgeInsets.symmetric(vertical: 12, horizontal: 4),
                ),
              ),
            ),
          ).animate().fadeIn(duration: 350.ms),

          // ── Legend row ────────────────────────────────────────────────
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: _categories.entries.map((e) {
                return Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: e.value.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: e.value.withOpacity(0.35)),
                  ),
                  child: Text(
                    _periodicCategoryLabel(e.key),
                    style: TextStyle(
                      color: e.value,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                );
              }).toList(),
            ),
          ),

          const SizedBox(height: 4),

          // ── Element grid ──────────────────────────────────────────────
          Expanded(
            child: Obx(() {
              final filtered = controller.filteredElements;
              if (filtered.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.search_off_rounded,
                          color: AppColors.textMuted, size: 40),
                      const SizedBox(height: 12),
                      Text(
                        'periodic_table_empty'.tr,
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 14),
                      ),
                    ],
                  ),
                );
              }
              return GridView.builder(
                padding: const EdgeInsets.all(16),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 4,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  childAspectRatio: 0.85,
                ),
                itemCount: filtered.length,
                itemBuilder: (_, i) {
                  final el = filtered[i];
                  return GestureDetector(
                    onTap: () => _showElementSheet(context, el),
                    child: _ElementTile(element: el)
                        .animate(delay: (i * 40).ms)
                        .fadeIn(duration: 300.ms)
                        .scale(begin: const Offset(0.85, 0.85), end: const Offset(1, 1)),
                  );
                },
              );
            }),
          ),
        ],
      ),
    );
  }

  static const _categories = {
    'Non-metal': Color(0xFF34D399),
    'Noble Gas': Color(0xFF22D3EE),
    'Alkali Metal': Color(0xFFEF4444),
    'Transition Metal': Color(0xFF8B7DF8),
    'Halogen': Color(0xFFA3E635),
    'Alkaline Earth': Color(0xFFF97316),
  };

  void _showElementSheet(BuildContext context, ElementData el) {
    controller.selectElement(el);
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _ElementSheet(element: el),
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
        'periodic_table_title'.tr,
        style: TextStyle(
          color: AppColors.textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w800,
          letterSpacing: 2.5,
        ),
      ),
      actions: [
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Obx(() => Text(
                  'periodic_table_count'.trParams({
                    'count': '${controller.elements.length}',
                  }),
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                )),
          ),
        ),
      ],
    );
  }
}

// ── Element tile ──────────────────────────────────────────────────────────────
class _ElementTile extends StatelessWidget {
  final ElementData element;
  const _ElementTile({required this.element});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: element.color.withOpacity(0.4), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: element.color.withOpacity(0.08),
            blurRadius: 8,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            element.number.toString(),
            style: TextStyle(
              color: AppColors.textMuted,
              fontSize: 9,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          Center(
            child: Text(
              element.symbol,
              style: TextStyle(
                color: element.color,
                fontSize: 26,
                fontWeight: FontWeight.w900,
              ),
            ),
          ),
          const Spacer(),
          Center(
            child: Text(
              element.name,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 9,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 2),
          Center(
            child: Text(
              element.mass.toStringAsFixed(2),
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 8,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Element bottom sheet ──────────────────────────────────────────────────────
class _ElementSheet extends StatelessWidget {
  final ElementData element;
  const _ElementSheet({required this.element});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: element.color.withOpacity(0.5), width: 2),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.borderDefault,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 20),

          // Symbol + name row
          Row(
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: element.color.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(16),
                  border:
                      Border.all(color: element.color.withOpacity(0.5), width: 2),
                ),
                alignment: Alignment.center,
                child: Text(
                  element.symbol,
                  style: TextStyle(
                    color: element.color,
                    fontSize: 32,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      element.name,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: element.color.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        _periodicCategoryLabel(element.category),
                        style: TextStyle(
                          color: element.color,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),
          Divider(color: AppColors.borderDefault),
          const SizedBox(height: 12),

          // Data rows
          _DataRow(
              label: 'periodic_table_atomic_number'.tr,
              value: element.number.toString()),
          _DataRow(
              label: 'periodic_table_atomic_mass'.tr,
              value: '${element.mass.toStringAsFixed(3)} u'),
          _DataRow(
              label: 'periodic_table_electron_config'.tr,
              value: element.config),
          _DataRow(
              label: 'periodic_table_category'.tr,
              value: _periodicCategoryLabel(element.category)),

          const SizedBox(height: 8),
        ],
      ),
    ).animate().slideY(begin: 0.15, end: 0, duration: 300.ms, curve: Curves.easeOut);
  }
}

class _DataRow extends StatelessWidget {
  final String label;
  final String value;
  const _DataRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}
