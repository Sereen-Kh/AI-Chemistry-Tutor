import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../app/routes/app_routes.dart';
import '../../../data/models/mentor_model.dart';
import '../../../data/repositories/chemai_repository.dart';

class MentorController extends GetxController {
  final _repo = Get.find<ChemAIRepository>();

  final mentors = <MentorModel>[].obs;
  final selectedId = RxnString();
  final isLoading = false.obs;

  bool get isEditMode => (Get.arguments as Map?)?['editMode'] == true;

  @override
  void onInit() {
    super.onInit();
    _loadMentors();
    _loadSavedSelection();
  }

  Future<void> _loadMentors() async {
    mentors.value = MentorModel.defaults;

    final result = await _repo.fetchMentors();
    if (result.data != null && result.data!.isNotEmpty) {
      mentors.value = result.data!;
    }
  }

  Future<void> _loadSavedSelection() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString('mentor_id');
    if (saved != null) {
      selectedId.value = saved;
    }
  }

  void select(String id) => selectedId.value = id;

  bool isSelected(String id) => selectedId.value == id;

  Future<void> confirmSelection() async {
    if (selectedId.value == null) {
      Get.snackbar(
        'mentor_snackbar_title'.tr,
        'mentor_snackbar_body'.tr,
        snackPosition: SnackPosition.BOTTOM,
      );
      return;
    }

    isLoading.value = true;
    await _repo.selectMentor(selectedId.value!);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('mentor_id', selectedId.value!);
    isLoading.value = false;

    if (isEditMode) {
      Get.back(result: selectedId.value);
      Get.snackbar(
        'mentor_saved_title'.tr,
        'mentor_saved_body'.tr,
        snackPosition: SnackPosition.BOTTOM,
      );
    } else {
      Get.offAllNamed(AppRoutes.mainNav);
    }
  }

  /// First-time flow entry point (kept for clarity in the view).
  Future<void> initializeSession() => confirmSelection();
}

/// Resolves a stored mentor id to a display name.
String mentorNameForId(String? id) {
  if (id == null) return '';
  for (final m in MentorModel.defaults) {
    if (m.id == id) return m.name;
  }
  return '';
}
