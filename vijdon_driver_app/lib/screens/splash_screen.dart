import 'package:flutter/material.dart';
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
    with SingleTickerProviderStateMixin {
  late final AnimationController _ac;
  late final Animation<double> _scale;
  late final Animation<double> _fade;
  late final Animation<double> _textFade;

  @override
  void initState() {
    super.initState();
    _ac = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200));

    _scale = Tween<double>(begin: 0.6, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0, 0.6, curve: Curves.elasticOut)));

    _fade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0, 0.4, curve: Curves.easeOut)));

    _textFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0.5, 1.0, curve: Curves.easeOut)));

    _ac.forward();

    Future.delayed(const Duration(milliseconds: 1800), _navigate);
  }

  Future<void> _navigate() async {
    final token = await ApiService.getToken();
    if (!mounted) return;
    Widget dest;
    if (token != null) {
      // Validate token
      try {
        await ApiService.getProfile();
        dest = const HomeScreen();
      } on ApiException catch (e) {
        if (e.isUnauthorized) {
          await ApiService.clearToken();
          dest = const LoginScreen();
        } else {
          dest = const HomeScreen(); // offline — let home handle it
        }
      } catch (_) {
        dest = const HomeScreen();
      }
    } else {
      dest = const LoginScreen();
    }

    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => dest,
        transitionsBuilder: (_, a, __, c) => FadeTransition(opacity: a, child: c),
        transitionDuration: const Duration(milliseconds: 500),
      ),
    );
  }

  @override
  void dispose() { _ac.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: dark
              ? const LinearGradient(
                  colors: [Color(0xFF0A0F1E), Color(0xFF0F1A2E)],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter)
              : const LinearGradient(
                  colors: [Color(0xFFFFFBEB), Color(0xFFFEF3C7)],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Logo
              AnimatedBuilder(
                animation: _ac,
                builder: (_, child) => FadeTransition(
                  opacity: _fade,
                  child: ScaleTransition(scale: _scale, child: child),
                ),
                child: Container(
                  width: 100, height: 100,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFFCD34D), Color(0xFFF59E0B)],
                      begin: Alignment.topLeft, end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(32),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.amber.withValues(alpha: 0.5),
                        blurRadius: 36, offset: const Offset(0, 16),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 52),
                ),
              ),
              const SizedBox(height: 24),

              // App name
              FadeTransition(
                opacity: _textFade,
                child: Column(
                  children: [
                    const Text(
                      'VijdonTaxi',
                      style: TextStyle(
                        fontSize: 34, fontWeight: FontWeight.w900, letterSpacing: -1.2,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Haydovchi ilovasi',
                      style: TextStyle(
                        fontSize: 15, color: Colors.grey.shade500, fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 60),

              // Loading dots
              FadeTransition(
                opacity: _textFade,
                child: _LoadingDots(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadingDots extends StatefulWidget {
  @override
  State<_LoadingDots> createState() => _LoadingDotsState();
}

class _LoadingDotsState extends State<_LoadingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))
      ..repeat();
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final delay = i * 0.3;
            final v = (_c.value - delay).clamp(0.0, 0.4) / 0.4;
            final opacity = (v <= 0.5 ? v * 2 : (1.0 - v) * 2).clamp(0.2, 1.0);
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              width: 8, height: 8,
              decoration: BoxDecoration(
                color: AppColors.amber.withValues(alpha: opacity),
                shape: BoxShape.circle,
              ),
            );
          }),
        );
      },
    );
  }
}
