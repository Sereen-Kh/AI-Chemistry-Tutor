import 'package:get/get.dart';

class PlanFeature {
  final String emoji;
  final String title;
  final bool included;
  const PlanFeature({required this.emoji, required this.title, required this.included});
}

class PlanTier {
  final String name;
  final String price;
  final String period;
  final List<PlanFeature> features;
  final bool isCurrent;
  const PlanTier({
    required this.name,
    required this.price,
    required this.period,
    required this.features,
    required this.isCurrent,
  });
}

class PlanController extends GetxController {
  final selectedTier = 'pro'.obs;

  final tiers = [
    const PlanTier(
      name: 'Free',
      price: '\$0',
      period: 'forever',
      features: [
        PlanFeature(emoji: '✓', title: '5 lessons/day', included: true),
        PlanFeature(emoji: '✓', title: 'Basic flashcards', included: true),
        PlanFeature(emoji: '✓', title: 'Daily quiz', included: true),
        PlanFeature(emoji: '✗', title: 'AI chat unlimited', included: false),
        PlanFeature(emoji: '✗', title: 'Virtual Lab', included: false),
        PlanFeature(emoji: '✗', title: 'Boss Battles', included: false),
      ],
      isCurrent: false,
    ),
    const PlanTier(
      name: 'Pro',
      price: '\$9.99',
      period: '/month',
      features: [
        PlanFeature(emoji: '✓', title: 'Unlimited lessons', included: true),
        PlanFeature(emoji: '✓', title: 'All flashcard packs', included: true),
        PlanFeature(emoji: '✓', title: 'Unlimited quizzes', included: true),
        PlanFeature(emoji: '✓', title: 'AI chat unlimited', included: true),
        PlanFeature(emoji: '✓', title: 'Virtual Lab access', included: true),
        PlanFeature(emoji: '✗', title: 'Boss Battles', included: false),
      ],
      isCurrent: true,
    ),
    const PlanTier(
      name: 'Elite',
      price: '\$19.99',
      period: '/month',
      features: [
        PlanFeature(emoji: '✓', title: 'Everything in Pro', included: true),
        PlanFeature(emoji: '✓', title: 'Boss Battles & Games', included: true),
        PlanFeature(emoji: '✓', title: 'Research Lab', included: true),
        PlanFeature(emoji: '✓', title: 'Squad features', included: true),
        PlanFeature(emoji: '✓', title: 'Priority AI model', included: true),
        PlanFeature(emoji: '✓', title: '2x XP multiplier', included: true),
      ],
      isCurrent: false,
    ),
  ];

  void selectTier(String tier) => selectedTier.value = tier;

  void subscribe() {
    Get.snackbar('Upgrade', 'Upgrade flow coming soon!',
        snackPosition: SnackPosition.BOTTOM);
  }
}
