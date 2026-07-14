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
    _slide = Tween<Offset>(begin: const Offset(0, .05), end: Offset.zero)
        .animate(CurvedAnimation(parent: _ac, curve: Curves.easeOutCubic));
    _ac.forward();
  }

  @override
  void dispose() { _ac.dispose(); _phoneCtr.dispose(); _passCtr.dispose(); super.dispose(); }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    HapticFeedback.lightImpact();
    setState(() => _loading = true);
    try {
      await ApiService.login(_phoneCtr.text.trim(), _passCtr.text);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      Navigator.pushReplacement(context,
          PageRouteBuilder(
            pageBuilder: (_, __, ___) => const HomeScreen(),
            transitionsBuilder: (_, a, __, c) => FadeTransition(opacity: a, child: c),
            transitionDuration: const Duration(milliseconds: 450),
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
              color: Colors.white, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
        backgroundColor: error ? AppColors.danger : AppColors.success,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        margin: const EdgeInsets.all(16),
        duration: const Duration(seconds: 3),
      ));
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: dark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
      child: Scaffold(
        body: Container(
          decoration: BoxDecoration(
            gradient: dark
                ? const LinearGradient(
                    colors: [Color(0xFF0A0F1E), Color(0xFF111827)],
                    begin: Alignment.topCenter, end: Alignment.bottomCenter)
                : const LinearGradient(
                    colors: [Color(0xFFFFFBEB), Color(0xFFF1F5F9)],
                    begin: Alignment.topLeft, end: Alignment.bottomRight),
          ),
          child: SafeArea(
            child: FadeTransition(
              opacity: _fade,
              child: SlideTransition(
                position: _slide,
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 28),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: 60),
                        _logo(),
                        const SizedBox(height: 50),
                        _sectionTitle('Telefon raqami'),
                        const SizedBox(height: 8),
                        _input(
                          controller: _phoneCtr,
                          hint: '+998 90 000 00 00',
                          icon: Icons.phone_rounded,
                          type: TextInputType.phone,
                          validator: (v) => (v == null || v.trim().length < 9) ? 'To\'g\'ri raqam kiriting' : null,
                        ),
                        const SizedBox(height: 20),
                        _sectionTitle('Parol'),
                        const SizedBox(height: 8),
                        _input(
                          controller: _passCtr,
                          hint: '••••••••',
                          icon: Icons.lock_rounded,
                          obscure: _obscure,
                          suffix: IconButton(
                            icon: Icon(
                              _obscure ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                              size: 20, color: Colors.grey.shade400,
                            ),
                            onPressed: () => setState(() => _obscure = !_obscure),
                          ),
                          onSubmit: (_) => _login(),
                          validator: (v) => (v == null || v.length < 6) ? 'Kamida 6 ta belgi' : null,
                        ),
                        const SizedBox(height: 36),
                        _loginBtn(),
                        const SizedBox(height: 20),
                        _divider(),
                        const SizedBox(height: 20),
                        _registerBtn(),
                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _logo() {
    return Column(
      children: [
        Container(
          width: 88, height: 88,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFFCD34D), Color(0xFFF59E0B)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(28),
            boxShadow: [
              BoxShadow(color: AppColors.amber.withValues(alpha: 0.45), blurRadius: 28, offset: const Offset(0, 12)),
            ],
          ),
          child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 46),
        ),
        const SizedBox(height: 20),
        const Text('VijdonTaxi',
            style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: -1.0)),
        const SizedBox(height: 6),
        Text('Haydovchi ilovasi',
            style: TextStyle(fontSize: 15, color: Colors.grey.shade500, fontWeight: FontWeight.w500)),
      ],
    );
  }

  Widget _sectionTitle(String t) => Text(
    t,
    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 0.3),
  );

  Widget _input({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    TextInputType type = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    void Function(String)? onSubmit,
    String? Function(String?)? validator,
  }) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return TextFormField(
      controller: controller,
      keyboardType: type,
      obscureText: obscure,
      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
      onFieldSubmitted: onSubmit,
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.normal, fontSize: 14),
        prefixIcon: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          child: Icon(icon, size: 20, color: Colors.grey.shade400),
        ),
        suffixIcon: suffix,
        filled: true,
        fillColor: dark ? AppColors.surfaceDark : Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.18)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.18)),
        ),
        focusedBorder: const OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          borderSide: BorderSide(color: AppColors.amber, width: 2),
        ),
        errorBorder: const OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          borderSide: BorderSide(color: AppColors.danger),
        ),
        focusedErrorBorder: const OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          borderSide: BorderSide(color: AppColors.danger, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
      ),
      validator: validator,
    );
  }

  Widget _loginBtn() => SizedBox(
    height: 56,
    child: ElevatedButton(
      onPressed: _loading ? null : _login,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.amber,
        foregroundColor: Colors.white,
        disabledBackgroundColor: AppColors.amber.withValues(alpha: 0.6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        elevation: 0,
        shadowColor: AppColors.amber.withValues(alpha: 0.5),
      ),
      child: _loading
          ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
          : const Text('Kirish', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
    ),
  );

  Widget _divider() => Row(children: [
    Expanded(child: Divider(color: Colors.grey.withValues(alpha: 0.2))),
    Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Text('yoki', style: TextStyle(color: Colors.grey.shade400, fontSize: 13)),
    ),
    Expanded(child: Divider(color: Colors.grey.withValues(alpha: 0.2))),
  ]);

  Widget _registerBtn() => SizedBox(
    height: 56,
    child: OutlinedButton.icon(
      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RegisterScreen())),
      icon: const Icon(Icons.person_add_alt_1_rounded, size: 18),
      label: const Text("Ro'yxatdan o'tish", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
      style: OutlinedButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        side: BorderSide(color: AppColors.amber.withValues(alpha: 0.6), width: 1.5),
        foregroundColor: AppColors.amber,
      ),
    ),
  );
}
