import 'package:flutter/material.dart';

class AppTheme {
  static const Color primary   = Color(0xFFF59E0B);
  static const Color primary2  = Color(0xFFD97706);
  static const Color darkBg    = Color(0xFF111827);
  static const Color darkCard  = Color(0xFF1F2937);
  static const Color darkBorder = Color(0xFF374151);
  static const Color success   = Color(0xFF10B981);
  static const Color danger    = Color(0xFFEF4444);
  static const Color info      = Color(0xFF3B82F6);
  static const Color warning   = Color(0xFFF59E0B);

  static ThemeData get light => ThemeData(
    useMaterial3: true,
    colorSchemeSeed: primary,
    fontFamily: 'Roboto',
    scaffoldBackgroundColor: const Color(0xFFF8FAFC),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: Color(0xFF111827),
      elevation: 0,
      centerTitle: true,
    ),
  );

  static ThemeData get darkTheme => ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorSchemeSeed: primary,
    fontFamily: 'Roboto',
    scaffoldBackgroundColor: const Color(0xFF0F172A),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF1E293B),
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
  );
}
