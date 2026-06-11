import 'package:flutter/material.dart';

import '../../../../app/theme/app_colors.dart';

class MissionCard extends StatelessWidget {
  const MissionCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 170,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.borderDefault),
        color: AppColors.bgCard,
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          // Background teal gradient overlay
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Color(0xFF0E3040),
                    Color(0xFF0A1828),
                  ],
                ),
              ),
            ),
          ),

          // Faint chemistry board text watermark
          Positioned(
            top: 12,
            right: 0,
            left: 0,
            child: Text(
              'CHEMISTRY FR---ΔG°',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withOpacity(0.06),
                fontSize: 20,
                fontWeight: FontWeight.w800,
                letterSpacing: 3,
              ),
            ),
          ),

          // Content
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Badge
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.cyan.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                        color: AppColors.cyan.withOpacity(0.35), width: 1),
                  ),
                  child:  Text(
                    'ACTIVE PROTOCOL',
                    style: TextStyle(
                      color: AppColors.cyan,
                      fontSize: 9,
                      letterSpacing: 1.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),

                const SizedBox(height: 10),

                 Text(
                  'Current Mission: The Periodic Table',
                  style: TextStyle(
                    color: AppColors.textPrimary,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),

                const SizedBox(height: 4),

                 Text(
                  'Mastering Transition Metals & Electron Configurations',
                  style: TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 12,
                  ),
                ),

                const Spacer(),

                // Resume button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.play_arrow, size: 16),
                    label: const Text('Resume Lesson'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.purple,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)),
                      textStyle: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
