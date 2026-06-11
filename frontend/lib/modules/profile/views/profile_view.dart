import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/profile_controller.dart';

class ProfileView extends GetView<ProfileController> {
  const ProfileView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgDeep,
      appBar: AppBar(
        backgroundColor: AppColors.bgDeep,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded,
              color: AppColors.textPrimary, size: 18),
          onPressed: Get.back,
        ),
        title: Text(
          'profile_performance_data'.tr,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.settings_outlined,
                color: AppColors.textSecondary, size: 20),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _CircleStatCard(
              percent: controller.xpPercent,
              centerLabel: 'XP GOAL',
              color: AppColors.purple,
              valueLine: '${_fmt(controller.xp)} XP',
              subLine: 'Level ${controller.level} ${controller.levelTitle}',
            ),
            const SizedBox(height: 12),
            _CircleStatCard(
              percent: controller.lessonsPercent,
              centerLabel: 'LESSONS',
              color: const Color(0xFFFBBF24),
              valueLine:
                  '${controller.lessonsCompleted}/${controller.lessonsTotal}',
              subLine: controller.lessonsCourse,
            ),
            const SizedBox(height: 12),
            _CircleStatCard(
              percent: controller.accuracyPercent,
              centerLabel: 'ACCURACY',
              color: AppColors.green,
              valueLine: controller.rankLabel,
              subLine: controller.rankSub,
            ),
            const SizedBox(height: 24),
            _StudyConsistencyCard(heatmap: controller.heatmap),
            const SizedBox(height: 24),
            _ScientificMilestonesSection(milestones: controller.milestones),
            const SizedBox(height: 24),
            _LearningSpeedCard(
              items: controller.learningSpeed,
              labels: controller.speedLabels,
            ),
            const SizedBox(height: 24),
            _AIAssistanceCard(
              rate: controller.aiRate,
              trend: controller.aiTrend,
              quote: controller.aiQuote,
            ),
          ],
        ),
      ),
    );
  }

  static String _fmt(int n) {
    final s = n.toString();
    if (s.length > 3) return '${s.substring(0, s.length - 3)},${s.substring(s.length - 3)}';
    return s;
  }
}

// ── Circular stat card ─────────────────────────────────────────────────────────
class _CircleStatCard extends StatelessWidget {
  final double percent;
  final String centerLabel;
  final Color color;
  final String valueLine;
  final String subLine;

  const _CircleStatCard({
    required this.percent,
    required this.centerLabel,
    required this.color,
    required this.valueLine,
    required this.subLine,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        children: [
          SizedBox(
            width: 130,
            height: 130,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CircularProgressIndicator(
                    value: percent,
                    strokeWidth: 11,
                    backgroundColor: AppColors.borderDefault,
                    valueColor: AlwaysStoppedAnimation<Color>(color),
                    strokeCap: StrokeCap.round,
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${(percent * 100).toInt()}%',
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 30,
                        fontWeight: FontWeight.w800,
                        height: 1.1,
                      ),
                    ),
                    Text(
                      centerLabel,
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 9,
                        letterSpacing: 1.8,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Text(
            valueLine,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(subLine, style: TextStyle(color: color, fontSize: 12)),
        ],
      ),
    );
  }
}

// ── Study consistency heatmap ──────────────────────────────────────────────────
class _StudyConsistencyCard extends StatelessWidget {
  final List<List<int>> heatmap;
  const _StudyConsistencyCard({required this.heatmap});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'profile_study_consistency'.tr,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Text('profile_less'.tr,
                  style: TextStyle(color: AppColors.textMuted, fontSize: 9)),
              const SizedBox(width: 4),
              ...[0, 1, 2, 3].map((v) => Container(
                    width: 10,
                    height: 10,
                    margin: const EdgeInsets.only(right: 3),
                    decoration: BoxDecoration(
                      color: _heatColor(v),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  )),
              Text('profile_more'.tr,
                  style: TextStyle(color: AppColors.textMuted, fontSize: 9)),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'profile_consistency_subtitle'.tr,
            style: TextStyle(color: AppColors.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 14),
          Row(
            children: List.generate(12, (w) {
              return Expanded(
                child: Column(
                  children: List.generate(7, (d) {
                    return Container(
                      height: 11,
                      margin: const EdgeInsets.all(1.5),
                      decoration: BoxDecoration(
                        color: _heatColor(heatmap[w][d]),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    );
                  }),
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          const Row(
            children: [
              Expanded(flex: 3, child: _MonthLabel('SEP')),
              Expanded(flex: 3, child: _MonthLabel('OCT')),
              Expanded(flex: 3, child: _MonthLabel('NOV')),
              Expanded(flex: 3, child: _MonthLabel('DEC')),
            ],
          ),
        ],
      ),
    );
  }

  Color _heatColor(int v) {
    switch (v) {
      case 1: return AppColors.purple.withOpacity(0.25);
      case 2: return AppColors.purple.withOpacity(0.55);
      case 3: return AppColors.purple;
      default: return AppColors.borderDefault;
    }
  }
}

class _MonthLabel extends StatelessWidget {
  final String text;
  const _MonthLabel(this.text);

  @override
  Widget build(BuildContext context) => Text(
        text,
        textAlign: TextAlign.center,
        style: TextStyle(color: AppColors.textMuted, fontSize: 9),
      );
}

// ── Scientific milestones ──────────────────────────────────────────────────────
class _ScientificMilestonesSection extends StatelessWidget {
  final List<Milestone> milestones;
  const _ScientificMilestonesSection({required this.milestones});

  static const _tierColors = [
    Color(0xFFFBBF24),
    Color(0xFF94A3B8),
    Color(0xFFF97316),
  ];
  static List<String> get _tierLabels => [
    'profile_tier_gold'.tr,
    'profile_tier_silver'.tr,
    'profile_tier_bronze'.tr,
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'profile_scientific_milestones'.tr,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.15,
          children: List.generate(milestones.length, (i) {
            return _MilestoneCard(
              milestone: milestones[i],
              tierColor: i < 3 ? _tierColors[i] : null,
              tierLabel: i < 3 ? _tierLabels[i] : null,
            );
          }),
        ),
      ],
    );
  }
}

class _MilestoneCard extends StatelessWidget {
  final Milestone milestone;
  final Color? tierColor;
  final String? tierLabel;

