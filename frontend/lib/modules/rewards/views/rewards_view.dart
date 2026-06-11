import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/rewards_controller.dart';

class RewardsView extends GetView<RewardsController> {
  const RewardsView({super.key});

  static const _tabs = ['AVAILABLE', 'CLAIMED', 'SHOP'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Text(
          'REWARD COLLECTION',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
      ),
      body: Column(
        children: [
          // Balance row
          _BalanceRow(controller: controller),

          // Tab bar
          Obx(() => _TabBar(
                tabs: _tabs,
                selected: controller.selectedTab.value,
                onTap: (i) => controller.selectedTab.value = i,
              )),

          // Content
          Expanded(
            child: Obx(() {
              final tab = controller.selectedTab.value;
              final List<Reward> filtered;
              if (tab == 0) {
                filtered = controller.rewards
                    .where((r) => !r.isClaimed)
                    .toList();
              } else if (tab == 1) {
                filtered = controller.rewards
                    .where((r) => r.isClaimed)
                    .toList();
              } else {
                filtered = controller.rewards.toList();
              }

              if (filtered.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.card_giftcard_outlined,
                          color: AppColors.textMuted, size: 48),
                      const SizedBox(height: 12),
                      Text(
                        tab == 1 ? 'No claimed rewards yet' : 'Nothing here',
                        style: TextStyle(
                            color: AppColors.textSecondary, fontSize: 14),
                      ),
                    ],
                  ),
                );
              }

              return ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 80),
                itemCount: filtered.length,
                itemBuilder: (_, i) => _RewardCard(reward: filtered[i]),
              );
            }),
          ),
        ],
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 16),
        color: AppColors.bgBase,
        child: Text(
          'NEXT REWARD UNLOCKS AT LVL 45',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: 11,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }
}

// ── Balance row ───────────────────────────────────────────────────────────────

class _BalanceRow extends StatelessWidget {
  final RewardsController controller;
  const _BalanceRow({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Container(
          margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.borderDefault),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _BalancePill(
                label:
                    '💎  ${_fmt(controller.crystals.value)} Crystals',
                color: AppColors.cyan,
              ),
              Container(
                  width: 1,
                  height: 24,
                  color: AppColors.borderDefault),
              _BalancePill(
                label: '⭐  ${_fmt(controller.xp.value)} XP',
                color: AppColors.amber,
              ),
            ],
          ),
        ));
  }

  String _fmt(int v) =>
      v.toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');
}

class _BalancePill extends StatelessWidget {
  final String label;
  final Color color;
  const _BalancePill({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: TextStyle(
        color: color,
        fontSize: 13,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

class _TabBar extends StatelessWidget {
  final List<String> tabs;
  final int selected;
  final ValueChanged<int> onTap;
  const _TabBar(
      {required this.tabs, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.borderDefault)),
      ),
      child: Row(
        children: List.generate(tabs.length, (i) {
          final active = i == selected;
          return Expanded(
            child: GestureDetector(
              onTap: () => onTap(i),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                      color: active ? AppColors.purple : Colors.transparent,
                      width: 2,
                    ),
                  ),
                ),
                alignment: Alignment.center,
                child: Text(
                  tabs[i],
                  style: TextStyle(
                    color:
                        active ? AppColors.purple : AppColors.textSecondary,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

// ── Reward card ───────────────────────────────────────────────────────────────

class _RewardCard extends StatelessWidget {
  final Reward reward;
  const _RewardCard({required this.reward});

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<RewardsController>();
    final locked = reward.isLocked;
    final claimed = reward.isClaimed;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: locked ? AppColors.bgCardAlt : AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: claimed
              ? AppColors.green.withOpacity(0.4)
              : locked
                  ? AppColors.borderDefault
                  : AppColors.borderDefault,
        ),
      ),
      child: Row(
        children: [
          // Emoji icon
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: locked
                  ? AppColors.bgDeep
                  : AppColors.purpleDim,
              border: Border.all(
                color: locked
                    ? AppColors.borderDefault
                    : AppColors.purple.withOpacity(0.4),
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              locked ? '🔒' : reward.emoji,
              style: const TextStyle(fontSize: 22),
            ),
          ),
          const SizedBox(width: 12),
          // Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  reward.name,
                  style: TextStyle(
                    color: locked
                        ? AppColors.textMuted
                        : AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  reward.description,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 11,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          // Cost + claim button
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (reward.cost > 0)
                Text(
                  reward.type == RewardType.crystal
                      ? '💎 ${reward.cost}'
                      : '⭐ ${reward.cost}',
                  style: TextStyle(
                    color: reward.type == RewardType.crystal
                        ? AppColors.cyan
                        : AppColors.amber,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                )
              else
                Text(
                  'FREE',
                  style: TextStyle(
                    color: AppColors.green,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              const SizedBox(height: 6),
              GestureDetector(
                onTap: locked || claimed
                    ? null
                    : () => ctrl.claimReward(reward.id),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    gradient: (!locked && !claimed)
                        ? AppColors.gradientPurple
                        : null,
                    color: (locked || claimed) ? AppColors.bgCardAlt : null,
                    borderRadius: BorderRadius.circular(8),
                    border: (locked || claimed)
                        ? Border.all(color: AppColors.borderDefault)
                        : null,
                  ),
                  child: Text(
                    claimed
                        ? 'CLAIMED'
                        : locked
                            ? 'LOCKED'
                            : 'CLAIM',
                    style: TextStyle(
                      color: locked || claimed
                          ? AppColors.textMuted
                          : Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
