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
    with SingleTickerProviderStateMixin {
  late final AnimationController _ac;
  late final Animation<double> _scale;
  late final Animation<double> _fade;
  late final Animation<double> _textFade;
  late final Animation<double> _glow;

  @override
  void initState() {
    super.initState();
    _ac = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500));

    _scale = Tween<double>(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0.0, 0.7, curve: Curves.elasticOut)));

    _fade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0.0, 0.4, curve: Curves.easeOut)));

    _textFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0.5, 1.0, curve: Curves.easeOut)));

    _glow = Tween<double>(begin: 0.8, end: 1.2).animate(
        CurvedAnimation(parent: _ac, curve: const Interval(0.6, 1.0, curve: Curves.easeInOutSine)));

    _ac.forward();

    Future.delayed(const Duration(milliseconds: 2000), _navigate);
  }

  Future<void> _navigate() async {
    try {
      await [
        Permission.location,
        Permission.notification,
      ].request();
    } catch (_) {}

    final token = await ApiService.getToken();
    if (!mounted) return;
    Widget dest;
    if (token != null) {
      try {
        await ApiService.getProfile();
        dest = const HomeScreen();
      } on ApiException catch (e) {
        if (e.isUnauthorized) {
          await ApiService.clearToken();
          dest = const LoginScreen();
        } else {
          dest = const HomeScreen(); 
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
        transitionDuration: const Duration(milliseconds: 600),
      ),
    );
  }

  @override
  void dispose() {
    _ac.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: dark
              ? const LinearGradient(
                  colors: [Color(0xFF030605), Color(0xFF0A110E)],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter)
              : const LinearGradient(
                  colors: [Color(0xFFECFDF5), Color(0xFFF8FAFC)],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Subtly animated background pattern element
            Positioned(
              top: -100, right: -100,
              child: Container(
                width: 300, height: 300,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: dark ? 0.03 : 0.05),
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Positioned(
              bottom: -150, left: -100,
              child: Container(
                width: 350, height: 350,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: dark ? 0.02 : 0.04),
                  shape: BoxShape.circle,
                ),
              ),
            ),
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Logo with glowing pulse
                  AnimatedBuilder(
                    animation: _ac,
                    builder: (_, child) => FadeTransition(
                      opacity: _fade,
                      child: ScaleTransition(scale: _scale, child: child),
                    ),
                    child: AnimatedBuilder(
                      animation: _glow,
                      builder: (_, child) => Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: dark ? 0.25 : 0.15),
                              blurRadius: 40 * _glow.value,
                              spreadRadius: 8 * _glow.value,
                            ),
                          ],
                        ),
                        child: child,
                      ),
                      child: Container(
                        width: 110, height: 110,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF34D399), Color(0xFF10B981), Color(0xFF059669)],
                            begin: Alignment.topLeft, end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(32),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.4),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            ),
                          ],
                        ),
                        child: const Center(
                          child: Icon(Icons.local_taxi_rounded, color: Colors.white, size: 56),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),

                  // Brand name and subtitle
                  FadeTransition(
                    opacity: _textFade,
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Vijdon',
                              style: TextStyle(
                                fontSize: 36,
                                fontWeight: FontWeight.w900,
                                color: dark ? Colors.white : AppColors.textPrimary,
                                letterSpacing: -1.2,
                              ),
                            ),
                            const Text(
                              'Taxi',
                              style: TextStyle(
                                fontSize: 36,
                                fontWeight: FontWeight.w900,
                                color: AppColors.primary,
                                letterSpacing: -1.2,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'HAYDOVCHI ILOVASI',
                          style: TextStyle(
                            fontSize: 12,
                            color: dark ? Colors.grey.shade400 : AppColors.textSecondary,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 3.0,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 80),

                  // Loading dots
                  FadeTransition(
                    opacity: _textFade,
                    child: const _LoadingDots(),
                  ),
                ],
              ),
            ),
            // Footer credits
            Positioned(
              bottom: 40,
              child: FadeTransition(
                opacity: _textFade,
                child: Text(
                  'Barcha huquqlar himoyalangan © 2026',
                  style: TextStyle(
                    fontSize: 11,
                    color: dark ? Colors.grey.shade600 : Colors.grey.shade400,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingDots extends StatefulWidget {
  const _LoadingDots();
  @override
  State<_LoadingDots> createState() => _LoadingDotsState();
}

class _LoadingDotsState extends State<_LoadingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final delay = i * 0.25;
            final v = (_c.value - delay).clamp(0.0, 0.5) / 0.5;
            final opacity = (v <= 0.5 ? v * 2 : (1.0 - v) * 2).clamp(0.15, 1.0);
            final scale = 0.8 + (opacity * 0.4);
            return Transform.scale(
              scale: scale,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 5),
                width: 10, height: 10,
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: opacity),
                  shape: BoxShape.circle,
                  boxShadow: [
                    if (opacity > 0.6)
                      BoxShadow(
                        color: AppColors.primary.withValues(alpha: 0.3),
                        blurRadius: 4,
                        spreadRadius: 1,
                      )
                  ],
                ),
              ),
            );
          }),
        );
      },
    );
  }
}
