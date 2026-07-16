import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import 'home_screen.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _logo;
  late final AnimationController _text;
  late final AnimationController _bar;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoFade;
  late final Animation<double> _textFade;
  late final Animation<Offset> _textSlide;
  late final Animation<double> _barWidth;

  @override
  void initState() {
    super.initState();

    _logo = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _text = AnimationController(vsync: this, duration: const Duration(milliseconds: 500));
    _bar  = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000));

    _logoScale = Tween<double>(begin: 0.6, end: 1.0).animate(
        CurvedAnimation(parent: _logo, curve: Curves.easeOutBack));
    _logoFade  = CurvedAnimation(parent: _logo, curve: Curves.easeOut);

    _textFade  = CurvedAnimation(parent: _text, curve: Curves.easeOut);
    _textSlide = Tween<Offset>(begin: const Offset(0, 0.3), end: Offset.zero)
        .animate(CurvedAnimation(parent: _text, curve: Curves.easeOutCubic));

    _barWidth = CurvedAnimation(parent: _bar, curve: Curves.easeInOut);

    _logo.forward().then((_) {
      _text.forward();
      _bar.forward();
    });

    Future.delayed(const Duration(milliseconds: 2600), _navigate);
  }

  Future<void> _navigate() async {
    try {
      await [Permission.location, Permission.notification].request();
    } catch (_) {}

    final token = await ApiService.getToken();
    if (!mounted) return;
    Widget dest;
    if (token != null) {
      try {
        await ApiService.getProfile();
        dest = const HomeScreen();
      } on ApiException catch (e) {
        dest = e.isUnauthorized ? const LoginScreen() : const HomeScreen();
        if (e.isUnauthorized) await ApiService.clearToken();
      } catch (_) {
        dest = const HomeScreen();
      }
    } else {
      dest = const LoginScreen();
    }
    if (!mounted) return;
    Navigator.pushReplacement(context, PageRouteBuilder(
      pageBuilder: (_, __, ___) => dest,
      transitionsBuilder: (_, a, __, c) => FadeTransition(opacity: a, child: c),
      transitionDuration: const Duration(milliseconds: 400),
    ));
  }

  @override
  void dispose() {
    _logo.dispose();
    _text.dispose();
    _bar.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgDark,
      body: Stack(
        children: [
          // Center content
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Logo box — Yandex style square
                FadeTransition(
                  opacity: _logoFade,
                  child: ScaleTransition(
                    scale: _logoScale,
                    child: Container(
                      width: 100, height: 100,
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: const Center(
                        child: Icon(Icons.local_taxi_rounded,
                            color: AppColors.textPrimary, size: 52),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 28),

                // Brand name
                FadeTransition(
                  opacity: _textFade,
                  child: SlideTransition(
                    position: _textSlide,
                    child: Column(
                      children: [
                        RichText(
                          text: const TextSpan(
                            children: [
                              TextSpan(
                                text: 'Vijdon',
                                style: TextStyle(
                                  fontSize: 38, fontWeight: FontWeight.w900,
                                  color: Colors.white, letterSpacing: -1.5,
                                ),
                              ),
                              TextSpan(
                                text: ' Driver',
                                style: TextStyle(
                                  fontSize: 38, fontWeight: FontWeight.w900,
                                  color: AppColors.primary, letterSpacing: -1.5,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'HAYDOVCHI ILOVASI',
                          style: TextStyle(
                            fontSize: 11, fontWeight: FontWeight.w700,
                            color: AppColors.textSecondaryDark,
                            letterSpacing: 3,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Bottom progress bar
          Positioned(
            bottom: 0, left: 0, right: 0,
            child: FadeTransition(
              opacity: _textFade,
              child: Column(
                children: [
                  AnimatedBuilder(
                    animation: _barWidth,
                    builder: (_, __) => LinearProgressIndicator(
                      value: _barWidth.value,
                      backgroundColor: AppColors.borderDark,
                      valueColor: const AlwaysStoppedAnimation(AppColors.primary),
                      minHeight: 3,
                    ),
                  ),
                  Container(
                    color: AppColors.cardDark,
                    padding: EdgeInsets.only(
                      top: 16, bottom: MediaQuery.of(context).padding.bottom + 16,
                    ),
                    child: const Center(
                      child: Text(
                        'v1.0.0  ·  © 2026 Vijdon Driver',
                        style: TextStyle(
                          fontSize: 11, color: AppColors.textSecondaryDark,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
