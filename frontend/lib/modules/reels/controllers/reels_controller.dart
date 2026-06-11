import 'dart:async';
import 'package:flutter/material.dart';
import 'package:get/get.dart';

class ReelItem {
  final String element;
  final String symbol;
  final int atomicNumber;
  final String chapter;
  final String title;
  final String description;
  final String tag;
  final int durationSeconds;
  final int likes;
  final int xpReward;
  final Color accentColor;

  const ReelItem({
    required this.element,
    required this.symbol,
    required this.atomicNumber,
    required this.chapter,
    required this.title,
    required this.description,
    required this.tag,
    required this.durationSeconds,
    required this.likes,
    required this.xpReward,
    required this.accentColor,
  });
}

class ReelsController extends GetxController with GetTickerProviderStateMixin {
  final currentIndex = 0.obs;
  final isLiked = false.obs;
  final isSaved = false.obs;
  final currentSeconds = 0.obs;
  final activeTab = 0.obs;

  late final PageController pageController;
  late final AnimationController pulseController;

  Timer? _timer;

  static const reels = [
    ReelItem(
      element: 'Hydrogen',
      symbol: 'H',
      atomicNumber: 1,
      chapter: 'Chapter 1',
      title: 'How does covalent bonding form?',
      description:
          'Electrons are shared between atoms to reach a stable configuration — this is what makes molecules hold together.',
      tag: 'BONDING',
      durationSeconds: 30,
      likes: 1200,
      xpReward: 25,
      accentColor: Color(0xFF22D3EE),
    ),
    ReelItem(
      element: 'Oxygen',
      symbol: 'O',
      atomicNumber: 8,
      chapter: 'Chapter 3',
      title: 'What is oxidation?',
      description:
          'Oxidation is the loss of electrons. Remember the golden rule: OIL RIG — Oxidation Is Loss, Reduction Is Gain.',
      tag: 'REDOX',
      durationSeconds: 45,
      likes: 890,
      xpReward: 30,
      accentColor: Color(0xFFEF4444),
    ),
    ReelItem(
      element: 'Carbon',
      symbol: 'C',
      atomicNumber: 6,
      chapter: 'Chapter 1',
      title: 'The periodic table explained',
      description:
          'Each row is a period, each column is a group. Elements in the same group share similar chemical properties.',
      tag: 'PERIODIC TABLE',
      durationSeconds: 60,
      likes: 2300,
      xpReward: 40,
      accentColor: Color(0xFF8B7DF8),
    ),
    ReelItem(
      element: 'Sodium',
      symbol: 'Na',
      atomicNumber: 11,
      chapter: 'Chapter 2',
      title: 'Ionic bonds in salt',
      description:
          'Sodium gives its outer electron to chlorine, creating Na⁺ and Cl⁻ ions that attract each other strongly.',
      tag: 'IONIC',
      durationSeconds: 35,
      likes: 1540,
      xpReward: 28,
      accentColor: Color(0xFFFBBF24),
    ),
    ReelItem(
      element: 'Nitrogen',
      symbol: 'N',
      atomicNumber: 7,
      chapter: 'Chapter 4',
      title: 'Triple bonds & molecular stability',
      description:
          'N₂ has a triple covalent bond — the strongest type. That\'s why nitrogen gas is so stable and unreactive.',
      tag: 'COVALENT',
      durationSeconds: 50,
      likes: 980,
      xpReward: 35,
      accentColor: Color(0xFF34D399),
    ),
  ];

  ReelItem get current => reels[currentIndex.value];

  @override
  void onInit() {
    super.onInit();
    pageController = PageController();
    pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _startTimer();
  }

  void _startTimer() {
    _timer?.cancel();
    currentSeconds.value = 0;
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (currentSeconds.value < current.durationSeconds) {
        currentSeconds.value++;
      }
    });
  }

  void onPageChanged(int index) {
    currentIndex.value = index;
    isLiked.value = false;
    isSaved.value = false;
    _startTimer();
  }

  void nextReel() {
    if (currentIndex.value < reels.length - 1) {
      pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  void previousReel() {
    if (currentIndex.value > 0) {
      pageController.previousPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    }
  }

  void toggleLike() => isLiked.value = !isLiked.value;
  void toggleSave() => isSaved.value = !isSaved.value;

  double get progress => currentSeconds.value / current.durationSeconds;
  String get timeLabel => '${current.durationSeconds - currentSeconds.value}s';

  @override
  void onClose() {
    _timer?.cancel();
    pageController.dispose();
    pulseController.dispose();
    super.onClose();
  }
}
