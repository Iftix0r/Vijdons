import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/theme.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final token  = prefs.getString('auth_token');
  runApp(VijdonDriverApp(initialRoute: token != null ? 'home' : 'login'));
}

class VijdonDriverApp extends StatelessWidget {
  final String initialRoute;
  const VijdonDriverApp({super.key, required this.initialRoute});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VijdonTaxi',
      debugShowCheckedModeBanner: false,
      theme:      AppTheme.light,
      darkTheme:  AppTheme.darkTheme,
      themeMode:  ThemeMode.system,
      home: initialRoute == 'home' ? const HomeScreen() : const LoginScreen(),
    );
  }
}
