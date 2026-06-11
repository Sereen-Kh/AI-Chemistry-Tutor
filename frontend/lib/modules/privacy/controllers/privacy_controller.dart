import 'package:get/get.dart';

class PrivacyController extends GetxController {
  final shareProgress = true.obs;
  final showInLeaderboard = true.obs;
  final allowSquadInvites = true.obs;
  final shareAchievements = false.obs;
  final analyticsEnabled = true.obs;
  final crashReportsEnabled = true.obs;

  void toggle(RxBool value) => value.value = !value.value;

  void deleteAccount() {
    Get.defaultDialog(
      title: 'Delete Account',
      middleText: 'This action is irreversible. All your data will be permanently deleted.',
      textConfirm: 'DELETE',
      textCancel: 'CANCEL',
      onConfirm: () {
        Get.back();
        Get.snackbar('Account', 'Account deletion request submitted.',
            snackPosition: SnackPosition.BOTTOM);
      },
    );
  }
}
