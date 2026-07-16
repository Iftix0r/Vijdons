import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:yandex_mapkit/yandex_mapkit.dart';
import 'core/theme.dart';
import 'core/notification_service.dart';
import 'screens/splash_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  AndroidYandexMap.useAndroidViewSurface = false;
  // API key AndroidManifest.xml orqali beriladi, initialize chaqirilmaydi

  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    systemNavigationBarColor: Colors.transparent,
  ));
  await SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);

  await NotificationService.init();

  runApp(const VijdonDriverApp());
}

class VijdonDriverApp extends StatelessWidget {
  const VijdonDriverApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VijdonTaxi',
      debugShowCheckedModeBanner: false,
      theme:     AppTheme.light,
      themeMode: ThemeMode.light,
      home: const SplashScreen(),
    );
  }
}
