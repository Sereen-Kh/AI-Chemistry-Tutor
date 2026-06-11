import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/social_controller.dart';

class SocialView extends GetView<SocialController> {
  const SocialView({super.key});

  static const _filters = ['ALL', 'FRIENDS', 'GLOBAL'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: AppBar(
        backgroundColor: AppColors.bgBase,
        titleSpacing: 16,
        title: Text(
          'SOCIAL SHOWCASE',
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w800,
            letterSpacing: 2,
          ),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.notifications_outlined,
                color: AppColors.textSecondary, size: 20),
            onPressed: () {},
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: AppColors.purple,
        child: const Icon(Icons.add, color: Colors.white),
        tooltip: 'POST ACHIEVEMENT',
      ),
      body: Column(
        children: [
          // Filter chips
          _FilterRow(filters: _filters, controller: controller),

          // Feed
          Expanded(
            child: Obx(() {
              final posts = controller.posts;
              return ListView.builder(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 80),
                itemCount: posts.length,
                itemBuilder: (_, i) {
                  final post = posts[i];
                  // First post is the featured one
                  if (i == 0) {
                    return _FeaturedPost(post: post);
                  }
                  return _FeedPost(post: post);
                },
              );
            }),
          ),
        ],
      ),
    );
  }
}

// ── Filter row ────────────────────────────────────────────────────────────────

class _FilterRow extends StatelessWidget {
  final List<String> filters;
  final SocialController controller;
  const _FilterRow({required this.filters, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() => Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: ListView(
            scrollDirection: Axis.horizontal,
            children: filters.map((f) {
              final active = controller.filter.value == f;
              return GestureDetector(
                onTap: () => controller.setFilter(f),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.only(right: 8, top: 6, bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color:
                        active ? AppColors.purple : AppColors.bgCard,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: active
                          ? AppColors.purple
                          : AppColors.borderDefault,
                    ),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    f,
                    style: TextStyle(
                      color: active
                          ? Colors.white
                          : AppColors.textSecondary,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ));
  }
}

// ── Featured post ─────────────────────────────────────────────────────────────

class _FeaturedPost extends StatelessWidget {
  final SocialPost post;
  const _FeaturedPost({required this.post});

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<SocialController>();
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.purpleDim,
            AppColors.bgCard,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.purple.withOpacity(0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.amber.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                      color: AppColors.amber.withOpacity(0.4)),
                ),
                child: Text(
                  'FEATURED',
                  style: TextStyle(
                    color: AppColors.amber,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                post.time,
                style:
                    TextStyle(color: AppColors.textMuted, fontSize: 11),
              ),
            ],
          ),
          const SizedBox(height: 14),
          // Achievement
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(post.userEmoji,
                  style: const TextStyle(fontSize: 36)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    RichText(
                      text: TextSpan(children: [
                        TextSpan(
                          text: '${post.badgeEmoji} ${post.userName} ',
                          style: TextStyle(
                            color: AppColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        TextSpan(
                          text: post.achievementText,
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 14,
                            height: 1.4,
                          ),
                        ),
                      ]),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          // Action buttons
          Row(
            children: [
              _ActionBtn(
                icon: Icons.favorite_outline,
                label: '${post.likes}',
                color: AppColors.danger,
                onTap: () => ctrl.likePost(post.id),
              ),
              const SizedBox(width: 12),
              _ActionBtn(
                icon: Icons.chat_bubble_outline,
                label: '${post.comments}',
                color: AppColors.cyan,
                onTap: () {},
              ),
              const SizedBox(width: 12),
              _ActionBtn(
                icon: Icons.share_outlined,
                label: 'SHARE',
                color: AppColors.textSecondary,
                onTap: () {},
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Feed post ─────────────────────────────────────────────────────────────────

class _FeedPost extends StatelessWidget {
  final SocialPost post;
  const _FeedPost({required this.post});

  @override
  Widget build(BuildContext context) {
    final ctrl = Get.find<SocialController>();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderDefault),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Avatar
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.bgCardAlt,
              border: Border.all(color: AppColors.borderDefault),
            ),
            alignment: Alignment.center,
            child: Text(post.userEmoji,
                style: const TextStyle(fontSize: 20)),
          ),
          const SizedBox(width: 12),
          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      post.userName,
                      style: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(post.badgeEmoji,
                        style: const TextStyle(fontSize: 13)),
                    const Spacer(),
                    Text(
                      post.time,
                      style: TextStyle(
                          color: AppColors.textMuted, fontSize: 10),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  post.achievementText,
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _ActionBtn(
                      icon: Icons.favorite_outline,
                      label: '${post.likes}',
                      color: AppColors.danger,
                      onTap: () => ctrl.likePost(post.id),
                    ),
                    const SizedBox(width: 12),
                    _ActionBtn(
                      icon: Icons.chat_bubble_outline,
                      label: '${post.comments}',
                      color: AppColors.cyan,
                      onTap: () {},
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Action button ─────────────────────────────────────────────────────────────

class _ActionBtn extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  const _ActionBtn({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 16),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
