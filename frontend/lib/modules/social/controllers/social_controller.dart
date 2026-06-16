import 'package:get/get.dart';

class SocialPost {
  final String id;
  final String userEmoji;
  final String userName;
  final String achievementText;
  final String badgeEmoji;
  final String time;
  final int likes;
  final int comments;

  const SocialPost({
    required this.id,
    required this.userEmoji,
    required this.userName,
    required this.achievementText,
    required this.badgeEmoji,
    required this.time,
    required this.likes,
    required this.comments,
  });

  SocialPost copyWith({int? likes}) => SocialPost(
        id: id,
        userEmoji: userEmoji,
        userName: userName,
        achievementText: achievementText,
        badgeEmoji: badgeEmoji,
        time: time,
        likes: likes ?? this.likes,
        comments: comments,
      );
}

class SocialController extends GetxController {
  final posts = <SocialPost>[].obs;
  final filter = 'ALL'.obs;

  @override
  void onInit() {
    super.onInit();
    posts.addAll(const [
      SocialPost(
        id: '1',
        userEmoji: '🚀',
        userName: 'Alex',
        achievementText: 'just reached QUANTUM VOYAGER rank!',
        badgeEmoji: '🏆',
        time: '2m ago',
        likes: 48,
        comments: 7,
      ),
      SocialPost(
        id: '2',
        userEmoji: '⚛️',
        userName: 'QuantumKid',
        achievementText: 'completed the Hardcore Quantum Gauntlet challenge!',
        badgeEmoji: '⚡',
        time: '18m ago',
        likes: 31,
        comments: 4,
      ),
      SocialPost(
        id: '3',
        userEmoji: '🧙',
        userName: 'ChemWizard',
        achievementText: 'reached Level 44 — almost at the top!',
        badgeEmoji: '🌟',
        time: '1h ago',
        likes: 22,
        comments: 2,
      ),
      SocialPost(
        id: '4',
        userEmoji: '🔬',
        userName: 'MoleMaster',
        achievementText: 'scored 100% on the Stoichiometry Master quiz!',
        badgeEmoji: '💯',
        time: '3h ago',
        likes: 15,
        comments: 5,
      ),
    ]);
  }

  void likePost(String id) {
    final idx = posts.indexWhere((p) => p.id == id);
    if (idx == -1) return;
    posts[idx] = posts[idx].copyWith(likes: posts[idx].likes + 1);
  }

  void setFilter(String f) => filter.value = f;
}
