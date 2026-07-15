import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  // Brand Primary: Electric Emerald Green (looks ultra-modern on dark screens)
  static const Color primary = Color(0xFF00E676); 
  static const Color primaryDark = Color(0xFF00C853);
  static const Color primaryLight = Color(0xFFE8F5E9);

  // Brand Accent: Electric Amber/Gold (Taxi feel)
  static const Color accent = Color(0xFFFFB300);
  static const Color accentDark = Color(0xFFFF8F00);
  static const Color accentLight = Color(0xFFFFF8E1);

  // Status & Utility
  static const Color success = Color(0xFF00E676);
  static const Color danger = Color(0xFFFF3D00);
  static const Color warning = Color(0xFFFFC107);
  static const Color info = Color(0xFF2979FF);
  static const Color purple = Color(0xFF651FFF);

  // Light Mode Colors
  static const Color bgLight = Color(0xFFF6F8FA);
  static const Color cardLight = Colors.white;
  static const Color textPrimary = Color(0xFF1A1D24);
  static const Color textSecondary = Color(0xFF6C757D);
  static const Color borderLight = Color(0xFFE9ECEF);

  // Dark Mode Colors: Deep Space Obsidian (dark slate/black blend)
  static const Color bgDark = Color(0xFF0B0D13); 
  static const Color cardDark = Color(0xFF131722); 
  static const Color surfaceDark = Color(0xFF1B2030); 
  static const Color borderDark = Color(0xFF242B3F);
  static const Color textPrimaryDark = Color(0xFFF1F3F5);
  static const Color textSecondaryDark = Color(0xFF868E96);

  // Aliases for compatibility
  static const Color green = primary;
  static const Color green2 = primaryDark;
  static const Color greenBg = primaryLight;
  static const Color amber = accent;
  static const Color amber2 = accentDark;
  static const Color amberBg = accentLight;
}

class AppTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bgLight,
    cardColor: AppColors.cardLight,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      centerTitle: true,
      iconTheme: IconThemeData(color: AppColors.textPrimary, size: 22),
      titleTextStyle: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.textPrimary, letterSpacing: -0.5),
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: AppColors.primary.withValues(alpha: 0.1),
      elevation: 8,
      height: 66,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: AppColors.primaryDark, size: 24);
        }
        return const IconThemeData(color: AppColors.textSecondary, size: 22);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: AppColors.primaryDark, letterSpacing: 0.2);
        }
        return const TextStyle(fontSize: 11, color: AppColors.textSecondary, fontWeight: FontWeight.w600);
      }),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borderLight),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.primaryDark, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.danger, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14, fontWeight: FontWeight.normal),
      labelStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14, fontWeight: FontWeight.w600),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryDark,
        foregroundColor: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: 0.2),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primaryDark,
        side: const BorderSide(color: AppColors.primaryDark, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: DividerThemeData(color: Colors.grey.withValues(alpha: 0.1), space: 1),
  );

  static ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bgDark,
    cardColor: AppColors.cardDark,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      foregroundColor: AppColors.textPrimaryDark,
      elevation: 0,
      centerTitle: true,
      iconTheme: IconThemeData(color: AppColors.textPrimaryDark, size: 22),
      titleTextStyle: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppColors.textPrimaryDark, letterSpacing: -0.5),
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
        systemNavigationBarColor: Colors.transparent,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.cardDark,
      indicatorColor: AppColors.primary.withValues(alpha: 0.15),
      elevation: 8,
      height: 66,
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: AppColors.primary, size: 24);
        }
        return const IconThemeData(color: AppColors.textSecondaryDark, size: 22);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: AppColors.primary, letterSpacing: 0.2);
        }
        return const TextStyle(fontSize: 11, color: AppColors.textSecondaryDark, fontWeight: FontWeight.w600);
      }),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceDark,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borderDark),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.danger, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondaryDark, fontSize: 14, fontWeight: FontWeight.normal),
      labelStyle: const TextStyle(color: AppColors.textSecondaryDark, fontSize: 14, fontWeight: FontWeight.w600),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.black,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: 0.2),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primary,
        side: const BorderSide(color: AppColors.primary, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: DividerThemeData(color: AppColors.borderDark.withValues(alpha: 0.6), space: 1),
  );
}
