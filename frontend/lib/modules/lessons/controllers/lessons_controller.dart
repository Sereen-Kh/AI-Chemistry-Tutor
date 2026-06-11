import 'package:get/get.dart';

import '../../../app/routes/app_routes.dart';
import '../../../data/models/chapter_model.dart';
import '../../../data/repositories/chemai_repository.dart';

class LessonsController extends GetxController {
  final _repo = Get.find<ChemAIRepository>();

  final chapters = <ChapterModel>[].obs;
  final isLoading = true.obs;

  @override
  void onReady() {
    super.onReady();
    _load();
  }

  Future<void> _load() async {
    // Seed with local data immediately
    chapters.value = ChapterModel.defaults;
    isLoading.value = false;

    // Try live data
    final result = await _repo.fetchChapters();
    if (result.data != null && result.data!.isNotEmpty) {
      chapters.value = result.data!;
    }
  }

  void resumeChapter(ChapterModel chapter) {
    Get.toNamed(AppRoutes.lessonDetail);
  }
}
