import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../data/models/chapter_model.dart';

class ChapterCard extends StatelessWidget {
  final ChapterModel chapter;
  final VoidCallback? onResume;
  final int index;

  const ChapterCard({
    super.key,
    required this.chapter,
    this.onResume,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    final isLocked = chapter.status == ChapterStatus.locked;
    final isCompleted = chapter.status == ChapterStatus.completed;
    final isActive = chapter.status == ChapterStatus.active;

    Color leftBorderColor = switch (chapter.status) {
      ChapterStatus.completed => AppColors.green,
      ChapterStatus.active    => AppColors.purple,
      ChapterStatus.locked    => AppColors.textMuted,
    };

    return AnimatedOpacity(
      duration:  Duration(milliseconds: 300),
      opacity: isLocked ? 0.55 : 1.0,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.bgCard,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.borderDefault),
        ),
        clipBehavior: Clip.antiAlias,
        child: IntrinsicHeight(
          child: Row(
            children: [
              // Left accent bar
              Container(width: 4, color: leftBorderColor),

              // Content
              Expanded(
                child: Padding(
                  padding:  EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Chapter label
                      Text(
                        'Chapter ${chapter.number}',
                        style: TextStyle(
                          color: leftBorderColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.5,
                        ),
                      ),

                       SizedBox(height: 4),

                      // Title row
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              chapter.title,
                              style: TextStyle(
                                color: isLocked
                                    ? AppColors.textSecondary
                                    : AppColors.textPrimary,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          _StatusIcon(chapter: chapter),
                        ],
                      ),

                       SizedBox(height: 8),

                      // Meta: lessons + XP
                      Row(
                        children: [
                           Icon(Icons.access_time,
                              color: AppColors.textMuted, size: 13),
                           SizedBox(width: 4),
                          Text(
                            '${chapter.lessonCount} Lessons',
                            style:  TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                           SizedBox(width: 16),
                           Icon(Icons.bolt,
                              color: AppColors.textMuted, size: 13),
                           SizedBox(width: 2),
                          Text(
                            '${chapter.xp} XP',
                            style:  TextStyle(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),

                       SizedBox(height: 12),

                      if (!isLocked) ...[
                        // Progress label
                        if (isActive && chapter.currentLesson != null)
                          Row(
                            mainAxisAlignment:
                                MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'CURRENT LESSON: ${chapter.currentLesson}',
                                style:  TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 9,
                                  letterSpacing: 1.2,
                                ),
                              ),
                              Text(
                                '${(chapter.progress * 100).toInt()}%',
                                style:  TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 9,
                                ),
                              ),
                            ],
                          ),

                         SizedBox(height: 6),

                        // Progress bar
                        ClipRRect(
                          borderRadius: BorderRadius.circular(3),
                          child: LinearProgressIndicator(
                            value: chapter.progress,
                            minHeight: 4,
                            backgroundColor: AppColors.borderDefault,
                            valueColor: AlwaysStoppedAnimation<Color>(
                                isCompleted ? AppColors.green : AppColors.purple),
                          ),
                        ),

                        if (isCompleted) ...[
                           SizedBox(height: 8),
                          Align(
                            alignment: Alignment.centerRight,
                            child: Text(
                              'COMPLETED',
                              style: TextStyle(
                                color: AppColors.green,
                                fontSize: 9,
                                letterSpacing: 1.5,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],

                        if (isActive) ...[
                           SizedBox(height: 12),
                          // Resume button
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton(
                              onPressed: onResume,
                              style: OutlinedButton.styleFrom(
                                foregroundColor: AppColors.purpleLight,
                                side:  BorderSide(
                                    color: AppColors.purpleDim),
                                backgroundColor:
                                    AppColors.purple.withOpacity(0.1),
                                padding:
                                     EdgeInsets.symmetric(vertical: 12),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(10)),
                              ),
                              child:  Text(
                                'RESUME LEARNING',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.5,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ] else ...[
                        // Locked hint
                        Row(
                          children: [
                             Icon(Icons.lock_clock_outlined,
                                color: AppColors.textMuted, size: 13),
                             SizedBox(width: 6),
                            Text(
                              'Complete Chapter ${chapter.number - 1} to unlock',
                              style:  TextStyle(
                                color: AppColors.textMuted,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      )
          .animate(delay: Duration(milliseconds: 100 * index))
          .fadeIn(duration: 400.ms)
          .slideY(begin: 0.12, duration: 400.ms, curve: Curves.easeOut),
    );
  }
}

class _StatusIcon extends StatelessWidget {
  final ChapterModel chapter;
   _StatusIcon({required this.chapter});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 42,
      height: 42,
      decoration: BoxDecoration(
        color: switch (chapter.status) {
          ChapterStatus.completed => AppColors.green.withOpacity(0.15),
          ChapterStatus.active    => AppColors.bgCardAlt,
          ChapterStatus.locked    => AppColors.bgCardAlt,
        },
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: switch (chapter.status) {
            ChapterStatus.completed => AppColors.green.withOpacity(0.4),
            ChapterStatus.active    => AppColors.borderDefault,
            ChapterStatus.locked    => AppColors.borderDefault,
          },
        ),
      ),
      child: Icon(
        switch (chapter.status) {
          ChapterStatus.completed => Icons.check_circle_outline,
          ChapterStatus.active    => Icons.science_outlined,
          ChapterStatus.locked    => Icons.lock_outline,
        },
        color: switch (chapter.status) {
          ChapterStatus.completed => AppColors.green,
          ChapterStatus.active    => AppColors.textSecondary,
          ChapterStatus.locked    => AppColors.textMuted,
        },
        size: 20,
      ),
    );
  }
}
