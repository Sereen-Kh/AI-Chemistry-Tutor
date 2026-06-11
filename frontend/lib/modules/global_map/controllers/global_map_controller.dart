import 'package:get/get.dart';

class MissionPin {
  final String id;
  final String name;
  final String region;
  final int xp;
  final String status; // ACTIVE | CLAIMED
  final double lat;   // 0.0–1.0 relative
  final double lng;   // 0.0–1.0 relative

  const MissionPin({
    required this.id,
    required this.name,
    required this.region,
    required this.xp,
    required this.status,
    required this.lat,
    required this.lng,
  });

  MissionPin copyWith({String? status}) => MissionPin(
        id: id,
        name: name,
        region: region,
        xp: xp,
        status: status ?? this.status,
        lat: lat,
        lng: lng,
      );
}

class GlobalMapController extends GetxController {
  final missions = <MissionPin>[].obs;

  List<MissionPin> get activeMissions =>
      missions.where((m) => m.status == 'ACTIVE').toList();

  @override
  void onInit() {
    super.onInit();
    missions.addAll(const [
      MissionPin(id: '1', name: 'Reaction Race',  region: 'Asia',     xp: 500, status: 'ACTIVE',  lat: 0.30, lng: 0.72),
      MissionPin(id: '2', name: 'Mole Marathon',  region: 'Europe',   xp: 350, status: 'ACTIVE',  lat: 0.22, lng: 0.50),
      MissionPin(id: '3', name: 'Bond Breaker',   region: 'Americas', xp: 450, status: 'ACTIVE',  lat: 0.40, lng: 0.20),
      MissionPin(id: '4', name: 'Element Hunt',   region: 'Africa',   xp: 300, status: 'ACTIVE',  lat: 0.48, lng: 0.52),
    ]);
  }

  void joinMission(String id) {
    final idx = missions.indexWhere((m) => m.id == id);
    if (idx == -1) return;
    missions[idx] = missions[idx].copyWith(status: 'CLAIMED');
  }
}
