import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/collaboration_controller.dart';

class CollaborationView extends GetView<CollaborationController> {
  const CollaborationView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Text(
          'COLLABORATION QUEST',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.share_outlined,
                color: AppColors.textSecondary, size: 20),
            onPressed: () {},
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Hero banner
            _HeroBanner(controller: controller),
            const SizedBox(height: 16),

            // Team section
            _SectionLabel(label: 'TEAM'),
            const SizedBox(height: 8),
            _TeamGrid(controller: controller),
            const SizedBox(height: 16),

            // Quest log
            _SectionLabel(label: 'QUEST LOG'),
            const SizedBox(height: 8),
            _QuestLog(controller: controller),
            const SizedBox(height: 16),

            // Activity feed
            _SectionLabel(label: 'ACTIVITY FEED'),
            const SizedBox(height: 8),
            _ActivityFeed(),
          ],
        ),
      ),
      floatingActionButton: Obx(() => FloatingActionButton.extended(
            onPressed:
                controller.hasSubmitted.value ? null : controller.submit,
            backgroundColor: controller.hasSubmitted.value
                ? AppColors.bgCardAlt
                : AppColors.purple,
            icon: Icon(
              controller.hasSubmitted.value
                  ? Icons.check_circle_outline
                  : Icons.upload_outlined,
              color: controller.hasSubmitted.value
                  ? AppColors.textMuted
                  : Colors.white,
            ),
            label: Text(
              controller.hasSubmitted.value
                  ? 'SUBMITTED'
                  : 'SUBMIT CONTRIBUTION',
              style: TextStyle(
                color: controller.hasSubmitted.value
                    ? AppColors.textMuted
                    : Colors.white,
                fontWeight: FontWeight.w800,
                letterSpacing: 1,
                fontSize: 12,
              ),
            ),
          )),
    );
  }
}

// ── Hero banner ───────────────────────────────────────────────────────────────

class _HeroBanner extends StatelessWidget {
  final CollaborationController controller;
  const _HeroBanner({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final pct = controller.progress.value;
      return Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [AppColors.purpleDim, AppColors.bgCard],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.purple.withOpacity(0.4)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🧬', style: const TextStyle(fontSize: 32)),
            const SizedBox(height: 8),
            Text(
              'Project: Synthesis Challenge',
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'TEAM QUANTUM · COLLABORATIVE RESEARCH',
              style: TextStyle(
                color: AppColors.textMuted,
                fontSize: 10,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: pct,
                      minHeight: 8,
                      backgroundColor: AppColors.bgDeep,
                      valueColor:
                          AlwaysStoppedAnimation(AppColors.purple),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  '${(pct * 100).toInt()}%',
                  style: TextStyle(
                    color: AppColors.purpleLight,
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    });
  }
}

// ── Team grid ─────────────────────────────────────────────────────────────────

class _TeamGrid extends StatelessWidget {
  final CollaborationController controller;
  const _TeamGrid({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Row(
          children: controller.members
              .map((m) => Expanded(
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.bgCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.borderDefault),
                      ),
                      child: Column(
                        children: [
                          Stack(
                            clipBehavior: Clip.none,
                            children: [
                              Text(m.emoji,
                                  style:
                                      const TextStyle(fontSize: 22)),
                              if (m.isOnline)
                                Positioned(
                                  bottom: -2,
                                  right: -4,
                                  child: Container(
                                    width: 9,
                                    height: 9,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      color: AppColors.online,
                                      border: Border.all(
                                          color: AppColors.bgCard,
                                          width: 1.5),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            m.name,
                            style: TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                            ),
                            textAlign: TextAlign.center,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${(m.contribution * 100).toInt()}%',
                            style: TextStyle(
                              color: AppColors.cyan,
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ))
              .toList(),
        ));
  }
}

// ── Quest log ─────────────────────────────────────────────────────────────────

class _QuestLog extends StatelessWidget {
  final CollaborationController controller;
  const _QuestLog({required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Column(
          children: controller.tasks
              .map((t) => GestureDetector(
                    onTap: () => controller.toggleTask(t.id),
                    child: Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: AppColors.bgCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: t.isCompleted
                              ? AppColors.green.withOpacity(0.4)
                              : AppColors.borderDefault,
                        ),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 20,
                            height: 20,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: t.isCompleted
                                  ? AppColors.green
                                  : Colors.transparent,
                              border: Border.all(
                                color: t.isCompleted
                                    ? AppColors.green
                                    : AppColors.textMuted,
                                width: 2,
                              ),
                            ),
                            child: t.isCompleted
                                ? const Icon(Icons.check,
                                    color: Colors.white, size: 12)
                                : null,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              t.title,
                              style: TextStyle(
                                color: t.isCompleted
                                    ? AppColors.textMuted
                                    : AppColors.textPrimary,
                                fontSize: 13,
                                decoration: t.isCompleted
                                    ? TextDecoration.lineThrough
                                    : null,
                              ),
                            ),
                          ),
                          Text(
                            t.assignee,
                            style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ))
              .toList(),
        ));
  }
}

// ── Activity feed ─────────────────────────────────────────────────────────────

class _ActivityFeed extends StatelessWidget {
  static const _activities = [
    _Activity('🌟', 'NovaStar99', 'completed "Analyze reaction pathways"', '2m ago'),
    _Activity('⚛️', 'QuantumKid', 'uploaded synthesis documentation', '14m ago'),
    _Activity('🧙', 'ChemWizard', 'started simulation models', '1h ago'),
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: _activities
          .map((a) => Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.bgCard,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.borderDefault),
                ),
                child: Row(
                  children: [
                    Text(a.emoji,
                        style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: RichText(
                        text: TextSpan(children: [
                          TextSpan(
                            text: '${a.name} ',
                            style: TextStyle(
                              color: AppColors.cyan,
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: a.action,
                            style: TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                        ]),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      a.time,
                      style: TextStyle(
                          color: AppColors.textMuted, fontSize: 10),
                    ),
                  ],
                ),
              ))
          .toList(),
    );
  }
}

class _Activity {
  final String emoji;
  final String name;
  final String action;
  final String time;
  const _Activity(this.emoji, this.name, this.action, this.time);
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
        fontWeight: FontWeight.w700,
        letterSpacing: 2,
      ),
    );
  }
}
