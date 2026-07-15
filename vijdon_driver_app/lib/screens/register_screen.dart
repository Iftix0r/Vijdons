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
    for (final c in [_nameCtr, _phoneCtr, _carMCtr, _carNCtr, _passCtr, _pass2Ctr]) {
      c.dispose();
    }
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
    return Scaffold(
      appBar: AppBar(
        title: Text(_step == 0 ? "Ro'yxatdan o'tish" : '',
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18)),
        leading: _step == 0
            ? IconButton(
                icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 18),
                onPressed: () => Navigator.pop(context),
              )
            : const SizedBox.shrink(),
      ),
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
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 400),
            child: _step == 1 ? _successPage(dark) : _formPage(dark),
          ),
        ),
      ),
    );
  }

  // ── Success Page ─────────────────────────────────────────────────────────────

  Widget _successPage(bool dark) => Center(
    key: const ValueKey('success'),
    child: SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 100, height: 100,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF059669)]),
              borderRadius: BorderRadius.circular(30),
              boxShadow: [
                BoxShadow(
                  color: AppColors.success.withValues(alpha: 0.35),
                  blurRadius: 28,
                  offset: const Offset(0, 10),
                )
              ],
            ),
            child: const Center(
              child: Icon(Icons.check_rounded, color: Colors.white, size: 52),
            ),
          ),
          const SizedBox(height: 32),
          Text(
            "Ariza yuborildi!",
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w900,
              color: dark ? Colors.white : AppColors.textPrimary,
              letterSpacing: -0.5,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 14),
          Text(
            "Arizangiz administrator tomonidan ko'rib chiqiladi. Tasdiqlanganingizdan so'ng mobil ilovadan foydalanishingiz mumkin.",
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: dark ? Colors.grey.shade400 : AppColors.textSecondary,
              height: 1.6,
            ),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.warning.withValues(alpha: 0.25)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.access_time_filled_rounded, color: AppColors.warning, size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Tasdiqlash odatda 1-2 soat ichida bajariladi.',
                    style: TextStyle(
                      fontSize: 12,
                      color: dark ? Colors.grey.shade300 : const Color(0xFFB45309),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 40),
          SizedBox(
            width: double.infinity, height: 56,
            child: ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.arrow_back_rounded, size: 18),
                  SizedBox(width: 8),
                  Text('Kirish sahifasiga qaytish', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );

  // ── Form Page ────────────────────────────────────────────────────────────────

  Widget _formPage(bool dark) => SingleChildScrollView(
    key: const ValueKey('form'),
    padding: const EdgeInsets.fromLTRB(20, 10, 20, 32),
    child: Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header guide
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primary.withValues(alpha: dark ? 0.08 : 0.06),
                  AppColors.primary.withValues(alpha: dark ? 0.02 : 0.01)
                ],
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.primary.withValues(alpha: 0.15)),
            ),
            child: Row(
              children: [
                Container(
                  width: 44, height: 44,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF34D399), Color(0xFF10B981)]),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Center(
                    child: Icon(Icons.taxi_alert_rounded, color: Colors.white, size: 22),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        "Haydovchilik arizasi",
                        style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        "Ma'lumotlarni to'ldirib ariza qoldiring",
                        style: TextStyle(fontSize: 12, color: dark ? Colors.grey.shade400 : AppColors.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Shaxsiy ma'lumotlar
          _sectionHeader('SHAXSIY MA\'LUMOTLAR', dark),
          const SizedBox(height: 12),
          _field(_nameCtr, 'Ism Familya', 'To\'liq ism familya', Icons.person_outline_rounded, dark,
              validator: (v) => v!.trim().isEmpty ? 'Ism familyangizni kiriting' : null),
          const SizedBox(height: 12),
          _field(_phoneCtr, 'Telefon raqami', '+998 (90) 000-00-00', Icons.phone_iphone_rounded, dark,
              type: TextInputType.phone,
              validator: (v) => v!.trim().length < 9 ? 'Raqam noto\'g\'ri' : null),
          const SizedBox(height: 24),

          // Mashina ma'lumotlari
          _sectionHeader('MASHINA TAFSILOTLARI', dark),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _field(_carMCtr, 'Mashina modeli', 'Model (Cobalt...)', Icons.directions_car_filled_outlined, dark,
                    validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _field(_carNCtr, 'Davlat raqami', '01A123AA', Icons.tag_rounded, dark,
                    validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Parol
          _sectionHeader('XAVFSIZLIK PAROLI', dark),
          const SizedBox(height: 12),
          _field(_passCtr, 'Parol', 'Kamida 6 ta belgi', Icons.lock_outline_rounded, dark,
              obscure: _obscure,
              suffix: IconButton(
                icon: Icon(_obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    size: 18, color: Colors.grey.shade400),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
              validator: (v) => v!.length < 6 ? 'Kamida 6 ta belgi bo\'lishi kerak' : null),
          const SizedBox(height: 12),
          _field(_pass2Ctr, 'Parolni tasdiqlang', 'Parolni qayta yozing', Icons.lock_outline_rounded, dark,
              obscure: true,
              validator: (v) => v != _passCtr.text ? 'Parollar mos kelmadi' : null),
          
          const SizedBox(height: 40),
          SizedBox(
            height: 56,
            child: ElevatedButton(
              onPressed: _loading ? null : _register,
              child: _loading
                  ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2.5))
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text("Ariza yuborish", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                        SizedBox(width: 8),
                        Icon(Icons.send_rounded, size: 16),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    ),
  );

  Widget _sectionHeader(String title, bool dark) => Row(
    children: [
      Container(
        width: 3.5, height: 16,
        decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(2)),
      ),
      const SizedBox(width: 8),
      Text(
        title,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w800,
          color: dark ? Colors.grey.shade400 : AppColors.textSecondary,
          letterSpacing: 1.2,
        ),
      ),
    ],
  );

  Widget _field(
    TextEditingController ctrl, String label, String hint, IconData icon, bool dark, {
    TextInputType type = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    String? Function(String?)? validator,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: dark ? Colors.grey.shade300 : AppColors.textPrimary.withValues(alpha: 0.8),
          ),
        ),
        const SizedBox(height: 6),
        TextFormField(
          controller: ctrl,
          keyboardType: type,
          obscureText: obscure,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
          decoration: InputDecoration(
            hintText: hint,
            prefixIcon: Icon(icon, size: 18, color: dark ? Colors.grey.shade500 : Colors.grey.shade400),
            suffixIcon: suffix,
          ),
          validator: validator,
        ),
      ],
    );
  }
}
