import 'package:flutter/material.dart';

enum ChemTheme { tutor, luna, milo }

// ──────────────────────────────────────────────────────────────────────────────
// AppColors — all properties are static getters backed by `isDark` + `theme`.
// ──────────────────────────────────────────────────────────────────────────────
abstract final class AppColors {
  static bool isDark = true;
  static ChemTheme theme = ChemTheme.tutor;

  // ── Semantic constants (theme-invariant) ───────────────────────────────────
  static const amber   = Color(0xFFFBBF24);
  static const danger  = Color(0xFFEF4444);
  static const warning = Color(0xFFFBBF24);

  // ── Backgrounds ────────────────────────────────────────────────────────────
  static Color get bgDeep => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF1A0A14) : const Color(0xFFFFE8F0),
        ChemTheme.milo  => isDark ? const Color(0xFF050F0A) : const Color(0xFFD5F0E0),
        ChemTheme.tutor => isDark ? const Color(0xFF070A1C) : const Color(0xFFDDE1FF),
      };

  static Color get bgBase => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF220D1A) : const Color(0xFFFFF0F5),
        ChemTheme.milo  => isDark ? const Color(0xFF081A0F) : const Color(0xFFE8F8EE),
        ChemTheme.tutor => isDark ? const Color(0xFF0C0F2A) : const Color(0xFFECEDFF),
      };

  static Color get bgCard => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF2D1022) : const Color(0xFFFFFFFF),
        ChemTheme.milo  => isDark ? const Color(0xFF0D2416) : const Color(0xFFFFFFFF),
        ChemTheme.tutor => isDark ? const Color(0xFF121638) : const Color(0xFFFFFFFF),
      };

  static Color get bgCardAlt => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF3A1530) : const Color(0xFFFFF5F8),
        ChemTheme.milo  => isDark ? const Color(0xFF132E1E) : const Color(0xFFF0FAF4),
        ChemTheme.tutor => isDark ? const Color(0xFF181D48) : const Color(0xFFF4F5FF),
      };

  // ── Brand accents ──────────────────────────────────────────────────────────
  static Color get purple => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFFF6B9D) : const Color(0xFFE91E6E),
        ChemTheme.milo  => isDark ? const Color(0xFF34D399) : const Color(0xFF059669),
        ChemTheme.tutor => isDark ? const Color(0xFF8B7DF8) : const Color(0xFF6366F1),
      };

  static Color get purpleLight => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFFFB0CC) : const Color(0xFFFF8BC0),
        ChemTheme.milo  => isDark ? const Color(0xFF6EE7B7) : const Color(0xFF34D399),
        ChemTheme.tutor => isDark ? const Color(0xFFB5A8FF) : const Color(0xFF818CF8),
      };

  static Color get purpleDim => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF5C1033) : const Color(0xFFFFE0EC),
        ChemTheme.milo  => isDark ? const Color(0xFF064E35) : const Color(0xFFD1FAE5),
        ChemTheme.tutor => isDark ? const Color(0xFF3D3280) : const Color(0xFFE0E7FF),
      };

  static Color get cyan => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFFF9EC5) : const Color(0xFFFF6BA3),
        ChemTheme.milo  => isDark ? const Color(0xFF22D3EE) : const Color(0xFF0891B2),
        ChemTheme.tutor => isDark ? const Color(0xFF22D3EE) : const Color(0xFF0891B2),
      };

  static Color get cyanDim => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF7A1445) : const Color(0xFFFFD6E8),
        ChemTheme.milo  => isDark ? const Color(0xFF0891B2) : const Color(0xFFBAE6FD),
        ChemTheme.tutor => isDark ? const Color(0xFF0891B2) : const Color(0xFFBAE6FD),
      };

  static Color get green => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFFF6B9D) : const Color(0xFFE91E6E),
        ChemTheme.milo  => isDark ? const Color(0xFF34D399) : const Color(0xFF10B981),
        ChemTheme.tutor => isDark ? const Color(0xFF34D399) : const Color(0xFF10B981),
      };

  static Color get greenDim => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF5C1033) : const Color(0xFFFFE0EC),
        ChemTheme.milo  => isDark ? const Color(0xFF065F46) : const Color(0xFFD1FAE5),
        ChemTheme.tutor => isDark ? const Color(0xFF065F46) : const Color(0xFFD1FAE5),
      };

  // ── Text ──────────────────────────────────────────────────────────────────
  static Color get textPrimary => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFFFE8F3) : const Color(0xFF2D0B1F),
        ChemTheme.milo  => isDark ? const Color(0xFFE8F8F0) : const Color(0xFF052E16),
        ChemTheme.tutor => isDark ? const Color(0xFFF0F2FF) : const Color(0xFF0D1035),
      };

  static Color get textSecondary => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFFC17A9E) : const Color(0xFF7B3D58),
        ChemTheme.milo  => isDark ? const Color(0xFF6BA88B) : const Color(0xFF374B3E),
        ChemTheme.tutor => isDark ? const Color(0xFF8B92B8) : const Color(0xFF475569),
      };

  static Color get textMuted => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF6B3052) : const Color(0xFFC4849B),
        ChemTheme.milo  => isDark ? const Color(0xFF2E6047) : const Color(0xFF6BA88B),
        ChemTheme.tutor => isDark ? const Color(0xFF464D7A) : const Color(0xFF94A3B8),
      };

  static Color get textCyan => cyan;

  // ── Borders ───────────────────────────────────────────────────────────────
  static Color get borderDefault => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF4A1535) : const Color(0xFFF5BCCF),
        ChemTheme.milo  => isDark ? const Color(0xFF0F3A22) : const Color(0xFFA7F3D0),
        ChemTheme.tutor => isDark ? const Color(0xFF1E2458) : const Color(0xFFC7CCEF),
      };

  static Color get borderSelected => switch (theme) {
        ChemTheme.luna  => const Color(0xFFE91E6E),
        ChemTheme.milo  => const Color(0xFF10B981),
        ChemTheme.tutor => const Color(0xFF6366F1),
      };

  static Color get borderGlow => cyan;

  // ── Status ────────────────────────────────────────────────────────────────
  static Color get online => green;
  static Color get locked => switch (theme) {
        ChemTheme.luna  => isDark ? const Color(0xFF6B3052) : const Color(0xFFC4849B),
        ChemTheme.milo  => isDark ? const Color(0xFF2E6047) : const Color(0xFF6BA88B),
        ChemTheme.tutor => isDark ? const Color(0xFF464D7A) : const Color(0xFF94A3B8),
      };

  // ── Gradients ─────────────────────────────────────────────────────────────
  static LinearGradient get gradientPurple => LinearGradient(
        colors: [purple, purpleLight],
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
      );

  static LinearGradient get gradientCyan => LinearGradient(
        colors: [cyan, cyanDim],
        begin: Alignment.centerLeft,
        end: Alignment.centerRight,
      );

  static LinearGradient get gradientCard => LinearGradient(
        colors: [bgCard, bgCardAlt],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );

  static RadialGradient get gradientBg => RadialGradient(
        center: Alignment.center,
        radius: 1.2,
        colors: [bgBase, bgDeep],
      );

  // ── Theme preview colors (for the picker UI) ───────────────────────────────
  static const tutorPreviewDark  = Color(0xFF8B7DF8);
  static const tutorPreviewLight = Color(0xFF0C0F2A);
  static const lunaPreviewPink   = Color(0xFFFF6B9D);
  static const lunaPreviewDeep   = Color(0xFF2D1022);
  static const miloPreviewGreen  = Color(0xFF34D399);
  static const miloPreviewDeep   = Color(0xFF0D2416);
}
