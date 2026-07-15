import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  // ── Brand: Yandex Taxi Yellow ──────────────────────────────────────────────
  static const Color primary      = Color(0xFFFFCC00); // Yandex sariq
  static const Color primaryDark  = Color(0xFFE6B800);
  static const Color primaryLight = Color(0xFFFFF8CC);

  // ── Dark surfaces (Yandex qora) ────────────────────────────────────────────
  static const Color bgDark      = Color(0xFF111111);
  static const Color cardDark    = Color(0xFF1C1C1C);
  static const Color surfaceDark = Color(0xFF252525);
  static const Color borderDark  = Color(0xFF333333);

  // ── Light surfaces ─────────────────────────────────────────────────────────
  static const Color bgLight     = Color(0xFFF5F5F5);
  static const Color cardLight   = Color(0xFFFFFFFF);
  static const Color borderLight = Color(0xFFE8E8E8);

  // ── Text ───────────────────────────────────────────────────────────────────
  static const Color textPrimary      = Color(0xFF111111);
  static const Color textSecondary    = Color(0xFF888888);
  static const Color textPrimaryDark  = Color(0xFFFFFFFF);
  static const Color textSecondaryDark= Color(0xFF888888);

  // ── Status ─────────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF21C55D);
  static const Color danger  = Color(0xFFEF4444);
  static const Color warning = Color(0xFFFFCC00);
  static const Color info    = Color(0xFF3B82F6);
  static const Color purple  = Color(0xFF8B5CF6);
  static const Color accent  = Color(0xFFFFCC00);
}

class AppTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bgLight,
    cardColor: AppColors.cardLight,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      centerTitle: false,
      iconTheme: IconThemeData(color: AppColors.textPrimary, size: 22),
      titleTextStyle: TextStyle(
          fontSize: 20, fontWeight: FontWeight.w900,
          color: AppColors.textPrimary, letterSpacing: -0.5),
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFFF5F5F5),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        side: const BorderSide(color: AppColors.borderLight, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.borderLight, space: 1),
  );

  static ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bgDark,
    cardColor: AppColors.cardDark,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.cardDark,
      foregroundColor: AppColors.textPrimaryDark,
      elevation: 0,
      centerTitle: false,
      iconTheme: IconThemeData(color: AppColors.textPrimaryDark, size: 22),
      titleTextStyle: TextStyle(
          fontSize: 20, fontWeight: FontWeight.w900,
          color: AppColors.textPrimaryDark, letterSpacing: -0.5),
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceDark,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondaryDark, fontSize: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimaryDark,
        side: const BorderSide(color: AppColors.borderDark, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.borderDark, space: 1),
  );
}
