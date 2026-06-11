import 'package:get/get.dart';

enum RewardType { xpReward, crystal, gear }

class Reward {
  final String id;
  final String emoji;
  final String name;
  final String description;
  final int cost;
  final bool isClaimed;
  final bool isLocked;
  final RewardType type;

  const Reward({
    required this.id,
    required this.emoji,
    required this.name,
    required this.description,
    required this.cost,
    this.isClaimed = false,
    this.isLocked = false,
    required this.type,
  });

  Reward copyWith({bool? isClaimed}) => Reward(
        id: id,
        emoji: emoji,
        name: name,
        description: description,
        cost: cost,
        isClaimed: isClaimed ?? this.isClaimed,
        isLocked: isLocked,
        type: type,
      );
}

class RewardsController extends GetxController {
  final rewards = <Reward>[].obs;
  final crystals = 2840.obs;
  final xp = 14500.obs;
  final selectedTab = 0.obs;

  @override
  void onInit() {
    super.onInit();
    rewards.addAll(const [
      Reward(
        id: '1',
        emoji: '⚡',
        name: 'XP Booster x2',
        description: 'Double your XP earnings for 24 hours.',
        cost: 0,
        type: RewardType.xpReward,
      ),
      Reward(
        id: '2',
        emoji: '💎',
        name: 'Crystal Pack',
        description: 'Receive 200 bonus crystals.',
        cost: 500,
        type: RewardType.crystal,
      ),
      Reward(
        id: '3',
        emoji: '🧪',
        name: 'Rare Flask',
        description: 'Exclusive lab flask cosmetic item.',
        cost: 200,
        type: RewardType.gear,
      ),
      Reward(
        id: '4',
        emoji: '🛡️',
        name: 'Streak Shield',
        description: 'Protect your streak for one missed day. (Day 14)',
        cost: 0,
        type: RewardType.xpReward,
      ),
      Reward(
        id: '5',
        emoji: '🔭',
        name: 'Epic Scope',
        description: 'Legendary gear — unlocks at LVL 45.',
        cost: 0,
        isLocked: true,
        type: RewardType.gear,
      ),
    ]);
  }

  void claimReward(String id) {
    final idx = rewards.indexWhere((r) => r.id == id);
    if (idx == -1) return;
    final r = rewards[idx];
    if (r.isLocked || r.isClaimed) return;

    // Deduct cost
    if (r.type == RewardType.crystal && r.cost > 0) {
      if (crystals.value < r.cost) return;
      crystals.value -= r.cost;
    } else if (r.cost > 0) {
      if (xp.value < r.cost) return;
      xp.value -= r.cost;
    }

    rewards[idx] = r.copyWith(isClaimed: true);
  }
}
