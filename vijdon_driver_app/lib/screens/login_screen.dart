import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import 'register_screen.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {
  final _formKey  = GlobalKey<FormState>();
  final _phoneCtr = TextEditingController(text: '+998');
  final _passCtr  = TextEditingController();
  bool _loading   = false;
  bool _obscure   = true;

  late final AnimationController _enter;
  late final AnimationController _bg;
  late final Animation<double>   _fade;
  late final Animation<Offset>   _cardSlide;
  late final Animation<double>   _cardFade;

  @override
  void initState() {
    super.initState();
    _enter = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));
    _bg    = AnimationController(vsync: this, duration: const Duration(seconds: 12))..repeat(reverse: true);

    _fade      = CurvedAnimation(parent: _enter, curve: const Interval(0.0, 0.5, curve: Curves.easeOut));
    _cardSlide = Tween<Offset>(begin: const Offset(0, 0.12), end: Offset.zero)
        .animate(CurvedAnimation(parent: _enter, curve: const Interval(0.2, 1.0, curve: Curves.easeOutCubic)));
    _cardFade  = CurvedAnimation(parent: _enter, curve: const Interval(0.2, 0.8, curve: Curves.easeOut));

    _enter.forward();
  }

  @override
  void dispose() {
    _enter.dispose();
    _bg.dispose();
    _phoneCtr.dispose();
    _passCtr.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    HapticFeedback.lightImpact();
    setState(() => _loading = true);
    try {
      await ApiService.login(_phoneCtr.text.trim(), _passCtr.text);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      Navigator.pushReplacement(context, PageRouteBuilder(
        pageBuilder: (_, __, ___) => const HomeScreen(),
        transitionsBuilder: (_, a, __, c) => FadeTransition(opacity: a, child: c),
        transitionDuration: const Duration(milliseconds: 500),
      ));
    } on ApiException catch (e) {
      HapticFeedback.vibrate();
      _snack(e.message, error: true);
    } catch (_) {
      HapticFeedback.vibrate();
      _snack('Internet aloqasini tekshiring.', error: true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(
        content: Row(children: [
          Icon(error ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
              color: Colors.white, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
        ]),
        backgroundColor: error ? AppColors.danger : AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: const EdgeInsets.all(20),
        elevation: 4,
        duration: const Duration(seconds: 3),
      ));
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final size = MediaQuery.of(context).size;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: Stack(
        children: [
          // Animated gradient background
          AnimatedBuilder(
            animation: _bg,
            builder: (_, __) => CustomPaint(
              size: size,
              painter: _LoginBgPainter(_bg.value, dark),
            ),
          ),

          // Floating orbs
          Positioned(top: -80, right: -60,
            child: _Orb(size: 260, color: AppColors.primary, opacity: dark ? 0.08 : 0.12)),
          Positioned(bottom: size.height * 0.25, left: -80,
            child: _Orb(size: 200, color: AppColors.accent, opacity: dark ? 0.06 : 0.08)),
          Positioned(bottom: -60, right: size.width * 0.2,
            child: _Orb(size: 160, color: AppColors.primary, opacity: dark ? 0.05 : 0.07)),

          // Content
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Logo section
                      FadeTransition(
                        opacity: _fade,
                        child: _LogoSection(dark: dark),
                      ),

                      const SizedBox(height: 36),

                      // Glass card
                      SlideTransition(
                        position: _cardSlide,
                        child: FadeTransition(
                          opacity: _cardFade,
                          child: _GlassCard(
                            dark: dark,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                // Header
                                Text(
                                  'Xush kelibsiz 👋',
                                  style: TextStyle(
                                    fontSize: 22,
                                    fontWeight: FontWeight.w900,
                                    color: dark ? Colors.white : const Color(0xFF0F172A),
                                    letterSpacing: -0.5,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Hisobingizga kiring',
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: dark ? Colors.grey.shade400 : Colors.grey.shade500,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                const SizedBox(height: 28),

                                // Phone field
                                _FieldLabel(label: 'Telefon raqami', dark: dark),
                                const SizedBox(height: 8),
                                _ModernField(
                                  controller: _phoneCtr,
                                  dark: dark,
                                  hint: '+998 (90) 000-00-00',
                                  icon: Icons.phone_iphone_rounded,
                                  keyboardType: TextInputType.phone,
                                  validator: (v) {
                                    if (v == null || v.trim().isEmpty) return 'Raqam kiriting';
                                    if (v.trim().length < 9) return "Raqam noto'g'ri";
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 20),

                                // Password field
                                _FieldLabel(label: 'Parol', dark: dark),
                                const SizedBox(height: 8),
                                _ModernField(
                                  controller: _passCtr,
                                  dark: dark,
                                  hint: '••••••••',
                                  icon: Icons.lock_outline_rounded,
                                  obscure: _obscure,
                                  onToggleObscure: () => setState(() => _obscure = !_obscure),
                                  onSubmitted: (_) => _login(),
                                  validator: (v) => (v == null || v.length < 6) ? 'Kamida 6 ta belgi' : null,
                                ),
                                const SizedBox(height: 32),

                                // Login button
                                _LoginButton(loading: _loading, onTap: _login),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 20),

                      // Register link
                      FadeTransition(
                        opacity: _cardFade,
                        child: _RegisterLink(dark: dark, context: context),
                      ),

                      const SizedBox(height: 16),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _LogoSection extends StatelessWidget {
  final bool dark;
  const _LogoSection({required this.dark});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 88, height: 88,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF00E676), Color(0xFF00C853), Color(0xFF00BFA5)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary.withValues(alpha: 0.45),
                blurRadius: 28,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Positioned(
                top: 10, left: 12,
                child: Container(
                  width: 32, height: 12,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
              const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 44),
            ],
          ),
        ),
        const SizedBox(height: 16),
        RichText(
          text: TextSpan(
            children: [
              TextSpan(
                text: 'Vijdon',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  color: dark ? Colors.white : const Color(0xFF0F172A),
                  letterSpacing: -1.5,
                ),
              ),
              const TextSpan(
                text: 'Taxi',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  color: AppColors.primary,
                  letterSpacing: -1.5,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _GlassCard extends StatelessWidget {
  final bool dark;
  final Widget child;
  const _GlassCard({required this.dark, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        color: dark
            ? Colors.white.withValues(alpha: 0.05)
            : Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(28),
        border: Border.all(
          color: dark
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.white.withValues(alpha: 0.9),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: dark
                ? Colors.black.withValues(alpha: 0.4)
                : Colors.black.withValues(alpha: 0.06),
            blurRadius: 40,
            offset: const Offset(0, 16),
          ),
          if (!dark)
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.04),
              blurRadius: 60,
              offset: const Offset(0, 8),
            ),
        ],
      ),
      child: child,
    );
  }
}

class _FieldLabel extends StatelessWidget {
  final String label;
  final bool dark;
  const _FieldLabel({required this.label, required this.dark});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: dark ? Colors.grey.shade400 : Colors.grey.shade600,
        letterSpacing: 0.3,
      ),
    );
  }
}

class _ModernField extends StatelessWidget {
  final TextEditingController controller;
  final bool dark;
  final String hint;
  final IconData icon;
  final TextInputType? keyboardType;
  final bool obscure;
  final VoidCallback? onToggleObscure;
  final ValueChanged<String>? onSubmitted;
  final String? Function(String?)? validator;

  const _ModernField({
    required this.controller,
    required this.dark,
    required this.hint,
    required this.icon,
    this.keyboardType,
    this.obscure = false,
    this.onToggleObscure,
    this.onSubmitted,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscure,
      onFieldSubmitted: onSubmitted,
      validator: validator,
      style: TextStyle(
        fontWeight: FontWeight.w600,
        fontSize: 15,
        color: dark ? Colors.white : const Color(0xFF0F172A),
        letterSpacing: obscure ? 2 : 0.3,
      ),
      decoration: InputDecoration(
        hintText: hint,
        filled: true,
        fillColor: dark
            ? Colors.white.withValues(alpha: 0.06)
            : const Color(0xFFF8FAFC),
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        prefixIcon: Container(
          margin: const EdgeInsets.only(left: 14, right: 10),
          child: Icon(icon, size: 20,
              color: dark ? Colors.grey.shade500 : Colors.grey.shade400),
        ),
        prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
        suffixIcon: onToggleObscure != null
            ? IconButton(
                icon: Icon(
                  obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                  size: 20,
                  color: dark ? Colors.grey.shade500 : Colors.grey.shade400,
                ),
                onPressed: onToggleObscure,
              )
            : null,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
              color: dark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(
              color: dark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0)),
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
        hintStyle: TextStyle(
          color: dark ? Colors.grey.shade600 : Colors.grey.shade400,
          fontSize: 14,
          fontWeight: FontWeight.normal,
        ),
      ),
    );
  }
}

class _LoginButton extends StatelessWidget {
  final bool loading;
  final VoidCallback onTap;
  const _LoginButton({required this.loading, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: loading ? null : onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 56,
        decoration: BoxDecoration(
          gradient: loading
              ? null
              : const LinearGradient(
                  colors: [Color(0xFF00E676), Color(0xFF00C853)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
          color: loading ? Colors.grey.shade300 : null,
          borderRadius: BorderRadius.circular(18),
          boxShadow: loading
              ? []
              : [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.45),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
        ),
        child: Center(
          child: loading
              ? const SizedBox(
                  width: 24, height: 24,
                  child: CircularProgressIndicator(
                    color: Colors.white, strokeWidth: 2.5),
                )
              : const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      'Tizimga kirish',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                        color: Colors.black,
                        letterSpacing: 0.2,
                      ),
                    ),
                    SizedBox(width: 10),
                    Icon(Icons.arrow_forward_rounded, color: Colors.black, size: 20),
                  ],
                ),
        ),
      ),
    );
  }
}

