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
    _ac    = AnimationController(vsync: this, duration: const Duration(milliseconds: 800));
    _fade  = CurvedAnimation(parent: _ac, curve: Curves.easeOut);
    _slide = Tween<Offset>(begin: const Offset(0, 0.08), end: Offset.zero)
        .animate(CurvedAnimation(parent: _ac, curve: const Interval(0.1, 1.0, curve: Curves.easeOutCubic)));
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
      Navigator.pushReplacement(context,
          PageRouteBuilder(
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
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: dark
              ? const LinearGradient(
                  colors: [Color(0xFF030605), Color(0xFF0A110E)],
                  begin: Alignment.topCenter, end: Alignment.bottomCenter)
              : const LinearGradient(
                  colors: [Color(0xFFECFDF5), Color(0xFFF8FAFC)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              child: FadeTransition(
                opacity: _fade,
                child: SlideTransition(
                  position: _slide,
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _logo(dark),
                        const SizedBox(height: 40),
                        
                        // Form Card
                        Container(
                          padding: const EdgeInsets.all(24),
                          decoration: BoxDecoration(
                            color: dark ? AppColors.cardDark : Colors.white,
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: dark ? 0.3 : 0.04),
                                blurRadius: 20,
                                offset: const Offset(0, 10),
                              )
                            ],
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _sectionTitle('TELEFON RAQAMI', dark),
                              const SizedBox(height: 8),
                              _phoneField(dark),
                              const SizedBox(height: 20),
                              _sectionTitle('PAROL', dark),
                              const SizedBox(height: 8),
                              _passwordField(dark),
                              const SizedBox(height: 28),
                              _loginBtn(),
                            ],
                          ),
                        ),
                        const SizedBox(height: 24),
                        _divider(dark),
                        const SizedBox(height: 24),
                        _registerBtn(),
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

  Widget _logo(bool dark) {
    return Column(
      children: [
        Container(
          width: 90, height: 90,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF34D399), Color(0xFF10B981), Color(0xFF059669)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(26),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary.withValues(alpha: 0.35),
                blurRadius: 24,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: const Center(
            child: Icon(Icons.local_taxi_rounded, color: Colors.white, size: 48),
          ),
        ),
        const SizedBox(height: 18),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Vijdon',
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w900,
                color: dark ? Colors.white : AppColors.textPrimary,
                letterSpacing: -1.0,
              ),
            ),
            const Text(
              'Taxi',
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w900,
                color: AppColors.primary,
                letterSpacing: -1.0,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          'Haydovchi mobil boshqaruvi',
          style: TextStyle(
            fontSize: 13,
            color: dark ? Colors.grey.shade400 : AppColors.textSecondary,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  Widget _sectionTitle(String label, bool dark) {
    return Text(
      label,
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w800,
        color: dark ? Colors.grey.shade400 : AppColors.textSecondary,
        letterSpacing: 1.2,
      ),
    );
  }

  Widget _phoneField(bool dark) {
    return TextFormField(
      controller: _phoneCtr,
      keyboardType: TextInputType.phone,
      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, letterSpacing: 0.5),
      decoration: InputDecoration(
        hintText: '+998 (90) 000-00-00',
        prefixIcon: Icon(Icons.phone_iphone_rounded, size: 20, color: dark ? Colors.grey.shade500 : Colors.grey.shade400),
      ),
      validator: (v) {
        if (v == null || v.trim().isEmpty) return 'Raqam kiriting';
        if (v.trim().length < 9) return 'Raqam noto\'g\'ri';
        return null;
      },
    );
  }

  Widget _passwordField(bool dark) {
    return TextFormField(
      controller: _passCtr,
      obscureText: _obscure,
      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, letterSpacing: 1.0),
      decoration: InputDecoration(
        hintText: '••••••••',
        prefixIcon: Icon(Icons.lock_outline_rounded, size: 20, color: dark ? Colors.grey.shade500 : Colors.grey.shade400),
        suffixIcon: IconButton(
          icon: Icon(
            _obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
            size: 20,
            color: dark ? Colors.grey.shade500 : Colors.grey.shade400,
          ),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
      onFieldSubmitted: (_) => _login(),
      validator: (v) => (v == null || v.length < 6) ? 'Kamida 6 ta belgi' : null,
    );
  }

  Widget _loginBtn() {
    return SizedBox(
      height: 54,
      child: ElevatedButton(
        onPressed: _loading ? null : _login,
        style: ElevatedButton.styleFrom(
          shadowColor: AppColors.primary.withValues(alpha: 0.4),
          elevation: 4,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: _loading
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5),
              )
            : const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Tizimga kirish', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, size: 18),
                ],
              ),
      ),
    );
  }

  Widget _divider(bool dark) {
    final dividerColor = dark ? AppColors.borderDark : AppColors.borderLight;
    return Row(
      children: [
        Expanded(child: Divider(color: dividerColor)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            'Hali hisobingiz yo\'qmi?',
            style: TextStyle(
              color: dark ? Colors.grey.shade500 : Colors.grey.shade500,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(child: Divider(color: dividerColor)),
      ],
    );
  }

  Widget _registerBtn() {
    return SizedBox(
      height: 52,
      child: OutlinedButton.icon(
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const RegisterScreen()),
        ),
        icon: const Icon(Icons.person_add_rounded, size: 18),
        label: const Text("Haydovchi bo'lib ro'yxatdan o'tish", style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
        style: OutlinedButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
      ),
    );
  }
}
