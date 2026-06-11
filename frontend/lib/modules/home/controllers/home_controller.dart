import 'package:get/get.dart';

import '../../../data/models/user_model.dart';
import '../../../data/repositories/chemai_repository.dart';

class HomeController extends GetxController {
  final _repo = Get.find<ChemAIRepository>();

  final user = Rxn<UserModel>();
  final isLoading = true.obs;

  @override
  void onReady() {
    super.onReady();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    // Show mock data immediately for fluid UX
    user.value = UserModel.mock;
    isLoading.value = false;

    // Then try live data
    final result = await _repo.fetchProfile();
    if (result.data != null) user.value = result.data;
  }

  void refresh() => _loadProfile();
}