  const _MilestoneCard({
    required this.milestone,
    this.tierColor,
    this.tierLabel,
  });

  @override
  Widget build(BuildContext context) {
    final unlocked = milestone.unlocked;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: unlocked && tierColor != null
              ? tierColor!.withOpacity(0.4)
              : AppColors.borderDefault,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: unlocked && tierColor != null
                  ? tierColor!.withOpacity(0.12)
                  : AppColors.bgCardAlt,
              border: Border.all(
                color: unlocked && tierColor != null
                    ? tierColor!.withOpacity(0.5)
                    : AppColors.borderDefault,
              ),
            ),
            child: Center(
              child: unlocked
                  ? Text(milestone.icon,
                      style: const TextStyle(fontSize: 22))
                  : Icon(Icons.lock_outline,
                      color: AppColors.textMuted, size: 20),
            ),
          ),
          const SizedBox(height: 8),
          if (tierLabel != null && unlocked) ...[
            Text(
              tierLabel!,
              style: TextStyle(
                color: tierColor,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 2),
          ],
          Text(
            milestone.label,
            style: TextStyle(
              color: unlocked ? AppColors.textPrimary : AppColors.textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

// ── Learning speed ─────────────────────────────────────────────────────────────
class _LearningSpeedCard extends StatelessWidget {
  final List<(String, double)> items;
  final List<String> labels;

  const _LearningSpeedCard({required this.items, required this.labels});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'profile_learning_speed'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 16),
          ...List.generate(items.length, (i) {
            final (name, value) = items[i];
            final parts = labels[i].split(' ');
            final numPart = parts.first;
            final unitPart = parts.skip(1).join(' ');
            return Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(name,
                          style: TextStyle(
                              color: AppColors.textSecondary, fontSize: 13)),
                      RichText(
                        text: TextSpan(
                          children: [
                            TextSpan(
                              text: '$numPart ',
                              style: TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            TextSpan(
                              text: unitPart,
                              style: TextStyle(
                                color: AppColors.purple,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: value,
                      minHeight: 7,
                      backgroundColor: AppColors.borderDefault,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AppColors.purple),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}

// ── AI assistance rate ─────────────────────────────────────────────────────────
class _AIAssistanceCard extends StatelessWidget {
  final double rate;
  final int trend;
  final String quote;

  const _AIAssistanceCard({
    required this.rate,
    required this.trend,
    required this.quote,
  });

  @override
  Widget build(BuildContext context) {
    final isImproving = trend < 0;
    final trendColor = isImproving ? AppColors.green : AppColors.danger;
    final trendText = trend < 0 ? '$trend%' : '+$trend%';

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'profile_ai_assistance'.tr,
            style: TextStyle(
              color: AppColors.textPrimary,
              fontSize: 15,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${rate.toStringAsFixed(1)}%',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 36,
                  fontWeight: FontWeight.w800,
                  height: 1,
                ),
              ),
              const SizedBox(width: 10),
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: trendColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: trendColor.withOpacity(0.4)),
                  ),
                  child: Text(
                    '$trendText from last week',
                    style: TextStyle(
                      color: trendColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'profile_ai_hint_reliance'.tr,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 4),
          Text(
            'profile_ai_solving_up'.tr,
            style: TextStyle(color: AppColors.green, fontSize: 12),
          ),
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.bgCardAlt,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Text(
              quote,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
