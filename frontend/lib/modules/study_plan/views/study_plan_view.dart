import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/study_plan_controller.dart';

class StudyPlanView extends GetView<StudyPlanController> {
  const StudyPlanView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Text(
          'STUDY PLAN',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 13,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.8,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.tune_rounded,
                color: AppColors.textSecondary, size: 20),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // AI plan header
            Obx(
              () => Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color: AppColors.purple.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.purple.withOpacity(0.15),
                      ),
                      child: const Center(
                          child: Text('🤖',
                              style: TextStyle(fontSize: 22))),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'AI PERSONALIZED PLAN',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 10,
                              letterSpacing: 1.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'For ${controller.userName.value}',
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: controller.regeneratePlan,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppColors.purple.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                              color: AppColors.purple.withOpacity(0.3)),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.refresh_rounded,
                                color: AppColors.purple, size: 14),
                            const SizedBox(width: 4),
                            Text(
                              'Update',
                              style: TextStyle(
                                color: AppColors.purple,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Weekly overview
            _SectionLabel(label: 'WEEKLY OVERVIEW'),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.bgCard,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.borderDefault),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(
                  7,
                  (i) => _DayChip(
                    day: controller.weekDays[i],
                    isCompleted: controller.weekStatus[i],
                    isToday: i == 4,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Today's plan
            _SectionLabel(label: "TODAY'S PLAN"),
            const SizedBox(height: 10),
            Obx(
              () => Column(
                children: controller.todayItems
                    .map((item) => _StudyItemCard(
                          item: item,
                          onToggle: () => controller.toggleItem(item.id),
                        ))
                    .toList(),
              ),
            ),

            const SizedBox(height: 20),

            // Suggested resources
            _SectionLabel(label: 'SUGGESTED RESOURCES'),
            const SizedBox(height: 10),
            ...controller.suggestedResources
                .map((r) => _ResourceCard(resource: r)),

            const SizedBox(height: 20),

            // Progress summary
            Obx(
              () => Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'WEEKLY PROGRESS',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 10,
                              letterSpacing: 1.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'This week: ${controller.weeklyProgress.value}/${controller.weeklyGoal.value} sessions completed',
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 10),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: controller.weeklyProgress.value /
                                  controller.weeklyGoal.value,
                              backgroundColor:
                                  AppColors.borderDefault,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                  AppColors.green),
                              minHeight: 6,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Text(
                      '${((controller.weeklyProgress.value / controller.weeklyGoal.value) * 100).toInt()}%',
                      style: TextStyle(
                        color: AppColors.green,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            // Regenerate button
            SizedBox(
              width: double.infinity,
              height: 50,
              child: OutlinedButton.icon(
                onPressed: controller.regeneratePlan,
                style: OutlinedButton.styleFrom(
                  side: BorderSide(
                      color: AppColors.cyan.withOpacity(0.5), width: 1.5),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(25),
                  ),
                ),
                icon: Icon(Icons.auto_awesome_rounded,
                    color: AppColors.cyan, size: 18),
                label: Text(
                  'REGENERATE PLAN',
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.5,
                  ),
                ),
              ),
            ),

            const SizedBox(height: 28),
          ],
        ),
      ),
    );
  }
}

// ── Day chip ──────────────────────────────────────────────────────────────────
class _DayChip extends StatelessWidget {
  final String day;
  final bool isCompleted;
  final bool isToday;
  const _DayChip(
      {required this.day,
      required this.isCompleted,
      required this.isToday});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          day,
          style: TextStyle(
            color: isToday ? AppColors.textPrimary : AppColors.textMuted,
            fontSize: 11,
            fontWeight: isToday ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isCompleted ? AppColors.green : AppColors.borderDefault,
            border: isToday
                ? Border.all(color: AppColors.cyan, width: 1.5)
                : null,
          ),
        ),
      ],
    );
  }
}

// ── Study item card ───────────────────────────────────────────────────────────
class _StudyItemCard extends StatelessWidget {
  final StudyItem item;
  final VoidCallback onToggle;
  const _StudyItemCard({required this.item, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    return Obx(
      () => GestureDetector(
        onTap: onToggle,
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: item.isCompleted.value
                  ? AppColors.green.withOpacity(0.3)
                  : AppColors.borderDefault,
            ),
          ),
          child: Row(
            children: [
              // Time
              SizedBox(
                width: 52,
                child: Text(
                  item.time,
                  style: TextStyle(
                    color: AppColors.cyan,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              // Divider
              Container(
                  width: 1,
                  height: 36,
                  color: AppColors.borderDefault,
                  margin: const EdgeInsets.only(right: 12)),
              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: TextStyle(
                        color: item.isCompleted.value
                            ? AppColors.textMuted
                            : AppColors.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        decoration: item.isCompleted.value
                            ? TextDecoration.lineThrough
                            : null,
                        decorationColor: AppColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${item.durationMin} min',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              // Check
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 28,
                height: 28,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: item.isCompleted.value
                      ? AppColors.green.withOpacity(0.2)
                      : Colors.transparent,
                  border: Border.all(
                    color: item.isCompleted.value
                        ? AppColors.green
                        : AppColors.textMuted.withOpacity(0.3),
                    width: 1.5,
                  ),
                ),
                child: item.isCompleted.value
                    ? Icon(Icons.check_rounded,
                        color: AppColors.green, size: 16)
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Resource card ─────────────────────────────────────────────────────────────
class _ResourceCard extends StatelessWidget {
  final Map<String, dynamic> resource;
  const _ResourceCard({required this.resource});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.purple.withOpacity(0.15),
            ),
            child: Icon(Icons.play_circle_outline_rounded,
                color: AppColors.purple, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  resource['title'] as String,
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    Text(
                      resource['type'] as String,
                      style: TextStyle(
                        color: AppColors.purple,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    Text(
                      ' · ${resource['duration']}',
                      style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Icon(Icons.arrow_forward_ios_rounded,
              color: AppColors.textMuted, size: 14),
        ],
      ),
    );
  }
}

// ── Section label ─────────────────────────────────────────────────────────────
class _SectionLabel extends StatelessWidget {
  final String label;
  const _SectionLabel({required this.label});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: TextStyle(
        color: AppColors.textMuted,
        fontSize: 10,
        letterSpacing: 2,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}
