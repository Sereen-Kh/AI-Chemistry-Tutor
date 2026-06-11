enum ChapterStatus { completed, active, locked }

class ChapterModel {
  final int number;
  final String title;
  final int lessonCount;
  final int xp;
  final double progress;   // 0.0–1.0
  final ChapterStatus status;
  final String? currentLesson;
  final String iconAsset;

  const ChapterModel({
    required this.number,
    required this.title,
    required this.lessonCount,
    required this.xp,
    required this.progress,
    required this.status,
    this.currentLesson,
    this.iconAsset = '',
  });

  factory ChapterModel.fromJson(Map<String, dynamic> j) => ChapterModel(
        number: j['number'] as int? ?? 0,
        title: j['title'] as String? ?? '',
        lessonCount: j['lesson_count'] as int? ?? 0,
        xp: j['xp'] as int? ?? 0,
        progress: (j['progress'] as num?)?.toDouble() ?? 0.0,
        status: _parseStatus(j['status'] as String?),
        currentLesson: j['current_lesson'] as String?,
        iconAsset: j['icon'] as String? ?? '',
      );

  static ChapterStatus _parseStatus(String? s) => switch (s) {
        'completed' => ChapterStatus.completed,
        'active'    => ChapterStatus.active,
        _           => ChapterStatus.locked,
      };

  // Seed data matching Figma
  static List<ChapterModel> get defaults => const [
        ChapterModel(
          number: 1,
          title: 'Atomic Structure',
          lessonCount: 12,
          xp: 450,
          progress: 1.0,
          status: ChapterStatus.completed,
          iconAsset: '✓',
        ),
        ChapterModel(
          number: 2,
          title: 'Chemical Bonds',
          lessonCount: 8,
          xp: 600,
          progress: 0.65,
          status: ChapterStatus.active,
          currentLesson: 'COVALENT SHARING',
          iconAsset: '⚗️',
        ),
        ChapterModel(
          number: 3,
          title: 'Acids & Bases',
          lessonCount: 15,
          xp: 800,
          progress: 0.0,
          status: ChapterStatus.locked,
          iconAsset: '🔒',
        ),
      ];
}
