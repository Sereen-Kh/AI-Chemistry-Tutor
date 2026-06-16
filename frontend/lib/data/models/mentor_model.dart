class MentorModel {
  final String id;
  final String name;
  final String description;
  final String iconAsset; // or emoji / icon code

  const MentorModel({
    required this.id,
    required this.name,
    required this.description,
    required this.iconAsset,
  });

  factory MentorModel.fromJson(Map<String, dynamic> j) => MentorModel(
        id: j['id'] as String,
        name: j['name'] as String,
        description: j['description'] as String,
        iconAsset: j['icon'] as String? ?? '',
      );

  // Local seed data matching the Figma design
  static List<MentorModel> get defaults => const [
        MentorModel(
          id: 'professor',
          name: 'The Professor',
          description:
              'Rigorous, detailed, and evidence-based approach to complex structures.',
          iconAsset: '🎓',
        ),
        MentorModel(
          id: 'gamer',
          name: 'The Gamer',
          description:
              'High energy, quest-based learning with real-time XP and achievements.',
          iconAsset: '🎮',
        ),
        MentorModel(
          id: 'visionary',
          name: 'The Visionary',
          description:
              'Concept-focused with sci-fi analogies and future-tech implications.',
          iconAsset: '🚀',
        ),
        MentorModel(
          id: 'minimalist',
          name: 'The Minimalist',
          description:
              'Straight to the point. No fluff, just pure chemical fundamentals.',
          iconAsset: '⚡',
        ),
        MentorModel(
          id: 'storyteller',
          name: 'The Storyteller',
          description:
              'Narrative-driven lessons connecting atoms to human history.',
          iconAsset: '📖',
        ),
        MentorModel(
          id: 'lab_partner',
          name: 'The Lab Partner',
          description:
              "Collaborative, casual environment. We're learning this together.",
          iconAsset: '⚗️',
        ),
      ];
}
