import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  // ── Brand: Yandex Taxi Yellow ──────────────────────────────────────────────
  static const Color primary      = Color(0xFFFFD600); // Yandex sariq (to'yingan)
  static const Color primaryDark  = Color(0xFFE6C200);
  static const Color primaryLight = Color(0xFFFFF5CC);

  // ── Dark surfaces — Yandex qora uslubi ────────────────────────────────────
  static const Color bgDark        = Color(0xFF0A0A0A); // eng chuqur qora
  static const Color cardDark      = Color(0xFF161616); // karta
  static const Color surfaceDark   = Color(0xFF1F1F1F); // input/chip
  static const Color elevatedDark  = Color(0xFF252525); // ko'tarma yuzalar
  static const Color borderDark    = Color(0xFF2A2A2A); // chegara

  // ── Light surfaces ─────────────────────────────────────────────────────────
  static const Color bgLight     = Color(0xFFF2F2F2);
  static const Color cardLight   = Color(0xFFFFFFFF);
  static const Color surfaceLight= Color(0xFFF7F7F7);
  static const Color borderLight = Color(0xFFE5E5E5);

  // ── Text ───────────────────────────────────────────────────────────────────
  static const Color textPrimary       = Color(0xFF0A0A0A);
  static const Color textSecondary     = Color(0xFF737373);
  static const Color textPrimaryDark   = Color(0xFFF5F5F5);
  static const Color textSecondaryDark = Color(0xFF737373);

  // ── Status ─────────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF22C55E);
  static const Color danger  = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);
  static const Color info    = Color(0xFF3B82F6);
  static const Color purple  = Color(0xFF8B5CF6);
  static const Color accent  = Color(0xFFFFD600);
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
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceLight,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderLight),
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
        side: const BorderSide(color: AppColors.borderLight, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
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
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: false,
      iconTheme: IconThemeData(color: AppColors.textPrimaryDark, size: 22),
      titleTextStyle: TextStyle(
        fontSize: 20, fontWeight: FontWeight.w900,
        color: AppColors.textPrimaryDark, letterSpacing: -0.5,
      ),
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
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: AppColors.borderDark),
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
      hintStyle: const TextStyle(color: AppColors.textSecondaryDark, fontSize: 14),
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
        foregroundColor: AppColors.textPrimaryDark,
        side: const BorderSide(color: AppColors.borderDark, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: const DividerThemeData(color: AppColors.borderDark, space: 1),
  );
}
