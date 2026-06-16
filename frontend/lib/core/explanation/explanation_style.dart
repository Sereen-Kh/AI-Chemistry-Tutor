import 'package:flutter/material.dart';
import 'package:get/get.dart';

/// User-facing ways lesson content can be explained.
class ExplanationStyleOption {
  final String id;
  final IconData icon;
  final String labelKey;

  const ExplanationStyleOption({
    required this.id,
    required this.icon,
    required this.labelKey,
  });
}

abstract final class ExplanationStyles {
  static const prefsKey = 'explanation_style';
  static const defaultId = 'text';

  static const options = <ExplanationStyleOption>[
    ExplanationStyleOption(
      id: 'text',
      icon: Icons.article_outlined,
      labelKey: 'explanation_style_text',
    ),
    ExplanationStyleOption(
      id: 'reel',
      icon: Icons.play_circle_outline,
      labelKey: 'explanation_style_reel',
    ),
    ExplanationStyleOption(
      id: 'voice',
      icon: Icons.mic_none_rounded,
      labelKey: 'explanation_style_voice',
    ),
    ExplanationStyleOption(
      id: 'visual',
      icon: Icons.visibility_outlined,
      labelKey: 'explanation_style_visual',
    ),
  ];

  static ExplanationStyleOption optionFor(String? id) {
    return options.firstWhere(
      (o) => o.id == id,
      orElse: () => options.first,
    );
  }

  static String labelFor(String? id) => optionFor(id).labelKey.tr;
}
