import 'package:get/get.dart';

class LeaderboardEntry {
  final int rank;
  final String name;
  final int xp;
  final int level;
  final bool isCurrentUser;
  final String avatarEmoji;

  const LeaderboardEntry({
    required this.rank,
    required this.name,
    required this.xp,
    required this.level,
    this.isCurrentUser = false,
    required this.avatarEmoji,
  });
}

class LeaderboardController extends GetxController {
  final entries = <LeaderboardEntry>[].obs;
  final filter = 'GLOBAL'.obs;
  final currentUserRank = 7.obs;

  @override
  void onInit() {
    super.onInit();
    entries.addAll([
      const LeaderboardEntry(rank: 1, name: 'NovaStar99',   xp: 24500, level: 52, avatarEmoji: '🌟'),
      const LeaderboardEntry(rank: 2, name: 'QuantumKid',   xp: 22100, level: 48, avatarEmoji: '⚛️'),
      const LeaderboardEntry(rank: 3, name: 'ChemWizard',   xp: 19800, level: 44, avatarEmoji: '🧙'),
      const LeaderboardEntry(rank: 4, name: 'MoleMaster',   xp: 17600, level: 41, avatarEmoji: '🔬'),
      const LeaderboardEntry(rank: 5, name: 'BondBreaker',  xp: 15900, level: 38, avatarEmoji: '⚡'),
      const LeaderboardEntry(rank: 6, name: 'ProtonPilot',  xp: 14200, level: 35, avatarEmoji: '🚀'),
      LeaderboardEntry(rank: 7, name: 'You',               xp: 12800, level: 32, isCurrentUser: true, avatarEmoji: '🎯'),
      const LeaderboardEntry(rank: 8, name: 'NeutronNova',  xp: 11400, level: 30, avatarEmoji: '💫'),
      const LeaderboardEntry(rank: 9, name: 'AtomicAce',    xp: 10200, level: 28, avatarEmoji: '🔭'),
      const LeaderboardEntry(rank: 10, name: 'ElementElite', xp: 9100, level: 26, avatarEmoji: '🏅'),
    ]);
  }

  void setFilter(String f) => filter.value = f;
}
