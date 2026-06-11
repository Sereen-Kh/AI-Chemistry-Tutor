import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ElementData {
  final String symbol;
  final String name;
  final int number;
  final double mass;
  final String config;
  final String category;
  final Color color;

  const ElementData({
    required this.symbol,
    required this.name,
    required this.number,
    required this.mass,
    required this.config,
    required this.category,
    required this.color,
  });
}

class PeriodicTableController extends GetxController {
  final elements = <ElementData>[].obs;
  final selected = Rxn<ElementData>();
  final searchQuery = ''.obs;

  List<ElementData> get filteredElements {
    final q = searchQuery.value.toLowerCase();
    if (q.isEmpty) return elements;
    return elements
        .where((e) =>
            e.symbol.toLowerCase().contains(q) ||
            e.name.toLowerCase().contains(q) ||
            e.number.toString().contains(q))
        .toList();
  }

  @override
  void onInit() {
    super.onInit();
    _loadElements();
  }

  void _loadElements() {
    elements.assignAll([
      const ElementData(
        symbol: 'H',
        name: 'Hydrogen',
        number: 1,
        mass: 1.008,
        config: '1s¹',
        category: 'Non-metal',
        color: Color(0xFF34D399),
      ),
      const ElementData(
        symbol: 'He',
        name: 'Helium',
        number: 2,
        mass: 4.003,
        config: '1s²',
        category: 'Noble Gas',
        color: Color(0xFF22D3EE),
      ),
      const ElementData(
        symbol: 'Li',
        name: 'Lithium',
        number: 3,
        mass: 6.941,
        config: '[He] 2s¹',
        category: 'Alkali Metal',
        color: Color(0xFFEF4444),
      ),
      const ElementData(
        symbol: 'Be',
        name: 'Beryllium',
        number: 4,
        mass: 9.012,
        config: '[He] 2s²',
        category: 'Alkaline Earth',
        color: Color(0xFFF97316),
      ),
      const ElementData(
        symbol: 'C',
        name: 'Carbon',
        number: 6,
        mass: 12.011,
        config: '[He] 2s² 2p²',
        category: 'Non-metal',
        color: Color(0xFF34D399),
      ),
      const ElementData(
        symbol: 'N',
        name: 'Nitrogen',
        number: 7,
        mass: 14.007,
        config: '[He] 2s² 2p³',
        category: 'Non-metal',
        color: Color(0xFF34D399),
      ),
      const ElementData(
        symbol: 'O',
        name: 'Oxygen',
        number: 8,
        mass: 15.999,
        config: '[He] 2s² 2p⁴',
        category: 'Non-metal',
        color: Color(0xFF34D399),
      ),
      const ElementData(
        symbol: 'Na',
        name: 'Sodium',
        number: 11,
        mass: 22.990,
        config: '[Ne] 3s¹',
        category: 'Alkali Metal',
        color: Color(0xFFEF4444),
      ),
      const ElementData(
        symbol: 'Cl',
        name: 'Chlorine',
        number: 17,
        mass: 35.453,
        config: '[Ne] 3s² 3p⁵',
        category: 'Halogen',
        color: Color(0xFFA3E635),
      ),
      const ElementData(
        symbol: 'Au',
        name: 'Gold',
        number: 79,
        mass: 196.967,
        config: '[Xe] 4f¹⁴ 5d¹⁰ 6s¹',
        category: 'Transition Metal',
        color: Color(0xFF8B7DF8),
      ),
    ]);
  }

  void selectElement(ElementData e) {
    selected.value = e;
  }

  void clearSelection() {
    selected.value = null;
  }

  void updateSearch(String q) {
    searchQuery.value = q;
  }
}
