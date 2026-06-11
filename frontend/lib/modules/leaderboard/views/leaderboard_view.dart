import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/leaderboard_controller.dart';

class LeaderboardView extends GetView<LeaderboardController> {
  const LeaderboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Row(
          children: [
            Icon(Icons.emoji_events_outlined, color: AppColors.amber, size: 20),
            const SizedBox(width: 8),
            Text(
              'LEADERBOARD',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 2,
              ),
            ),
          ],
        ),
        actions: [
          // Weekly Challenge badge
          Container(
            margin: const EdgeInsets.only(right: 12),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.purpleDim,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.purple.withOpacity(0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.timer_outlined, color: AppColors.purple, size: 12),
                const SizedBox(width: 4),
                Text(
                  'WEEKLY · 3d',
                  style: TextStyle(
                    color: AppColors.purple,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Obx(() => Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: ['GLOBAL', 'FRIENDS'].map((f) {
                    final active = controller.filter.value == f;
                    return GestureDetector(
                      onTap: () => controller.setFilter(f),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 8),
                        decoration: BoxDecoration(
                          color: active ? AppColors.purple : AppColors.bgCard,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: active
                                ? AppColors.purple
                                : AppColors.borderDefault,
                          ),
                        ),
                        child: Text(
                          f,
                          style: TextStyle(
                            color: active
                                ? Colors.white
                                : AppColors.textSecondary,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                )),
          ),

          Expanded(
            child: Obx(() {
              final all = controller.entries;
              final top3 = all.take(3).toList();
              final rest = all.skip(3).where((e) => !e.isCurrentUser).toList();
              final me = all.firstWhereOrNull((e) => e.isCurrentUser);

              return Column(
                children: [
                  // Podium
                  _Podium(top3: top3),

                  // Ranked list
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      itemCount: rest.length,
                      itemBuilder: (_, i) =>
                          _RankRow(entry: rest[i]),
                    ),
                  ),

                  // Current user sticky entry
                  if (me != null) _StickyUserRow(entry: me),
                ],
              );
            }),
          ),
        ],
      ),
    );
  }
}

// ── Podium ────────────────────────────────────────────────────────────────────

class _Podium extends StatelessWidget {
  final List<LeaderboardEntry> top3;
  const _Podium({required this.top3});

  @override
  Widget build(BuildContext context) {
    if (top3.length < 3) return const SizedBox();
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 4),
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _PodiumSlot(entry: top3[1], medalColor: const Color(0xFFC0C0C0), height: 70),
          _PodiumSlot(entry: top3[0], medalColor: AppColors.amber, height: 100),
          _PodiumSlot(entry: top3[2], medalColor: const Color(0xFFCD7F32), height: 55),
        ],
      ),
    );
  }
}

class _PodiumSlot extends StatelessWidget {
  final LeaderboardEntry entry;
  final Color medalColor;
  final double height;
  const _PodiumSlot(
      {required this.entry, required this.medalColor, required this.height});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(entry.avatarEmoji, style: const TextStyle(fontSize: 28)),
        const SizedBox(height: 4),
        Text(
          entry.name,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          '${(entry.xp / 1000).toStringAsFixed(1)}k XP',
          style: TextStyle(color: AppColors.textSecondary, fontSize: 10),
        ),
        const SizedBox(height: 6),
        Container(
          width: 60,
          height: height,
          decoration: BoxDecoration(
            color: medalColor.withOpacity(0.15),
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(8),
              topRight: Radius.circular(8),
            ),
            border: Border.all(color: medalColor.withOpacity(0.4)),
          ),
          alignment: Alignment.center,
          child: Text(
            '#${entry.rank}',
            style: TextStyle(
              color: medalColor,
              fontSize: 20,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ],
    );
  }
}

// ── Rank row ──────────────────────────────────────────────────────────────────

class _RankRow extends StatelessWidget {
  final LeaderboardEntry entry;
  const _RankRow({required this.entry});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 24,
            child: Text(
              '#${entry.rank}',
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Text(entry.avatarEmoji, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              entry.name,
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            '${entry.xp.toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},')} XP',
            style: TextStyle(color: AppColors.cyan, fontSize: 12, fontWeight: FontWeight.w700),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppColors.purpleDim,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'LVL ${entry.level}',
              style: TextStyle(
                color: AppColors.purpleLight,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sticky current user row ───────────────────────────────────────────────────

class _StickyUserRow extends StatelessWidget {
  final LeaderboardEntry entry;
  const _StickyUserRow({required this.entry});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.purpleDim,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.purple.withOpacity(0.6)),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 24,
            child: Text(
              '#${entry.rank}',
              style: TextStyle(
                color: AppColors.purple,
                fontSize: 12,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Text(entry.avatarEmoji, style: const TextStyle(fontSize: 20)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.name,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  'YOUR RANK',
                  style: TextStyle(
                    color: AppColors.purple,
                    fontSize: 9,
                    letterSpacing: 1.2,
                  ),
                ),
              ],
            ),
          ),
          Text(
            '${entry.xp.toString().replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},')} XP',
            style: TextStyle(
                color: AppColors.purpleLight,
                fontSize: 13,
                fontWeight: FontWeight.w800),
          ),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppColors.purple.withOpacity(0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'LVL ${entry.level}',
              style: TextStyle(
                color: AppColors.purpleLight,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.8,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
