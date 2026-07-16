import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

class AppColors {
  // ── Brand ──────────────────────────────────────────────────────────────────
  static const Color primary      = Color(0xFFFFD600);
  static const Color primaryDark  = Color(0xFFE6C200);
  static const Color primaryLight = Color(0xFFFFF9CC);

  // ── Light surfaces ─────────────────────────────────────────────────────────
  static const Color bg          = Color(0xFFF2F2F7); // iOS systemGroupedBackground
  static const Color card        = Color(0xFFFFFFFF);
  static const Color surface     = Color(0xFFEFEFF4); // iOS secondarySystemBackground
  static const Color border      = Color(0xFFE5E5EA); // iOS separator

  // ── Dark surfaces ─────────────────────────────────────────────────────────
  static const Color bgDark       = Color(0xFF000000); // iOS true black
  static const Color cardDark     = Color(0xFF1C1C1E); // iOS secondarySystemBackground dark
  static const Color surfaceDark  = Color(0xFF2C2C2E); // iOS tertiarySystemBackground dark
  static const Color elevatedDark = Color(0xFF3A3A3C);
  static const Color borderDark   = Color(0xFF38383A); // iOS separator dark

  // ── Aliases ────────────────────────────────────────────────────────────────
  static const Color bgLight      = bg;
  static const Color cardLight    = card;
  static const Color surfaceLight = surface;
  static const Color borderLight  = border;

  // ── Text ───────────────────────────────────────────────────────────────────
  static const Color textPrimary       = Color(0xFF000000); // iOS label
  static const Color textSecondary     = Color(0xFF8E8E93); // iOS secondaryLabel
  static const Color textPrimaryDark   = Color(0xFFFFFFFF);
  static const Color textSecondaryDark = Color(0xFF8E8E93);

  // ── Status (iOS system colors) ─────────────────────────────────────────────
  static const Color success = Color(0xFF34C759); // iOS green
  static const Color danger  = Color(0xFFFF3B30); // iOS red
  static const Color warning = Color(0xFFFF9500); // iOS orange
  static const Color info    = Color(0xFF007AFF); // iOS blue
  static const Color purple  = Color(0xFFAF52DE); // iOS purple
  static const Color accent  = Color(0xFFFFD600);
}

class AppTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorSchemeSeed: AppColors.primary,
    scaffoldBackgroundColor: AppColors.bg,
    cardColor: AppColors.card,
    // iOS da system font ishlatiladi
    fontFamily: '.SF Pro Text',
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: CupertinoPageTransitionsBuilder(),
        TargetPlatform.iOS:     CupertinoPageTransitionsBuilder(),
      },
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.card,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      centerTitle: true, // iOS center title
      iconTheme: IconThemeData(color: AppColors.info, size: 22), // iOS blue back button
      titleTextStyle: TextStyle(
        fontSize: 17, fontWeight: FontWeight.w600, // iOS nav title weight
        color: AppColors.textPrimary, letterSpacing: -0.4,
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
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.info, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: AppColors.danger, width: 1.5),
      ),
      hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 16),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.info,
        side: const BorderSide(color: AppColors.border, width: 1),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.border,
      space: 0,
      thickness: 0.5, // iOS thin separator
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.card,
      selectedItemColor: AppColors.info, // iOS blue selected
      unselectedItemColor: AppColors.textSecondary,
      elevation: 0,
      type: BottomNavigationBarType.fixed,
    ),
    // iOS card style
    cardTheme: CardThemeData(
      color: AppColors.card,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.border, width: 0.5),
      ),
      margin: EdgeInsets.zero,
    ),
    // iOS switch
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.all(Colors.white),
      trackColor: WidgetStateProperty.resolveWith((s) =>
          s.contains(WidgetState.selected) ? AppColors.success : AppColors.border),
    ),
    // Splash/highlight — iOS da yo'q
    splashFactory: NoSplash.splashFactory,
    highlightColor: Colors.transparent,
  );

  static ThemeData get darkTheme => light;
}
