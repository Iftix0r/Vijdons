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
    with SingleTickerProviderStateMixin {
  final _formKey  = GlobalKey<FormState>();
  final _phoneCtr = TextEditingController(text: '+998');
  final _passCtr  = TextEditingController();
  bool _loading   = false;
  bool _obscure   = true;

  late final AnimationController _ac;
  late final Animation<double>   _fade;
  late final Animation<Offset>   _slide;

  @override
  void initState() {
    super.initState();
    _ac    = AnimationController(vsync: this, duration: const Duration(milliseconds: 700));
    _fade  = CurvedAnimation(parent: _ac, curve: Curves.easeOut);
    _slide = Tween<Offset>(begin: const Offset(0, 0.05), end: Offset.zero)
        .animate(CurvedAnimation(parent: _ac, curve: Curves.easeOutCubic));
    _ac.forward();
  }

  @override
  void dispose() {
    _ac.dispose();
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
        transitionDuration: const Duration(milliseconds: 400),
      ));
    } on ApiException catch (e) {
      HapticFeedback.vibrate();
      _snack(e.message);
    } catch (_) {
      HapticFeedback.vibrate();
      _snack('Internet aloqasini tekshiring.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(
        content: Text(msg, style: const TextStyle(fontWeight: FontWeight.w700)),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ));
  }

  @override
  Widget build(BuildContext context) {
    // Yandex uslubi: har doim qora fon
    const bg = AppColors.bgDark;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.bgDark,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
      child: Scaffold(
        backgroundColor: bg,
        body: FadeTransition(
          opacity: _fade,
          child: SlideTransition(
            position: _slide,
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          SizedBox(height: MediaQuery.of(context).padding.top + 48),

                          // ── Logo ──────────────────────────────────────────
                          _logoBox(),
                          const SizedBox(height: 32),

                          // ── Title ─────────────────────────────────────────
                          const Text(
                            'Kirish',
                            style: TextStyle(
                              fontSize: 34, fontWeight: FontWeight.w900,
                              color: Colors.white, letterSpacing: -1.2,
                            ),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Haydovchi hisobingizga kiring',
                            style: TextStyle(
                              fontSize: 15, color: AppColors.textSecondaryDark,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 40),

                          // ── Phone ─────────────────────────────────────────
                          _darkLabel('Telefon raqami'),
                          const SizedBox(height: 10),
                          _darkField(
                            controller: _phoneCtr,
                            hint: '+998 90 000 00 00',
                            icon: Icons.phone_iphone_rounded,
                            keyboardType: TextInputType.phone,
                            validator: (v) =>
                                v!.trim().length < 9 ? "Noto'g'ri raqam" : null,
                          ),
                          const SizedBox(height: 20),

                          // ── Password ──────────────────────────────────────
                          _darkLabel('Parol'),
                          const SizedBox(height: 10),
                          _darkField(
                            controller: _passCtr,
                            hint: '••••••••',
                            icon: Icons.lock_outline_rounded,
                            obscure: _obscure,
                            onSubmitted: (_) => _login(),
                            suffix: GestureDetector(
                              onTap: () => setState(() => _obscure = !_obscure),
                              child: Icon(
                                _obscure
                                    ? Icons.visibility_off_outlined
                                    : Icons.visibility_outlined,
                                size: 20, color: AppColors.textSecondaryDark,
                              ),
                            ),
                            validator: (v) =>
                                v!.length < 6 ? 'Kamida 6 ta belgi' : null,
                          ),
                          const SizedBox(height: 32),
                        ],
                      ),
                    ),
                  ),

                  // ── Bottom actions ────────────────────────────────────────
                  Padding(
                    padding: EdgeInsets.fromLTRB(
                        24, 0, 24, MediaQuery.of(context).padding.bottom + 28),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Login button
                        SizedBox(
                          height: 58,
                          child: ElevatedButton(
                            onPressed: _loading ? null : _login,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primary,
                              foregroundColor: AppColors.textPrimary,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14)),
                              elevation: 0,
                              disabledBackgroundColor:
                                  AppColors.primary.withValues(alpha: 0.5),
                            ),
                            child: _loading
                                ? const SizedBox(
                                    width: 22, height: 22,
                                    child: CircularProgressIndicator(
                                        color: AppColors.textPrimary,
                                        strokeWidth: 2.5))
                                : const Text(
                                    'Kirish',
                                    style: TextStyle(
                                        fontSize: 17,
                                        fontWeight: FontWeight.w900),
                                  ),
                          ),
                        ),
                        const SizedBox(height: 14),

                        // Register link
                        SizedBox(
                          height: 52,
                          child: OutlinedButton(
                            onPressed: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (_) => const RegisterScreen())),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.white,
                              side: const BorderSide(
                                  color: AppColors.borderDark, width: 1.5),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14)),
                            ),
                            child: const Text(
                              "Ro'yxatdan o'tish",
                              style: TextStyle(
                                  fontSize: 15, fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _logoBox() {
    return Container(
      width: 76, height: 76,
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(22),
      ),
      child: const Center(
        child: Icon(Icons.local_taxi_rounded,
            color: AppColors.textPrimary, size: 40),
      ),
    );
  }

  Widget _darkLabel(String text) => Text(
    text,
    style: TextStyle(
      fontSize: 13, fontWeight: FontWeight.w700,
      color: Colors.grey.shade400,
    ),
  );

  Widget _darkField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    TextInputType keyboardType = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    ValueChanged<String>? onSubmitted,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      obscureText: obscure,
      onFieldSubmitted: onSubmitted,
      validator: validator,
      style: const TextStyle(
        fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white,
      ),
      decoration: InputDecoration(
        hintText: hint,
        filled: true,
        fillColor: AppColors.surfaceDark,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        prefixIcon: Padding(
          padding: const EdgeInsets.only(left: 14, right: 12),
          child: Icon(icon, size: 20, color: AppColors.textSecondaryDark),
        ),
        prefixIconConstraints:
            const BoxConstraints(minWidth: 0, minHeight: 0),
        suffixIcon: suffix != null
            ? Padding(
                padding: const EdgeInsets.only(right: 14), child: suffix)
            : null,
        suffixIconConstraints:
            const BoxConstraints(minWidth: 0, minHeight: 0),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.borderDark),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.borderDark),
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
        hintStyle: const TextStyle(
            color: AppColors.textSecondaryDark, fontSize: 15),
        errorStyle: const TextStyle(color: AppColors.danger, fontSize: 12),
      ),
    );
  }
}
