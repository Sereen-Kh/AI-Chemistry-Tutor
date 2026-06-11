enum SessionStatus { completed, active, upcoming }

class ScheduleSession {
  final String time;
  final SessionStatus status;
  final String title;
  final String description;
  final String? extra;
  final bool isVerified;
  final bool hasAction;

  const ScheduleSession({
    required this.time,
    required this.status,
    required this.title,
    required this.description,
    this.extra,
    this.isVerified = false,
    this.hasAction = false,
  });

  static List<ScheduleSession> get defaults => const [
        ScheduleSession(
          time: '08:05',
          status: SessionStatus.completed,
          title: 'Morning Review',
          description: 'Atomic Orbitals & Electron Configuration basics.',
          isVerified: true,
        ),
        ScheduleSession(
          time: '14:58',
          status: SessionStatus.active,
          title: 'AI Tutoring Session',
          description:
              'Deep dive into Schrödinger Equation and Wave-Particle Duality with ChemAi-4.',
          hasAction: true,
        ),
        ScheduleSession(
          time: '17:00',
          status: SessionStatus.upcoming,
          title: 'Practice Quiz',
          description:
              'Module 4 assessment: Periodic Trends & Ionization Energy.',
          extra: '10 Questions',
        ),
      ];
}
