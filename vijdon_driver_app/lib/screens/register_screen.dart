import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_service.dart';
import '../core/theme.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey  = GlobalKey<FormState>();
  final _nameCtr  = TextEditingController();
  final _phoneCtr = TextEditingController(text: '+998');
  final _carMCtr  = TextEditingController();
  final _carNCtr  = TextEditingController();
  final _passCtr  = TextEditingController();
  final _pass2Ctr = TextEditingController();
  bool _loading   = false;
  bool _obscure   = true;
  int  _step      = 0;

  @override
  void dispose() {
    for (final c in [_nameCtr, _phoneCtr, _carMCtr, _carNCtr, _passCtr, _pass2Ctr]) c.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
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
      setState(() => _step = 1);
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
          const Icon(Icons.error_outline_rounded, color: Colors.white, size: 18),
          const SizedBox(width: 10),
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        margin: const EdgeInsets.all(16),
      ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(_step == 0 ? "Ro'yxatdan o'tish" : '',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
        leading: _step == 0
            ? const BackButton()
            : const SizedBox.shrink(),
      ),
      body: SafeArea(
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          child: _step == 1 ? _successPage() : _formPage(),
        ),
      ),
    );
  }

  // ── Success ──────────────────────────────────────────────────────────────────

  Widget _successPage() => Center(
    key: const ValueKey('success'),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 36),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 96, height: 96,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF34D399), Color(0xFF10B981)]),
              borderRadius: BorderRadius.circular(30),
              boxShadow: [BoxShadow(color: AppColors.success.withValues(alpha: 0.4), blurRadius: 24, offset: const Offset(0, 10))],
            ),
            child: const Icon(Icons.check_rounded, color: Colors.white, size: 52),
          ),
          const SizedBox(height: 28),
          const Text("Ariza yuborildi!",
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900, letterSpacing: -0.5),
              textAlign: TextAlign.center),
          const SizedBox(height: 12),
          Text(
            "Arizangiz admin tomonidan ko'rib chiqiladi.\nTasdiqlangandan so'ng tizimga kirishingiz mumkin.",
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 14, color: Colors.grey.shade500, height: 1.6),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.warning.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.access_time_rounded, color: AppColors.warning, size: 16),
                const SizedBox(width: 8),
                Text('Odatda 1-24 soat ichida tasdiqlanadi',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w500)),
              ],
            ),
          ),
          const SizedBox(height: 36),
          SizedBox(
            width: double.infinity, height: 56,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.amber,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                elevation: 0,
              ),
              child: const Text('Kirish sahifasiga qaytish',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            ),
          ),
        ],
      ),
    ),
  );

  // ── Form ─────────────────────────────────────────────────────────────────────

  Widget _formPage() => SingleChildScrollView(
    key: const ValueKey('form'),
    padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
    child: Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [AppColors.amber.withValues(alpha: 0.12), AppColors.amber.withValues(alpha: 0.04)],
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.amber.withValues(alpha: 0.2)),
            ),
            child: Row(
              children: [
                Container(
                  width: 42, height: 42,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFFFCD34D), Color(0xFFF59E0B)]),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 22),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("Haydovchi sifatida qo'shiling",
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      Text("Barcha maydonlarni to'ldiring",
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          _sectionLabel('Shaxsiy ma\'lumotlar'),
          const SizedBox(height: 12),
          _field(_nameCtr,  'To\'liq ism familya', 'Ism Familya', Icons.person_rounded,
              validator: (v) => v!.trim().isEmpty ? 'Ism kiriting' : null),
          const SizedBox(height: 12),
          _field(_phoneCtr, 'Telefon raqami', '+998 90 000 00 00', Icons.phone_rounded,
              type: TextInputType.phone,
              validator: (v) => v!.trim().length < 9 ? 'To\'g\'ri raqam kiriting' : null),

          const SizedBox(height: 20),
          _sectionLabel('Mashina ma\'lumotlari'),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _field(_carMCtr, 'Mashina modeli', 'Cobalt', Icons.directions_car_rounded,
                validator: (v) => v!.trim().isEmpty ? 'Kiriting' : null)),
            const SizedBox(width: 12),
            Expanded(child: _field(_carNCtr, 'Davlat raqami', '01A123AA', Icons.tag_rounded,
                validator: (v) => v!.trim().isEmpty ? 'Kiriting' : null)),
          ]),

          const SizedBox(height: 20),
          _sectionLabel('Parol'),
          const SizedBox(height: 12),
          _field(_passCtr, 'Parol', '••••••••', Icons.lock_rounded,
              obscure: _obscure,
              suffix: IconButton(
                icon: Icon(_obscure ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                    size: 20, color: Colors.grey.shade400),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
              validator: (v) => v!.length < 6 ? 'Kamida 6 ta belgi' : null),
          const SizedBox(height: 12),
          _field(_pass2Ctr, 'Parolni tasdiqlang', '••••••••', Icons.lock_rounded,
              obscure: true,
              validator: (v) => v != _passCtr.text ? 'Parollar mos emas' : null),

          const SizedBox(height: 32),
          SizedBox(
            height: 56,
            child: ElevatedButton(
              onPressed: _loading ? null : _register,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.amber,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                elevation: 0,
              ),
              child: _loading
                  ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                  : const Text("Ariza yuborish",
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
            ),
          ),
        ],
      ),
    ),
  );

  Widget _sectionLabel(String t) => Row(children: [
    Container(width: 3, height: 16, decoration: BoxDecoration(color: AppColors.amber, borderRadius: BorderRadius.circular(2))),
    const SizedBox(width: 8),
    Text(t, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: 0.2)),
  ]);

  Widget _field(
    TextEditingController ctrl, String label, String hint, IconData icon, {
    TextInputType type = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    String? Function(String?)? validator,
  }) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey.shade500)),
        const SizedBox(height: 6),
        TextFormField(
          controller: ctrl,
          keyboardType: type,
          obscureText: obscure,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.normal, fontSize: 13),
            prefixIcon: Icon(icon, size: 18, color: Colors.grey.shade400),
            suffixIcon: suffix,
            filled: true,
            fillColor: dark ? AppColors.surfaceDark : Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.18))),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: Colors.grey.withValues(alpha: 0.18))),
            focusedBorder: const OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(14)),
                borderSide: BorderSide(color: AppColors.amber, width: 2)),
            errorBorder: const OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(14)),
                borderSide: BorderSide(color: AppColors.danger)),
            focusedErrorBorder: const OutlineInputBorder(
                borderRadius: BorderRadius.all(Radius.circular(14)),
                borderSide: BorderSide(color: AppColors.danger, width: 2)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          ),
          validator: validator,
        ),
      ],
    );
  }
}
