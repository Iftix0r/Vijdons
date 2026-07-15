import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen>
    with TickerProviderStateMixin {
  final _formKey  = GlobalKey<FormState>();
  final _nameCtr  = TextEditingController();
  final _phoneCtr = TextEditingController(text: '+998');
  final _carMCtr  = TextEditingController();
  final _carNCtr  = TextEditingController();
  final _passCtr  = TextEditingController();
  final _pass2Ctr = TextEditingController();
  bool _loading   = false;
  bool _obscure   = true;
  bool _done      = false;

  late final AnimationController _enter;
  late final AnimationController _bg;
  late final Animation<double>   _fade;
  late final Animation<Offset>   _slide;

  @override
  void initState() {
    super.initState();
    _enter = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _bg    = AnimationController(vsync: this, duration: const Duration(seconds: 14))..repeat(reverse: true);
    _fade  = CurvedAnimation(parent: _enter, curve: const Interval(0.0, 0.6, curve: Curves.easeOut));
    _slide = Tween<Offset>(begin: const Offset(0, 0.1), end: Offset.zero)
        .animate(CurvedAnimation(parent: _enter, curve: const Interval(0.1, 1.0, curve: Curves.easeOutCubic)));
    _enter.forward();
  }

  @override
  void dispose() {
    _enter.dispose();
    _bg.dispose();
    for (final c in [_nameCtr, _phoneCtr, _carMCtr, _carNCtr, _passCtr, _pass2Ctr]) c.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    HapticFeedback.lightImpact();
    setState(() => _loading = true);
    try {
      await ApiService.register({
        'full_name':    _nameCtr.text.trim(),
        'phone_number': _phoneCtr.text.trim(),
        'car_model':    _carMCtr.text.trim(),
        'car_number':   _carNCtr.text.trim().toUpperCase(),
        'password':     _passCtr.text,
      });
      HapticFeedback.mediumImpact();
      setState(() => _done = true);
    } on ApiException catch (e) {
      HapticFeedback.vibrate();
      _snack(e.message);
    } catch (_) {
      HapticFeedback.vibrate();
      _snack('Server bilan ulanishda xatolik.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(
        content: Row(children: [
          const Icon(Icons.error_outline_rounded, color: Colors.white, size: 20),
          const SizedBox(width: 12),
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
        ]),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: const EdgeInsets.all(20),
        elevation: 4,
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
          // Animated background
          AnimatedBuilder(
            animation: _bg,
            builder: (_, __) => CustomPaint(
              size: size,
              painter: _RegBgPainter(_bg.value, dark),
            ),
          ),

          // Orbs
          Positioned(top: -60, left: -60,
            child: _Orb(size: 220, color: AppColors.accent, opacity: dark ? 0.07 : 0.1)),
          Positioned(bottom: size.height * 0.3, right: -80,
            child: _Orb(size: 180, color: AppColors.primary, opacity: dark ? 0.06 : 0.08)),

          // Back button
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.only(left: 8, top: 4),
              child: FadeTransition(
                opacity: _fade,
                child: IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                      color: dark ? Colors.white.withValues(alpha: 0.08) : Colors.white.withValues(alpha: 0.7),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: dark ? Colors.white.withValues(alpha: 0.1) : Colors.grey.shade200),
                    ),
                    child: Icon(Icons.arrow_back_ios_new_rounded, size: 16,
                        color: dark ? Colors.white : const Color(0xFF0F172A)),
                  ),
                ),
              ),
            ),
          ),

          // Content
          SafeArea(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 500),
              child: _done ? _successView(dark) : _formView(dark),
            ),
          ),
        ],
      ),
    );
  }

  // ── Success ──────────────────────────────────────────────────────────────────

  Widget _successView(bool dark) {
    return Center(
      key: const ValueKey('success'),
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Animated check icon
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.0, end: 1.0),
              duration: const Duration(milliseconds: 600),
              curve: Curves.elasticOut,
              builder: (_, v, child) => Transform.scale(scale: v, child: child),
              child: Container(
                width: 110, height: 110,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF00E676), Color(0xFF00C853)],
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                  ),
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.4),
                      blurRadius: 32, offset: const Offset(0, 12),
                    ),
                  ],
                ),
                child: const Icon(Icons.check_rounded, color: Colors.black, size: 56),
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'Ariza yuborildi! 🎉',
              style: TextStyle(
                fontSize: 28, fontWeight: FontWeight.w900,
                color: dark ? Colors.white : const Color(0xFF0F172A),
                letterSpacing: -0.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            Text(
              "Arizangiz administrator tomonidan ko'rib chiqiladi. Tasdiqlanganingizdan so'ng tizimga kirishingiz mumkin.",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14, height: 1.6,
                color: dark ? Colors.grey.shade400 : Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.warning.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.warning.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.access_time_rounded, color: AppColors.warning, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Tasdiqlash odatda 1–2 soat ichida bajariladi.',
                      style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w700,
                        color: dark ? Colors.orange.shade300 : const Color(0xFFB45309),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36),
            _GradientButton(
              label: 'Kirish sahifasiga qaytish',
              icon: Icons.arrow_back_rounded,
              onTap: () => Navigator.pop(context),
            ),
          ],
        ),
      ),
    );
  }

  // ── Form ─────────────────────────────────────────────────────────────────────

  Widget _formView(bool dark) {
    return SingleChildScrollView(
      key: const ValueKey('form'),
      padding: const EdgeInsets.fromLTRB(20, 56, 20, 32),
      child: SlideTransition(
        position: _slide,
        child: FadeTransition(
          opacity: _fade,
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Title
                const SizedBox(height: 8),
                Text(
                  "Ro'yxatdan o'tish",
                  style: TextStyle(
                    fontSize: 28, fontWeight: FontWeight.w900,
                    color: dark ? Colors.white : const Color(0xFF0F172A),
                    letterSpacing: -1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Ma'lumotlarni to'ldiring va ariza qoldiring",
                  style: TextStyle(fontSize: 13, color: dark ? Colors.grey.shade400 : Colors.grey.shade500),
                ),
                const SizedBox(height: 28),

                // Personal info card
                _SectionCard(
                  dark: dark,
                  icon: Icons.person_rounded,
                  iconColor: AppColors.info,
                  title: "Shaxsiy ma'lumotlar",
                  children: [
                    _Field(
                      controller: _nameCtr, dark: dark,
                      label: 'Ism Familya', hint: "To'liq ism familya",
                      icon: Icons.person_outline_rounded,
                      validator: (v) => v!.trim().isEmpty ? 'Ism familyangizni kiriting' : null,
                    ),
                    const SizedBox(height: 14),
                    _Field(
                      controller: _phoneCtr, dark: dark,
                      label: 'Telefon raqami', hint: '+998 (90) 000-00-00',
                      icon: Icons.phone_iphone_rounded,
                      keyboardType: TextInputType.phone,
                      validator: (v) => v!.trim().length < 9 ? "Raqam noto'g'ri" : null,
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Car info card
                _SectionCard(
                  dark: dark,
                  icon: Icons.directions_car_rounded,
                  iconColor: AppColors.accent,
                  title: 'Mashina tafsilotlari',
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _Field(
                            controller: _carMCtr, dark: dark,
                            label: 'Model', hint: 'Cobalt, Nexia...',
                            icon: Icons.directions_car_filled_outlined,
                            validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _Field(
                            controller: _carNCtr, dark: dark,
                            label: 'Davlat raqami', hint: '01A123AA',
                            icon: Icons.tag_rounded,
                            validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                // Password card
                _SectionCard(
                  dark: dark,
                  icon: Icons.lock_rounded,
                  iconColor: AppColors.purple,
                  title: 'Xavfsizlik paroli',
                  children: [
                    _Field(
                      controller: _passCtr, dark: dark,
                      label: 'Parol', hint: 'Kamida 6 ta belgi',
                      icon: Icons.lock_outline_rounded,
                      obscure: _obscure,
                      suffix: IconButton(
                        icon: Icon(
                          _obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                          size: 18, color: Colors.grey.shade400,
                        ),
                        onPressed: () => setState(() => _obscure = !_obscure),
                      ),
                      validator: (v) => v!.length < 6 ? "Kamida 6 ta belgi bo'lishi kerak" : null,
                    ),
                    const SizedBox(height: 14),
                    _Field(
                      controller: _pass2Ctr, dark: dark,
                      label: 'Parolni tasdiqlang', hint: 'Parolni qayta yozing',
                      icon: Icons.lock_outline_rounded,
                      obscure: true,
                      validator: (v) => v != _passCtr.text ? 'Parollar mos kelmadi' : null,
                    ),
                  ],
                ),

                const SizedBox(height: 28),
                _GradientButton(
                  label: 'Ariza yuborish',
                  icon: Icons.send_rounded,
                  loading: _loading,
                  onTap: _register,
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Reusable widgets ──────────────────────────────────────────────────────────

class _SectionCard extends StatelessWidget {
  final bool dark;
  final IconData icon;
  final Color iconColor;
  final String title;
  final List<Widget> children;
  const _SectionCard({
    required this.dark, required this.icon, required this.iconColor,
    required this.title, required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: dark ? Colors.white.withValues(alpha: 0.05) : Colors.white.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: dark ? Colors.white.withValues(alpha: 0.08) : Colors.white.withValues(alpha: 0.9),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: dark ? Colors.black.withValues(alpha: 0.3) : Colors.black.withValues(alpha: 0.04),
            blurRadius: 24, offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34, height: 34,
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, size: 18, color: iconColor),
              ),
              const SizedBox(width: 10),
              Text(
                title,
                style: TextStyle(
                  fontSize: 14, fontWeight: FontWeight.w800,
                  color: dark ? Colors.white : const Color(0xFF0F172A),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          ...children,
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  final TextEditingController controller;
  final bool dark;
  final String label;
  final String hint;
  final IconData icon;
  final TextInputType keyboardType;
  final bool obscure;
  final Widget? suffix;
  final String? Function(String?)? validator;

  const _Field({
    required this.controller, required this.dark,
    required this.label, required this.hint, required this.icon,
    this.keyboardType = TextInputType.text,
    this.obscure = false, this.suffix, this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12, fontWeight: FontWeight.w700,
            color: dark ? Colors.grey.shade400 : Colors.grey.shade600,
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: controller,
          keyboardType: keyboardType,
          obscureText: obscure,
          validator: validator,
          style: TextStyle(
            fontWeight: FontWeight.w600, fontSize: 15,
            color: dark ? Colors.white : const Color(0xFF0F172A),
          ),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: dark ? Colors.white.withValues(alpha: 0.06) : const Color(0xFFF8FAFC),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            prefixIcon: Padding(
              padding: const EdgeInsets.only(left: 14, right: 10),
              child: Icon(icon, size: 18, color: dark ? Colors.grey.shade500 : Colors.grey.shade400),
            ),
            prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
            suffixIcon: suffix,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: dark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(color: dark ? Colors.white.withValues(alpha: 0.08) : const Color(0xFFE2E8F0)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.primary, width: 2),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.danger),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.danger, width: 2),
            ),
            hintStyle: TextStyle(
              color: dark ? Colors.grey.shade600 : Colors.grey.shade400,
              fontSize: 13, fontWeight: FontWeight.normal,
            ),
          ),
        ),
      ],
    );
  }
}

class _GradientButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool loading;
  final VoidCallback onTap;
  const _GradientButton({required this.label, required this.icon, required this.onTap, this.loading = false});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: loading ? null : onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 56,
        decoration: BoxDecoration(
          gradient: loading ? null : const LinearGradient(
            colors: [Color(0xFF00E676), Color(0xFF00C853)],
            begin: Alignment.topLeft, end: Alignment.bottomRight,
          ),
          color: loading ? Colors.grey.shade300 : null,
          borderRadius: BorderRadius.circular(18),
          boxShadow: loading ? [] : [
            BoxShadow(
              color: AppColors.primary.withValues(alpha: 0.4),
              blurRadius: 20, offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Center(
          child: loading
              ? const SizedBox(width: 24, height: 24,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
              : Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(label, style: const TextStyle(
                      fontSize: 16, fontWeight: FontWeight.w900,
                      color: Colors.black, letterSpacing: 0.2,
                    )),
                    const SizedBox(width: 10),
                    Icon(icon, color: Colors.black, size: 18),
                  ],
                ),
        ),
      ),
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

class _RegBgPainter extends CustomPainter {
  final double t;
  final bool dark;
  _RegBgPainter(this.t, this.dark);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      Paint()..color = dark ? const Color(0xFF0B0D13) : const Color(0xFFF0FDF4),
    );
    final blobs = <(double, double, double, Color, double)>[
      (size.width * 0.1,  size.height * 0.15, 160.0, AppColors.accent,  0.05),
      (size.width * 0.9,  size.height * 0.5,  140.0, AppColors.primary, 0.05),
      (size.width * 0.4,  size.height * 0.85, 180.0, AppColors.primary, 0.04),
    ];
    for (final b in blobs) {
      final dx = b.$1 + sin(t * pi * 2) * 18;
      final dy = b.$2 + cos(t * pi * 2) * 14;
      final paint = Paint()
        ..shader = RadialGradient(
          colors: [b.$4.withValues(alpha: b.$5), b.$4.withValues(alpha: 0)],
        ).createShader(Rect.fromCircle(center: Offset(dx, dy), radius: b.$3));
      canvas.drawCircle(Offset(dx, dy), b.$3, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _RegBgPainter old) => old.t != t;
}
