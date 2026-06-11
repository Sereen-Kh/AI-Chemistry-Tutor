import 'package:get/get.dart';

class ResearchEntry {
  final String label;
  final String value;
  final String unit;
  final String timestamp;

  const ResearchEntry({
    required this.label,
    required this.value,
    required this.unit,
    required this.timestamp,
  });
}

class ResearchLabController extends GetxController {
  final experimentId = '0042'.obs;
  final experimentName = 'Acid-Base Titration'.obs;
  final status = 'IN PROGRESS'.obs;

  final ph = 7.2.obs;
  final volume = 24.5.obs;
  final temperature = 25.0.obs;
  final concentration = 0.1.obs;

  final dataPoints = <ResearchEntry>[].obs;

  final collaborators = [
    {'name': 'Alex', 'initials': 'AX', 'color': 0xFF8B7DF8},
    {'name': 'Maya', 'initials': 'MY', 'color': 0xFF22D3EE},
    {'name': 'Ryo', 'initials': 'RY', 'color': 0xFF34D399},
  ];

  final recentActivity = [
    ActivityEntry(
      action: 'pH reading recorded: 7.2',
      timestamp: '2 min ago',
    ),
    ActivityEntry(
      action: 'Volume adjusted to 24.5 mL',
      timestamp: '8 min ago',
    ),
    ActivityEntry(
      action: 'Experiment #0042 started',
      timestamp: '15 min ago',
    ),
  ];

  @override
  void onInit() {
    super.onInit();
    dataPoints.addAll([
      const ResearchEntry(
          label: 'pH', value: '7.2', unit: '', timestamp: '14:02'),
      const ResearchEntry(
          label: 'Volume', value: '24.5', unit: 'mL', timestamp: '14:05'),
      const ResearchEntry(
          label: 'Temp', value: '25.0', unit: '°C', timestamp: '14:08'),
    ]);
  }

  void addDataPoint() {
    final now = DateTime.now();
    final ts =
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    dataPoints.add(
      ResearchEntry(
        label: 'pH',
        value: ph.value.toStringAsFixed(1),
        unit: '',
        timestamp: ts,
      ),
    );
  }

  void generateReport() {}
}

class ActivityEntry {
  final String action;
  final String timestamp;
  const ActivityEntry({required this.action, required this.timestamp});
}
