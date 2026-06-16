import 'dart:async';

import 'package:get/get.dart';

class DailyChallenge {
  final String id;
  final String title;
  final String description;
  final int xp;
  final String difficulty; // QUICK | STANDARD | HARDCORE
  final bool isCompleted;
  final int durationMin;

  const DailyChallenge({
    required this.id,
    required this.title,
    required this.description,
    required this.xp,
    required this.difficulty,
    this.isCompleted = false,
    required this.durationMin,
  });

  DailyChallenge copyWith({bool? isCompleted}) => DailyChallenge(
        id: id,
        title: title,
        description: description,
        xp: xp,
        difficulty: difficulty,
        isCompleted: isCompleted ?? this.isCompleted,
        durationMin: durationMin,
      );
}

class DailyChallengesController extends GetxController {
  final challenges = <DailyChallenge>[].obs;
  final streak = 12.obs;
  final hoursLeft = 8.obs;
  final minutesLeft = 24.obs;
  final secondsLeft = 33.obs;

  Timer? _timer;

  @override
  void onInit() {
    super.onInit();
    challenges.addAll(const [
      DailyChallenge(
        id: '1',
        title: 'Quick Bonds Quiz',
        description: 'Identify covalent vs ionic bonds in 10 questions.',
        xp: 100,
        difficulty: 'QUICK',
        durationMin: 5,
      ),
      DailyChallenge(
        id: '2',
        title: 'Stoichiometry Sprint',
        description: 'Balance 8 chemical equations against the clock.',
        xp: 250,
        difficulty: 'STANDARD',
        durationMin: 15,
      ),
      DailyChallenge(
        id: '3',
        title: 'Quantum Gauntlet',
        description: 'Master electron configurations & quantum numbers.',
        xp: 500,
        difficulty: 'HARDCORE',
        durationMin: 30,
      ),
    ]);
    _startTimer();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (secondsLeft.value > 0) {
        secondsLeft.value--;
      } else if (minutesLeft.value > 0) {
        minutesLeft.value--;
        secondsLeft.value = 59;
      } else if (hoursLeft.value > 0) {
        hoursLeft.value--;
        minutesLeft.value = 59;
        secondsLeft.value = 59;
      }
    });
  }

  void startChallenge(String id) {
    // Navigate to challenge or show detail
    Get.snackbar(
      'Challenge Started',
      challenges.firstWhere((c) => c.id == id).title,
      snackPosition: SnackPosition.BOTTOM,
    );
  }

  void claimReward(String id) {
    final idx = challenges.indexWhere((c) => c.id == id);
    if (idx == -1) return;
    challenges[idx] = challenges[idx].copyWith(isCompleted: true);
  }

  @override
  void onClose() {
    _timer?.cancel();
    super.onClose();
  }
}
