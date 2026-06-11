import 'package:get/get.dart';

class CollabTask {
  final String id;
  final String title;
  final String assignee;
  final bool isCompleted;

  const CollabTask({
    required this.id,
    required this.title,
    required this.assignee,
    this.isCompleted = false,
  });

  CollabTask copyWith({bool? isCompleted}) => CollabTask(
        id: id,
        title: title,
        assignee: assignee,
        isCompleted: isCompleted ?? this.isCompleted,
      );
}

class TeamMember {
  final String emoji;
  final String name;
  final double contribution;
  final bool isOnline;

  const TeamMember({
    required this.emoji,
    required this.name,
    required this.contribution,
    this.isOnline = false,
  });
}

class CollaborationController extends GetxController {
  final tasks = <CollabTask>[].obs;
  final members = <TeamMember>[].obs;
  final progress = 0.65.obs;
  final hasSubmitted = false.obs;

  @override
  void onInit() {
    super.onInit();
    tasks.addAll(const [
      CollabTask(id: '1', title: 'Analyze reaction pathways', assignee: 'NovaStar99', isCompleted: true),
      CollabTask(id: '2', title: 'Document synthesis steps', assignee: 'QuantumKid', isCompleted: true),
      CollabTask(id: '3', title: 'Run simulation models', assignee: 'ChemWizard', isCompleted: false),
      CollabTask(id: '4', title: 'Submit final report', assignee: 'You', isCompleted: false),
    ]);
    members.addAll(const [
      TeamMember(emoji: '🌟', name: 'NovaStar99', contribution: 0.35, isOnline: true),
      TeamMember(emoji: '⚛️', name: 'QuantumKid', contribution: 0.30, isOnline: true),
      TeamMember(emoji: '🧙', name: 'ChemWizard', contribution: 0.20, isOnline: false),
      TeamMember(emoji: '🎯', name: 'You',        contribution: 0.15, isOnline: true),
    ]);
  }

  void toggleTask(String id) {
    final idx = tasks.indexWhere((t) => t.id == id);
    if (idx == -1) return;
    tasks[idx] = tasks[idx].copyWith(isCompleted: !tasks[idx].isCompleted);
    // Update progress
    final done = tasks.where((t) => t.isCompleted).length;
    progress.value = done / tasks.length;
  }

  void submit() {
    if (hasSubmitted.value) return;
    hasSubmitted.value = true;
    Get.snackbar(
      'Contribution Submitted!',
      'Your work has been added to the team project.',
      snackPosition: SnackPosition.BOTTOM,
    );
  }
}
