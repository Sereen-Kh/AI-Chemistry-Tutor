import 'package:get/get.dart';

class StudyItem {
  final String id;
  final String time;
  final String title;
  final int durationMin;
  final RxBool isCompleted;

  StudyItem({
    required this.id,
    required this.time,
    required this.title,
    required this.durationMin,
    bool completed = false,
  }) : isCompleted = completed.obs;
}

class StudyPlanController extends GetxController {
  final userName = 'Alex'.obs;
  final weeklyProgress = 4.obs;
  final weeklyGoal = 7.obs;
  final todayItems = <StudyItem>[].obs;

  final weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  // true = completed, false = scheduled
  final weekStatus = [true, true, true, true, false, false, false];

  final suggestedResources = [
    {'title': 'Covalent Bonds Explained', 'type': 'Lesson', 'duration': '12 min'},
    {'title': 'Periodic Table Deep Dive', 'type': 'Interactive', 'duration': '8 min'},
  ];

  @override
  void onInit() {
    super.onInit();
    todayItems.addAll([
      StudyItem(
        id: '1',
        time: '09:00',
        title: 'Covalent Bonds Review',
        durationMin: 30,
        completed: true,
      ),
      StudyItem(
        id: '2',
        time: '11:00',
        title: 'Practice Quiz: Periodic Table',
        durationMin: 20,
        completed: false,
      ),
      StudyItem(
        id: '3',
        time: '14:00',
        title: 'Flashcard Session',
        durationMin: 15,
        completed: false,
      ),
    ]);
  }

  void toggleItem(String id) {
    final item = todayItems.firstWhereOrNull((e) => e.id == id);
    if (item != null) {
      item.isCompleted.value = !item.isCompleted.value;
    }
  }

  void regeneratePlan() {}
}
