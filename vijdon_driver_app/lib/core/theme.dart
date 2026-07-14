import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class AppColors {
  // Brand — Green palette
  static const Color green    = Color(0xFF16A34A); // primary green
  static const Color green2   = Color(0xFF15803D); // darker green
  static const Color greenBg  = Color(0xFFF0FDF4); // light green background

  // Keep old names as aliases for backward compatibility
  static const Color amber    = green;
  static const Color amber2   = green2;
  static const Color amberBg  = greenBg;

  // Status
  static const Color success  = Color(0xFF10B981);
  static const Color danger   = Color(0xFFEF4444);
  static const Color info     = Color(0xFF3B82F6);
  static const Color purple   = Color(0xFF8B5CF6);
  static const Color warning  = Color(0xFFF59E0B);

  // Light mode
  static const Color bgLight  = Color(0xFFF1F5F9);
  static const Color cardLight = Colors.white;
  static const Color textPrimary = Color(0xFF0F172A);
  static const Color textSecondary = Color(0xFF64748B);

  // Dark mode
  static const Color bgDark   = Color(0xFF071310);
  static const Color cardDark = Color(0xFF0D1F1A);
  static const Color surfaceDark = Color(0xFF142920);
  static const Color borderDark = Color(0xFF1E3A2E);
}

class AppTheme {
  // Keep backward compat
  static const Color primary  = AppColors.green;
  static const Color primary2 = AppColors.green2;
  static const Color success  = AppColors.success;
  static const Color danger   = AppColors.danger;
  static const Color info     = AppColors.info;
  static const Color warning  = AppColors.warning;

  static ThemeData get light => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: AppColors.green,
    fontFamily: 'Roboto',
    scaffoldBackgroundColor: AppColors.bgLight,
    cardColor: AppColors.cardLight,
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      centerTitle: false,
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: Colors.white,
      indicatorColor: AppColors.green.withValues(alpha: 0.15),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: AppColors.green);
        }
        return const IconThemeData(color: AppColors.textSecondary);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.green);
        }
        return const TextStyle(fontSize: 11, color: AppColors.textSecondary);
      }),
      elevation: 0,
      height: 62,
    ),
    dividerTheme: DividerThemeData(color: Colors.grey.withValues(alpha: 0.1), space: 1),
  );

  static ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: AppColors.green,
    fontFamily: 'Roboto',
    scaffoldBackgroundColor: AppColors.bgDark,
    cardColor: AppColors.cardDark,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.cardDark,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.cardDark,
      indicatorColor: AppColors.green.withValues(alpha: 0.2),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: AppColors.green);
        }
        return IconThemeData(color: Colors.grey.shade500);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.green);
        }
        return TextStyle(fontSize: 11, color: Colors.grey.shade500);
      }),
      elevation: 0,
      height: 62,
    ),
    dividerTheme: DividerThemeData(color: AppColors.borderDark.withValues(alpha: 0.6), space: 1),
  );
}
