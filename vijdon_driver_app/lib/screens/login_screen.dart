import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import 'register_screen.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey   = GlobalKey<FormState>();
  final _phoneCtr  = TextEditingController();
  final _passCtr   = TextEditingController();
  bool _loading    = false;
  bool _obscure    = true;

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await ApiService.login(_phoneCtr.text.trim(), _passCtr.text);
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const HomeScreen()));
    } on ApiException catch (e) {
      _showError(e.message);
    } catch (_) {
      _showError('Server bilan ulanishda xatolik. Internetni tekshiring.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppTheme.danger),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 40),
                // Logo
                Center(
                  child: Container(
                    width: 80, height: 80,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFFBBF24), Color(0xFFF59E0B)],
                        begin: Alignment.topLeft, end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [BoxShadow(color: AppTheme.primary.withOpacity(.3), blurRadius: 20, offset: const Offset(0, 8))],
                    ),
                    child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 42),
                  ),
                ),
                const SizedBox(height: 20),
                const Text('VijdonTaxi', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: -0.5)),
                const Text('Haydovchi ilovasi', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: Colors.grey)),
                const SizedBox(height: 40),

                // Phone
                _label('Telefon raqami'),
                const SizedBox(height: 6),
                TextFormField(
                  controller: _phoneCtr,
                  keyboardType: TextInputType.phone,
                  decoration: _inputDec(hint: '+998 90 000 00 00', icon: Icons.phone_outlined),
                  validator: (v) => (v == null || v.trim().length < 9) ? 'Telefon raqam kiriting' : null,
                ),
                const SizedBox(height: 16),

                // Password
                _label('Parol'),
                const SizedBox(height: 6),
                TextFormField(
                  controller: _passCtr,
                  obscureText: _obscure,
                  decoration: _inputDec(hint: '••••••••', icon: Icons.lock_outline).copyWith(
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  validator: (v) => (v == null || v.length < 6) ? 'Parol kamida 6 ta belgi' : null,
                ),
                const SizedBox(height: 28),

                // Login button
                SizedBox(
                  height: 52,
                  child: ElevatedButton(
                    onPressed: _loading ? null : _login,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      elevation: 0,
                    ),
                    child: _loading
                        ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                        : const Text('Kirish', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(height: 20),

                // Register link
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text("Hisobingiz yo'qmi? ", style: TextStyle(color: Colors.grey)),
                    GestureDetector(
                      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const RegisterScreen())),
                      child: const Text("Ro'yxatdan o'tish", style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _label(String t) => Text(t, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey));

  InputDecoration _inputDec({required String hint, required IconData icon}) => InputDecoration(
    hintText: hint,
    prefixIcon: Icon(icon, size: 20),
    filled: true,
    fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(.4),
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppTheme.primary, width: 2)),
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
  );

  @override
  void dispose() { _phoneCtr.dispose(); _passCtr.dispose(); super.dispose(); }
}
