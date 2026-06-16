import 'package:get/get.dart';

class Milestone {
  final String icon;
  final String label;
  final bool unlocked;

  const Milestone({
    required this.icon,
    required this.label,
    required this.unlocked,
  });
}

class ProfileController extends GetxController {
  // Stats
  final xpPercent = 0.75;
  final lessonsPercent = 0.50;
  final accuracyPercent = 0.92;

  final xp = 12450;
  final level = 28;
  final levelTitle = 'Alchemist';
  final lessonsCompleted = 18;
  final lessonsTotal = 36;
  final lessonsCourse = 'Organic Chemistry I';
  final rankLabel = 'Elite';
  final rankSub = 'Top 5% of Students';

  // Study heatmap: 12 weeks × 7 days (0=none, 1=low, 2=mid, 3=high)
  final List<List<int>> heatmap = List.generate(
    12,
    (w) => List.generate(
      7,
      (d) {
        final v = ((w * 7 + d) * 37 + 13) % 4;
        return v;
      },
    ),
  );

  final milestones = const [
    Milestone(icon: '🏆', label: 'Element Master', unlocked: true),
    Milestone(icon: '⚗️', label: 'Bond Creator', unlocked: true),
    Milestone(icon: '🔥', label: 'First Reaction', unlocked: true),
    Milestone(icon: '🔬', label: 'Quantum Leap', unlocked: false),
    Milestone(icon: '🧪', label: 'Lab Director', unlocked: false),
    Milestone(icon: '🌿', label: 'Organic Catalyst', unlocked: false),
  ];

  final learningSpeed = const [
    ('Theoretical Chemistry', 0.58),
    ('Biochemistry', 0.82),
  ];

  final speedLabels = const [
    '2.4 mole/Cal/wk',
    '4.1 mole/Cal/wk',
  ];

  final aiRate = 12.4;
  final aiTrend = -5;
  final aiQuote = '"You\'re showing strong autonomous growth in Redox Reactions."';
}
