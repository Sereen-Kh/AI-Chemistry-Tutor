import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

import '../../../../app/theme/app_colors.dart';
import '../../../../data/models/mentor_model.dart';

class MentorCard extends StatelessWidget {
  final MentorModel mentor;
  final bool isSelected;
  final VoidCallback onTap;
  final int index;

  const MentorCard({
    super.key,
    required this.mentor,
    required this.isSelected,
    required this.onTap,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.purple.withOpacity(0.15)
              : AppColors.bgCard,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? AppColors.borderSelected : AppColors.borderDefault,
            width: isSelected ? 1.5 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: AppColors.purple.withOpacity(0.25),
                    blurRadius: 12,
                    spreadRadius: 0,
                  )
                ]
              : null,
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Icon
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.purple.withOpacity(0.25)
                        : AppColors.bgCardAlt,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Center(
                    child: Text(
                      mentor.iconAsset,
                      style: const TextStyle(fontSize: 16),
                    ),
                  ),
                ),
                const Spacer(),
                // Checkmark
                if (isSelected)
                  Container(
                    width: 20,
                    height: 20,
                    decoration:  BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.borderSelected,
                    ),
                    child: const Icon(Icons.check,
                        color: Colors.white, size: 12),
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              mentor.name,
              style: TextStyle(
                color: isSelected
                    ? AppColors.textPrimary
                    : AppColors.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              mentor.description,
              style:  TextStyle(
                color: AppColors.textSecondary,
                fontSize: 11,
                height: 1.4,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      )
          .animate(delay: Duration(milliseconds: 80 * index))
          .fadeIn(duration: 400.ms)
          .slideY(begin: 0.15, duration: 400.ms, curve: Curves.easeOut),
    );
  }
}
