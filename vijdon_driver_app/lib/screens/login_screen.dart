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

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final _formKey  = GlobalKey<FormState>();
  final _phoneCtr = TextEditingController(text: '+998');
  final _passCtr  = TextEditingController();
  bool _loading   = false;
  bool _obscure   = true;

  late AnimationController _animCtrl;
  late Animation<double>   _fadeAnim;
  late Animation<Offset>   _slideAnim;

  @override
  void initState() {
    super.initState();
    _animCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _fadeAnim  = CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(begin: const Offset(0, .06), end: Offset.zero)
        .animate(CurvedAnimation(parent: _animCtrl, curve: Curves.easeOut));
    _animCtrl.forward();
  }

  @override
  void dispose() {
    _animCtrl.dispose();
    _phoneCtr.dispose();
    _passCtr.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    HapticFeedback.lightImpact();
    setState(() => _loading = true);
    try {
      await ApiService.login(_phoneCtr.text.trim(), _passCtr.text);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      Navigator.pushReplacement(context, _fadeRoute(const HomeScreen()));
    } on ApiException catch (e) {
      HapticFeedback.vibrate();
      _showError(e.message);
    } catch (_) {
      HapticFeedback.vibrate();
      _showError('Internet aloqasini tekshiring.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Row(children: [
        const Icon(Icons.error_outline_rounded, color: Colors.white, size: 18),
        const SizedBox(width: 10),
        Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600))),
      ]),
      backgroundColor: AppTheme.danger,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      margin: const EdgeInsets.all(16),
    ));
  }

  PageRouteBuilder _fadeRoute(Widget page) => PageRouteBuilder(
    pageBuilder: (_, __, ___) => page,
    transitionsBuilder: (_, a, __, c) => FadeTransition(opacity: a, child: c),
    transitionDuration: const Duration(milliseconds: 400),
  );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: isDark
              ? const LinearGradient(colors: [Color(0xFF0F172A), Color(0xFF1E293B)], begin: Alignment.topLeft, end: Alignment.bottomRight)
              : const LinearGradient(colors: [Color(0xFFFFFBEB), Color(0xFFF8FAFC)], begin: Alignment.topLeft, end: Alignment.bottomRight),
        ),
        child: SafeArea(
          child: FadeTransition(
            opacity: _fadeAnim,
            child: SlideTransition(
              position: _slideAnim,
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 28),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const SizedBox(height: 56),

                      // ── Logo ──────────────────────────────────────────────
                      Center(
                        child: Column(
                          children: [
                            Container(
                              width: 84, height: 84,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFFFCD34D), Color(0xFFF59E0B)],
                                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                                ),
                                borderRadius: BorderRadius.circular(26),
                                boxShadow: [
                                  BoxShadow(color: AppTheme.primary.withValues(alpha: 0.4), blurRadius: 24, offset: const Offset(0, 10)),
                                ],
                              ),
                              child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 44),
                            ),
                            const SizedBox(height: 18),
                            const Text('VijdonTaxi',
                                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: -0.8)),
                            const SizedBox(height: 4),
                            Text('Haydovchi ilovasi',
                                style: TextStyle(fontSize: 14, color: Colors.grey.shade500, fontWeight: FontWeight.w500)),
                          ],
                        ),
                      ),

                      const SizedBox(height: 44),

                      // ── Phone ─────────────────────────────────────────────
                      _fieldLabel('Telefon raqami'),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _phoneCtr,
                        keyboardType: TextInputType.phone,
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                        decoration: _dec(hint: '+998 90 000 00 00', icon: Icons.phone_rounded),
                        validator: (v) => (v == null || v.trim().length < 9) ? 'To\'g\'ri telefon raqam kiriting' : null,
                      ),
                      const SizedBox(height: 18),

                      // ── Password ──────────────────────────────────────────
                      _fieldLabel('Parol'),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _passCtr,
                        obscureText: _obscure,
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                        decoration: _dec(hint: '••••••••', icon: Icons.lock_rounded).copyWith(
                          suffixIcon: IconButton(
                            icon: Icon(_obscure ? Icons.visibility_off_rounded : Icons.visibility_rounded, size: 20),
                            onPressed: () => setState(() => _obscure = !_obscure),
                            color: Colors.grey.shade400,
                          ),
                        ),
                        onFieldSubmitted: (_) => _login(),
                        validator: (v) => (v == null || v.length < 6) ? 'Parol kamida 6 ta belgi' : null,
                      ),
                      const SizedBox(height: 32),

                      // ── Login button ──────────────────────────────────────
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        height: 54,
                        child: ElevatedButton(
                          onPressed: _loading ? null : _login,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primary,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            elevation: _loading ? 0 : 4,
                            shadowColor: AppTheme.primary.withValues(alpha: 0.4),
                          ),
                          child: _loading
                              ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                              : const Text('Kirish', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // ── Divider ───────────────────────────────────────────
                      Row(children: [
                        Expanded(child: Divider(color: Colors.grey.withValues(alpha: 0.25))),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text('yoki', style: TextStyle(color: Colors.grey.shade400, fontSize: 13)),
                        ),
                        Expanded(child: Divider(color: Colors.grey.withValues(alpha: 0.25))),
                      ]),
                      const SizedBox(height: 20),

                      // ── Register ──────────────────────────────────────────
                      OutlinedButton.icon(
                        onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RegisterScreen())),
                        icon: const Icon(Icons.person_add_rounded, size: 18),
                        label: const Text("Ro'yxatdan o'tish", style: TextStyle(fontWeight: FontWeight.bold)),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(54),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                          side: BorderSide(color: AppTheme.primary.withValues(alpha: 0.5)),
                          foregroundColor: AppTheme.primary,
                        ),
                      ),
                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _fieldLabel(String t) => Text(
    t,
    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 0.2),
  );

  InputDecoration _dec({required String hint, required IconData icon}) => InputDecoration(
    hintText: hint,
    hintStyle: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.normal),
    prefixIcon: Icon(icon, size: 20, color: Colors.grey.shade400),
    filled: true,
    fillColor: Theme.of(context).brightness == Brightness.dark
        ? const Color(0xFF1E293B)
        : Colors.white,
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.2))),
    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.2))),
    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppTheme.primary, width: 2)),
    errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppTheme.danger)),
    focusedErrorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppTheme.danger, width: 2)),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
  );
}
