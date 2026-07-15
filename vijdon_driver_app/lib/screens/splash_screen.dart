import 'dart:math';
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
  late final AnimationController _main;
  late final AnimationController _pulse;
  late final AnimationController _particles;

  late final Animation<double> _logoScale;
  late final Animation<double> _logoFade;
  late final Animation<double> _textFade;
  late final Animation<Offset> _textSlide;
  late final Animation<double> _barFade;

  @override
  void initState() {
    super.initState();

    _main = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800));
    _pulse = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000))..repeat(reverse: true);
    _particles = AnimationController(vsync: this, duration: const Duration(seconds: 8))..repeat();

    _logoScale = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _main, curve: const Interval(0.0, 0.55, curve: Curves.elasticOut)));
    _logoFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _main, curve: const Interval(0.0, 0.3, curve: Curves.easeOut)));
    _textFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _main, curve: const Interval(0.45, 0.75, curve: Curves.easeOut)));
    _textSlide = Tween<Offset>(begin: const Offset(0, 0.4), end: Offset.zero).animate(
        CurvedAnimation(parent: _main, curve: const Interval(0.45, 0.8, curve: Curves.easeOutCubic)));
    _barFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _main, curve: const Interval(0.7, 1.0, curve: Curves.easeOut)));

    _main.forward();
    Future.delayed(const Duration(milliseconds: 2800), _navigate);
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
      transitionDuration: const Duration(milliseconds: 600),
    ));
  }

  @override
  void dispose() {
    _main.dispose();
    _pulse.dispose();
    _particles.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Stack(
        children: [
          // Animated gradient background
          AnimatedBuilder(
            animation: _particles,
            builder: (_, __) => CustomPaint(
              size: size,
              painter: _BgPainter(_particles.value, dark),
            ),
          ),

          // Floating orbs
          _orb(size.width * 0.8, -60, 220, AppColors.primary, 0.07, dark),
          _orb(-60, size.height * 0.6, 180, AppColors.accent, 0.05, dark),
          _orb(size.width * 0.3, size.height * 0.85, 140, AppColors.primary, 0.04, dark),

          // Main content
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Logo
                AnimatedBuilder(
                  animation: _pulse,
                  builder: (_, child) => Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: AppColors.primary.withValues(alpha: 0.15 + _pulse.value * 0.15),
                          blurRadius: 40 + _pulse.value * 30,
                          spreadRadius: 5 + _pulse.value * 10,
                        ),
                      ],
                    ),
                    child: child,
                  ),
                  child: FadeTransition(
                    opacity: _logoFade,
                    child: ScaleTransition(
                      scale: _logoScale,
                      child: Container(
                        width: 120, height: 120,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF00E676), Color(0xFF00C853), Color(0xFF00BFA5)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(36),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.5),
                              blurRadius: 30,
                              offset: const Offset(0, 12),
                            ),
                          ],
                        ),
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            // Shine effect
                            Positioned(
                              top: 12, left: 16,
                              child: Container(
                                width: 40, height: 16,
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.25),
                                  borderRadius: BorderRadius.circular(20),
                                ),
                              ),
                            ),
                            const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 58),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 32),

                // Brand text
                FadeTransition(
                  opacity: _textFade,
                  child: SlideTransition(
                    position: _textSlide,
                    child: Column(
                      children: [
                        RichText(
                          text: TextSpan(
                            children: [
                              TextSpan(
                                text: 'Vijdon',
                                style: TextStyle(
                                  fontSize: 42,
                                  fontWeight: FontWeight.w900,
                                  color: dark ? Colors.white : const Color(0xFF0F172A),
                                  letterSpacing: -2,
                                ),
                              ),
                              const TextSpan(
                                text: 'Taxi',
                                style: TextStyle(
                                  fontSize: 42,
                                  fontWeight: FontWeight.w900,
                                  color: AppColors.primary,
                                  letterSpacing: -2,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                          decoration: BoxDecoration(
                            color: AppColors.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
                          ),
                          child: const Text(
                            'HAYDOVCHI ILOVASI',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primary,
                              letterSpacing: 3,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 72),

                // Loading bar
                FadeTransition(
                  opacity: _barFade,
                  child: _AnimatedLoadingBar(dark: dark),
                ),
              ],
            ),
          ),

          // Bottom version
          Positioned(
            bottom: 36,
            left: 0, right: 0,
            child: FadeTransition(
              opacity: _barFade,
              child: Text(
                'v1.0.0  ·  © 2026 VijdonTaxi',
                textAlign: TextAlign.center,
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
    );
  }

  Widget _orb(double x, double y, double size, Color color, double opacity, bool dark) {
    return Positioned(
      left: x, top: y,
      child: Container(
        width: size, height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(
            colors: [
              color.withValues(alpha: opacity * (dark ? 1.5 : 1.0)),
              color.withValues(alpha: 0),
            ],
          ),
        ),
      ),
    );
  }
}

class _BgPainter extends CustomPainter {
  final double t;
  final bool dark;
  _BgPainter(this.t, this.dark);

  @override
  void paint(Canvas canvas, Size size) {
    final bg = dark ? const Color(0xFF0B0D13) : const Color(0xFFF0FDF4);
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), Paint()..color = bg);

    final paint = Paint()..style = PaintingStyle.fill;
    final rng = Random(42);
    for (int i = 0; i < 18; i++) {
      final x = rng.nextDouble() * size.width;
      final y = rng.nextDouble() * size.height;
      final r = 1.5 + rng.nextDouble() * 2.5;
      final phase = rng.nextDouble() * 2 * pi;
      final opacity = (0.3 + 0.7 * ((sin(t * 2 * pi + phase) + 1) / 2)) * (dark ? 0.25 : 0.15);
      paint.color = AppColors.primary.withValues(alpha: opacity);
      canvas.drawCircle(Offset(x, y), r, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _BgPainter old) => old.t != t;
}

class _AnimatedLoadingBar extends StatefulWidget {
  final bool dark;
  const _AnimatedLoadingBar({required this.dark});
  @override
  State<_AnimatedLoadingBar> createState() => _AnimatedLoadingBarState();
}

class _AnimatedLoadingBarState extends State<_AnimatedLoadingBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 2200))..forward();
    _anim = CurvedAnimation(parent: _c, curve: Curves.easeInOutCubic);
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AnimatedBuilder(
          animation: _anim,
          builder: (_, __) => Container(
            width: 160,
            height: 3,
            decoration: BoxDecoration(
              color: widget.dark ? AppColors.borderDark : AppColors.borderLight,
              borderRadius: BorderRadius.circular(2),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: _anim.value,
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.primary, AppColors.accent],
                  ),
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: [
                    BoxShadow(color: AppColors.primary.withValues(alpha: 0.5), blurRadius: 6),
                  ],
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'Yuklanmoqda...',
          style: TextStyle(
            fontSize: 12,
            color: widget.dark ? Colors.grey.shade500 : Colors.grey.shade400,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}
