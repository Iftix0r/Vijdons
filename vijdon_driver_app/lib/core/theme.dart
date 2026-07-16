import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  // ── Brand ──────────────────────────────────────────────────────────────────
  static const Color primary      = Color(0xFFFFD600);
  static const Color primaryDark  = Color(0xFFE6C200);
  static const Color primaryLight = Color(0xFFFFF9CC);

  // ── Light surfaces ─────────────────────────────────────────────────────────
  static const Color bg          = Color(0xFFF5F6FA);
  static const Color card        = Color(0xFFFFFFFF);
  static const Color surface     = Color(0xFFF0F1F5);
  static const Color border      = Color(0xFFE8E9EF);

  // ── Dark surfaces (splash & login screens keep dark bg) ───────────────────
  static const Color bgDark       = Color(0xFF0A0A0A);
  static const Color cardDark     = Color(0xFF161616);
  static const Color surfaceDark  = Color(0xFF1F1F1F);
  static const Color elevatedDark = Color(0xFF252525);
  static const Color borderDark   = Color(0xFF2A2A2A);

  // ── Aliases used in screens ────────────────────────────────────────────────
  static const Color bgLight     = bg;
  static const Color cardLight   = card;
  static const Color surfaceLight= surface;
  static const Color borderLight = border;

  // ── Text ───────────────────────────────────────────────────────────────────
  static const Color textPrimary       = Color(0xFF0F0F0F);
  static const Color textSecondary     = Color(0xFF8A8FA8);
  static const Color textPrimaryDark   = Color(0xFFF5F5F5);
  static const Color textSecondaryDark = Color(0xFF737373);

  // ── Status ─────────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF16C47F);
  static const Color danger  = Color(0xFFFF4757);
  static const Color warning = Color(0xFFFF9F43);
  static const Color info    = Color(0xFF4A90E2);
  static const Color purple  = Color(0xFF9B59B6);
  static const Color accent  = Color(0xFFFFD600);
}

class AppTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bg,
    cardColor: AppColors.card,
    fontFamily: 'Roboto',
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.card,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
      iconTheme: IconThemeData(color: AppColors.textPrimary, size: 22),
      titleTextStyle: TextStyle(
        fontSize: 20, fontWeight: FontWeight.w900,
        color: AppColors.textPrimary, letterSpacing: -0.5,
      ),
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: Colors.white,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.danger, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        side: const BorderSide(color: AppColors.border, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.border, space: 1),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.card,
      selectedItemColor: AppColors.textPrimary,
      unselectedItemColor: AppColors.textSecondary,
      elevation: 0,
    ),
  );

  // darkTheme kept for splash/login screens that explicitly use dark colors
  static ThemeData get darkTheme => light;
}