class _RegisterLink extends StatelessWidget {
  final bool dark;
  final BuildContext context;
  const _RegisterLink({required this.dark, required this.context});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          "Hisobingiz yo'qmi? ",
          style: TextStyle(
            fontSize: 13,
            color: dark ? Colors.grey.shade500 : Colors.grey.shade500,
            fontWeight: FontWeight.w500,
          ),
        ),
        GestureDetector(
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const RegisterScreen()),
          ),
          child: const Text(
            "Ro'yxatdan o'tish",
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: AppColors.primary,
            ),
          ),
        ),
      ],
    );
  }
}

class _Orb extends StatelessWidget {
  final double size;
  final Color color;
  final double opacity;
  const _Orb({required this.size, required this.color, required this.opacity});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size, height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [color.withValues(alpha: opacity), color.withValues(alpha: 0)],
        ),
      ),
    );
  }
}

class _LoginBgPainter extends CustomPainter {
  final double t;
  final bool dark;
  _LoginBgPainter(this.t, this.dark);

  @override
  void paint(Canvas canvas, Size size) {
    final bg = dark ? const Color(0xFF0B0D13) : const Color(0xFFF0FDF4);
    canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), Paint()..color = bg);

    // Subtle mesh gradient blobs
    final blobs = <(double, double, double, Color, double)>[
      (size.width * 0.85, size.height * 0.1, 180.0, AppColors.primary, 0.06),
      (size.width * 0.1,  size.height * 0.4, 150.0, AppColors.accent,  0.04),
      (size.width * 0.5,  size.height * 0.9, 200.0, AppColors.primary, 0.05),
    ];

    for (final b in blobs) {
      final dx = b.$1 + sin(t * pi * 2) * 20;
      final dy = b.$2 + cos(t * pi * 2) * 15;
      final paint = Paint()
        ..shader = RadialGradient(
          colors: [
            b.$4.withValues(alpha: b.$5 * (dark ? 1.2 : 1.0)),
            b.$4.withValues(alpha: 0),
          ],
        ).createShader(Rect.fromCircle(center: Offset(dx, dy), radius: b.$3));
      canvas.drawCircle(Offset(dx, dy), b.$3, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _LoginBgPainter old) => old.t != t;
}
