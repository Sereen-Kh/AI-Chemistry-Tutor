class UserModel {
  final String id;
  final String name;
  final String avatarUrl;
  final int level;
  final int xp;
  final int xpToNextLevel;
  final String? selectedMentorId;

  const UserModel({
    required this.id,
    required this.name,
    required this.avatarUrl,
    required this.level,
    required this.xp,
    required this.xpToNextLevel,
    this.selectedMentorId,
  });

  double get progressToNextLevel =>
      xpToNextLevel > 0 ? (xp / xpToNextLevel).clamp(0.0, 1.0) : 0.0;

  int get xpRemaining => (xpToNextLevel - xp).clamp(0, xpToNextLevel);

  factory UserModel.fromJson(Map<String, dynamic> j) => UserModel(
        id: j['id'] as String? ?? '',
        name: j['name'] as String? ?? 'Learner',
        avatarUrl: j['avatar_url'] as String? ?? '',
        level: j['level'] as int? ?? 1,
        xp: j['xp'] as int? ?? 0,
        xpToNextLevel: j['xp_to_next'] as int? ?? 1000,
        selectedMentorId: j['mentor_id'] as String?,
      );

  static UserModel get mock => const UserModel(
        id: '1',
        name: 'Aleen',
        avatarUrl: '',
        level: 14,
        xp: 760,
        xpToNextLevel: 1000,
        selectedMentorId: 'gamer',
      );
}
