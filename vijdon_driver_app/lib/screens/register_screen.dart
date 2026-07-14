import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey    = GlobalKey<FormState>();
  final _nameCtr    = TextEditingController();
  final _phoneCtr   = TextEditingController();
  final _carMCtr    = TextEditingController();
  final _carNCtr    = TextEditingController();
  final _passCtr    = TextEditingController();
  final _pass2Ctr   = TextEditingController();
  bool _loading     = false;
  bool _obscure     = true;
  int _step         = 0; // 0 = form, 1 = success

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await ApiService.register({
        'full_name':    _nameCtr.text.trim(),
        'phone_number': _phoneCtr.text.trim(),
        'car_model':    _carMCtr.text.trim(),
        'car_number':   _carNCtr.text.trim(),
        'password':     _passCtr.text,
      });
      setState(() => _step = 1);
    } on ApiException catch (e) {
      _showError(e.message);
    } catch (_) {
      _showError('Server bilan ulanishda xatolik.');
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
      appBar: AppBar(title: const Text("Ro'yxatdan o'tish")),
      body: SafeArea(
        child: _step == 1 ? _successView() : _formView(),
      ),
    );
  }

  Widget _successView() => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 80, height: 80,
            decoration: BoxDecoration(color: AppTheme.success.withOpacity(.1), borderRadius: BorderRadius.circular(24)),
            child: const Icon(Icons.check_circle_outline_rounded, color: AppTheme.success, size: 48),
          ),
          const SizedBox(height: 20),
          const Text("Muvaffaqiyatli ro'yxatdan o'tdingiz!", style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
          const SizedBox(height: 12),
          const Text(
            "Arizangiz admin ko'rib chiqmoqda.\nAdmin tasdiqlagan so'ng hisobingizga kirishingiz mumkin bo'ladi.",
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey, height: 1.5),
          ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                elevation: 0,
              ),
              child: const Text('Kirish sahifasiga qaytish', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _formView() => SingleChildScrollView(
    padding: const EdgeInsets.all(24),
    child: Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text("Ma'lumotlaringizni kiriting", style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
          const Text("Admin tekshirganidan so'ng hisobingiz faollashadi", style: TextStyle(fontSize: 13, color: Colors.grey)),
          const SizedBox(height: 24),

          _field(controller: _nameCtr, label: "To'liq ism familya", hint: 'Ism Familya', icon: Icons.person_outline,
              validator: (v) => v!.trim().isEmpty ? 'Ism kiriting' : null),
          const SizedBox(height: 14),
          _field(controller: _phoneCtr, label: 'Telefon raqami', hint: '+998 90 000 00 00', icon: Icons.phone_outlined,
              type: TextInputType.phone, validator: (v) => v!.trim().length < 9 ? 'Telefon kiriting' : null),
          const SizedBox(height: 14),
          _field(controller: _carMCtr, label: 'Mashina modeli', hint: 'Chevrolet Cobalt', icon: Icons.directions_car_outlined,
              validator: (v) => v!.trim().isEmpty ? 'Mashina modelini kiriting' : null),
          const SizedBox(height: 14),
          _field(controller: _carNCtr, label: 'Mashina davlat raqami', hint: '01 A 123 AA', icon: Icons.confirmation_number_outlined,
              validator: (v) => v!.trim().isEmpty ? 'Mashina raqamini kiriting' : null),
          const SizedBox(height: 14),
          _field(controller: _passCtr, label: 'Parol', hint: '••••••••', icon: Icons.lock_outline, obscure: _obscure,
              suffixIcon: IconButton(
                icon: Icon(_obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
              validator: (v) => v!.length < 6 ? 'Parol kamida 6 ta belgi' : null),
          const SizedBox(height: 14),
          _field(controller: _pass2Ctr, label: 'Parolni tasdiqlang', hint: '••••••••', icon: Icons.lock_outline, obscure: true,
              validator: (v) => v != _passCtr.text ? 'Parollar mos emas' : null),
          const SizedBox(height: 28),

          SizedBox(
            height: 52,
            child: ElevatedButton(
              onPressed: _loading ? null : _register,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                elevation: 0,
              ),
              child: _loading
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                  : const Text("Ro'yxatdan o'tish", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _field({
    required TextEditingController controller,
    required String label, required String hint, required IconData icon,
    TextInputType type = TextInputType.text,
    String? Function(String?)? validator,
    bool obscure = false,
    Widget? suffixIcon,
  }) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey)),
      const SizedBox(height: 6),
      TextFormField(
        controller: controller,
        keyboardType: type,
        obscureText: obscure,
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: Icon(icon, size: 20),
          suffixIcon: suffixIcon,
          filled: true,
          fillColor: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(.4),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: AppTheme.primary, width: 2)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
        validator: validator,
      ),
    ],
  );

  @override
  void dispose() {
    for (final c in [_nameCtr, _phoneCtr, _carMCtr, _carNCtr, _passCtr, _pass2Ctr]) c.dispose();
    super.dispose();
  }
}
