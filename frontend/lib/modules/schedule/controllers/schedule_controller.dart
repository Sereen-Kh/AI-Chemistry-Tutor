import 'package:get/get.dart';

import '../../../data/models/schedule_model.dart';

class ScheduleController extends GetxController {
  final sessions = ScheduleSession.defaults;

  final completed = 12;
  final upcoming = 4;
  final missed = 81;

  final efficiency = 0.78;
  final efficiencyLabel = 'Optimal';

  final examDate = 'May 15, 2024';
  final daysToExam = 8.obs;
  final weeklyProgress = 0.65;
  final todayLessons = ['Naming Organic Compounds', 'Oxidation and Reduction'];
}
