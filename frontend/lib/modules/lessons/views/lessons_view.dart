import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:get/get.dart';

import '../../../app/theme/app_colors.dart';
import '../controllers/lessons_controller.dart';
import 'widgets/chapter_card.dart';
import '../../home/controllers/home_controller.dart';
import '../../main_nav/controllers/main_nav_controller.dart';
class LessonsView extends GetView<LessonsController> {
  const LessonsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBase,
      appBar: _buildAppBar(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
             Text(
              'lessons_master'.tr,
              style: TextStyle(
                color: AppColors.textPrimary,
                fontSize: 26,
                fontWeight: FontWeight.w800,
              ),
            ).animate().fadeIn(duration: 400.ms),

             SizedBox(height: 6),

             Text(
              'lessons_subtitle'.tr,
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 13,
                height: 1.5,
              ),
            ).animate().fadeIn(delay: 100.ms, duration: 400.ms),

             SizedBox(height: 24),

            // Chapter list
            Obx(() => ListView.separated(
                  shrinkWrap: true,
                  physics:  NeverScrollableScrollPhysics(),
                  itemCount: controller.chapters.length,
                  separatorBuilder: (_, __) =>  SizedBox(height: 14),
                  itemBuilder: (_, i) {
                    final c = controller.chapters[i];
                    return ChapterCard(
                      chapter: c,
                      index: i,
                      onResume: () => controller.resumeChapter(c),
                    );
                  },
                )),

             SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    final avatarUrl =
        '';
    return AppBar(
      // backgroundColor: const Color(0xFF020408),
      elevation: 0,
      leading: Padding(
        padding: const EdgeInsets.all(6),
        child: GestureDetector(
          onTap: () => Get.find<MainNavController>().openDrawer(),
          child: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppColors.bgCard,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppColors.borderDefault),
            ),
            child: Icon(Icons.menu_rounded, color: AppColors.textSecondary, size: 18),
          ),
        ),
      ),
      title: ShaderMask(
        shaderCallback: (bounds) => AppColors.gradientPurple.createShader(bounds),
        child: Text(
          'app_name'.tr,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      centerTitle: true,
      actions: [
        Padding(
          padding: const EdgeInsets.all(6),
          child:

     Container(
    width: 36,
    height: 36,
    decoration: BoxDecoration(
    shape: BoxShape.circle,
    color: AppColors.bgCard,
    border: Border.all(color: AppColors.borderDefault),
    image: avatarUrl.isNotEmpty
    ? DecorationImage(image: NetworkImage(avatarUrl), fit: BoxFit.cover)
        : null,
    ),
    child: avatarUrl.isEmpty
    ? Icon(Icons.account_circle_outlined, color: AppColors.purple, size: 22)
        : null,
    )
    ,
        ),
      ],
    );
  }
}
