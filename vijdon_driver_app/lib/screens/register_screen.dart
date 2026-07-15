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
  bool _done      = false;

  @override
  void dispose() {
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
        content: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600)),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        margin: const EdgeInsets.all(16),
      ));
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final bg   = dark ? AppColors.bgDark : Colors.white;

    return Scaffold(
      backgroundColor: bg,
      appBar: AppBar(
        backgroundColor: bg,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded, size: 18,
              color: dark ? Colors.white : AppColors.textPrimary),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          _done ? '' : "Ro'yxatdan o'tish",
          style: TextStyle(
            fontSize: 18, fontWeight: FontWeight.w900,
            color: dark ? Colors.white : AppColors.textPrimary,
          ),
        ),
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 400),
        child: _done ? _successView(dark, bg) : _formView(dark, bg),
      ),
    );
  }

  Widget _successView(bool dark, Color bg) {
    return Center(
      key: const ValueKey('s'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.0, end: 1.0),
              duration: const Duration(milliseconds: 500),
              curve: Curves.easeOutBack,
              builder: (_, v, child) => Transform.scale(scale: v, child: child),
              child: Container(
                width: 96, height: 96,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(24),
                ),
                child: const Icon(Icons.check_rounded,
                    color: AppColors.textPrimary, size: 52),
              ),
            ),
            const SizedBox(height: 28),
            Text(
              'Ariza yuborildi!',
              style: TextStyle(
                fontSize: 28, fontWeight: FontWeight.w900,
                color: dark ? Colors.white : AppColors.textPrimary,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              "Administrator ko'rib chiqgandan so'ng tizimga kirishingiz mumkin bo'ladi.",
              style: TextStyle(
                fontSize: 15, height: 1.5,
                color: AppColors.textSecondaryDark,
              ),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.access_time_rounded, color: AppColors.primary, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Tasdiqlash 1–2 soat ichida bajariladi.',
                      style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w700,
                        color: dark ? AppColors.primary : AppColors.primaryDark,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36),
            SizedBox(
              height: 56,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Kirish sahifasiga qaytish',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _formView(bool dark, Color bg) {
    final card = dark ? AppColors.cardDark : AppColors.bgLight;
    return SingleChildScrollView(
      key: const ValueKey('f'),
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _section("Shaxsiy ma'lumotlar", dark),
            _field(_nameCtr, "Ism Familya", "To'liq ism familya",
                Icons.person_outline_rounded, card, dark,
                validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null),
            const SizedBox(height: 12),
            _field(_phoneCtr, "Telefon", "+998 90 000 00 00",
                Icons.phone_iphone_rounded, card, dark,
                keyboardType: TextInputType.phone,
                validator: (v) => v!.trim().length < 9 ? "Noto'g'ri raqam" : null),

            _section('Mashina', dark),
            Row(children: [
              Expanded(child: _field(_carMCtr, "Model", "Cobalt...",
                  Icons.directions_car_outlined, card, dark,
                  validator: (v) => v!.trim().isEmpty ? 'Shart' : null)),
              const SizedBox(width: 12),
              Expanded(child: _field(_carNCtr, "Raqam", "01A123AA",
                  Icons.tag_rounded, card, dark,
                  validator: (v) => v!.trim().isEmpty ? 'Shart' : null)),
            ]),

            _section('Parol', dark),
            _field(_passCtr, "Parol", "Kamida 6 ta belgi",
                Icons.lock_outline_rounded, card, dark,
                obscure: _obscure,
                suffix: GestureDetector(
                  onTap: () => setState(() => _obscure = !_obscure),
                  child: Icon(
                    _obscure ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    size: 20, color: AppColors.textSecondaryDark,
                  ),
                ),
                validator: (v) => v!.length < 6 ? 'Kamida 6 ta belgi' : null),
            const SizedBox(height: 12),
            _field(_pass2Ctr, "Parolni tasdiqlang", "Qayta yozing",
                Icons.lock_outline_rounded, card, dark,
                obscure: true,
                validator: (v) => v != _passCtr.text ? 'Parollar mos kelmadi' : null),

            const SizedBox(height: 32),
            SizedBox(
              height: 56,
              child: ElevatedButton(
                onPressed: _loading ? null : _register,
                child: _loading
                    ? const SizedBox(width: 22, height: 22,
                        child: CircularProgressIndicator(
                            color: AppColors.textPrimary, strokeWidth: 2.5))
                    : const Text('Ariza yuborish',
                        style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _section(String title, bool dark) => Padding(
    padding: const EdgeInsets.only(top: 28, bottom: 12),
    child: Text(
      title.toUpperCase(),
      style: const TextStyle(
        fontSize: 11, fontWeight: FontWeight.w800,
        color: AppColors.textSecondaryDark, letterSpacing: 1.5,
      ),
    ),
  );

  Widget _field(
    TextEditingController ctrl, String label, String hint,
    IconData icon, Color card, bool dark, {
    TextInputType keyboardType = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    String? Function(String?)? validator,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(
          fontSize: 12, fontWeight: FontWeight.w700,
          color: dark ? Colors.grey.shade400 : Colors.grey.shade600,
        )),
        const SizedBox(height: 6),
        TextFormField(
          controller: ctrl,
          keyboardType: keyboardType,
          obscureText: obscure,
          validator: validator,
          style: TextStyle(
            fontSize: 15, fontWeight: FontWeight.w600,
            color: dark ? Colors.white : AppColors.textPrimary,
          ),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: card,
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            prefixIcon: Padding(
              padding: const EdgeInsets.only(left: 14, right: 12),
              child: Icon(icon, size: 18, color: AppColors.textSecondaryDark),
            ),
            prefixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
            suffixIcon: suffix != null
                ? Padding(padding: const EdgeInsets.only(right: 14), child: suffix)
                : null,
            suffixIconConstraints: const BoxConstraints(minWidth: 0, minHeight: 0),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                  color: dark ? AppColors.borderDark : AppColors.borderLight),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                  color: dark ? AppColors.borderDark : AppColors.borderLight),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.primary, width: 2),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.danger),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.danger, width: 2),
            ),
            hintStyle: const TextStyle(
                color: AppColors.textSecondaryDark, fontSize: 14),
          ),
        ),
      ],
    );
  }
}
