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
        content: Text(msg, style: const TextStyle(fontWeight: FontWeight.w700)),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
      ));
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.bgDark,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
      child: Scaffold(
        backgroundColor: AppColors.bgDark,
        appBar: AppBar(
          backgroundColor: AppColors.bgDark,
          surfaceTintColor: Colors.transparent,
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new_rounded,
                size: 18, color: Colors.white),
            onPressed: () => Navigator.pop(context),
          ),
          title: AnimatedSwitcher(
            duration: const Duration(milliseconds: 300),
            child: _done
                ? const SizedBox.shrink()
                : const Text(
                    "Ro'yxatdan o'tish",
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        color: Colors.white),
                  ),
          ),
        ),
        body: AnimatedSwitcher(
          duration: const Duration(milliseconds: 450),
          transitionBuilder: (child, anim) =>
              FadeTransition(opacity: anim, child: child),
          child: _done ? _successView() : _formView(),
        ),
      ),
    );
  }

  // ── Success ────────────────────────────────────────────────────────────────

  Widget _successView() {
    return Center(
      key: const ValueKey('success'),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Animated checkmark icon
            Center(
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.0, end: 1.0),
                duration: const Duration(milliseconds: 600),
                curve: Curves.easeOutBack,
                builder: (_, v, child) =>
                    Transform.scale(scale: v, child: child),
                child: Container(
                  width: 100, height: 100,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: const Icon(Icons.check_rounded,
                      color: AppColors.textPrimary, size: 56),
                ),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'Ariza yuborildi!',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 30, fontWeight: FontWeight.w900,
                color: Colors.white, letterSpacing: -0.8,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              "Administrator ko'rib chiqgandan so'ng\ntizimga kirishingiz mumkin bo'ladi.",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 15, height: 1.6,
                color: AppColors.textSecondaryDark,
              ),
            ),
            const SizedBox(height: 24),

            // Info banner
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surfaceDark,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 38, height: 38,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.access_time_rounded,
                        color: AppColors.primary, size: 20),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Tasdiqlash odatda 1–2 soat ichida bajariladi.',
                      style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w700,
                        color: Colors.white, height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36),

            SizedBox(
              height: 58,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Kirish sahifasiga qaytish',
                    style: TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w900)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Form ───────────────────────────────────────────────────────────────────

  Widget _formView() {
    return SingleChildScrollView(
      key: const ValueKey('form'),
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _sectionLabel("Shaxsiy ma'lumotlar"),
            _field(
              _nameCtr, "Ism Familya", "To'liq ism familya",
              Icons.person_outline_rounded,
              validator: (v) => v!.trim().isEmpty ? 'Kiritish shart' : null,
            ),
            const SizedBox(height: 12),
            _field(
              _phoneCtr, "Telefon", "+998 90 000 00 00",
              Icons.phone_iphone_rounded,
              keyboardType: TextInputType.phone,
              validator: (v) =>
                  v!.trim().length < 9 ? "Noto'g'ri raqam" : null,
            ),

            _sectionLabel('Mashina ma\'lumotlari'),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: _field(
                    _carMCtr, "Model", "Cobalt...",
                    Icons.directions_car_outlined,
                    validator: (v) =>
                        v!.trim().isEmpty ? 'Kiritish shart' : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: _field(
                    _carNCtr, "Raqam", "01A123AA",
                    Icons.tag_rounded,
                    validator: (v) =>
                        v!.trim().isEmpty ? 'Kiritish shart' : null,
                  ),
                ),
              ],
            ),

            _sectionLabel('Parol belgilash'),
            _field(
              _passCtr, "Parol", "Kamida 6 ta belgi",
              Icons.lock_outline_rounded,
              obscure: _obscure,
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
            const SizedBox(height: 12),
            _field(
              _pass2Ctr, "Parolni tasdiqlang", "Qayta yozing",
              Icons.lock_outline_rounded,
              obscure: true,
              validator: (v) =>
                  v != _passCtr.text ? 'Parollar mos kelmadi' : null,
            ),

            const SizedBox(height: 36),

            SizedBox(
              height: 58,
              child: ElevatedButton(
                onPressed: _loading ? null : _register,
                style: ElevatedButton.styleFrom(
                  disabledBackgroundColor:
                      AppColors.primary.withValues(alpha: 0.5),
                ),
                child: _loading
                    ? const SizedBox(
                        width: 22, height: 22,
                        child: CircularProgressIndicator(
                            color: AppColors.textPrimary, strokeWidth: 2.5))
                    : const Text('Ariza yuborish',
                        style: TextStyle(
                            fontSize: 17, fontWeight: FontWeight.w900)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionLabel(String title) => Padding(
    padding: const EdgeInsets.only(top: 28, bottom: 14),
    child: Row(
      children: [
        Container(
          width: 3, height: 14,
          decoration: BoxDecoration(
            color: AppColors.primary,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title.toUpperCase(),
          style: const TextStyle(
            fontSize: 10, fontWeight: FontWeight.w900,
            color: AppColors.textSecondaryDark, letterSpacing: 1.8,
          ),
        ),
      ],
    ),
  );

  Widget _field(
    TextEditingController ctrl,
    String label,
    String hint,
    IconData icon, {
    TextInputType keyboardType = TextInputType.text,
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
            fontSize: 12, fontWeight: FontWeight.w700,
            color: Colors.grey.shade500,
          ),
        ),
        const SizedBox(height: 7),
        TextFormField(
          controller: ctrl,
          keyboardType: keyboardType,
          obscureText: obscure,
          validator: validator,
          style: const TextStyle(
            fontSize: 15, fontWeight: FontWeight.w600,
            color: Colors.white,
          ),
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: AppColors.surfaceDark,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            prefixIcon: Padding(
              padding: const EdgeInsets.only(left: 14, right: 12),
              child: Icon(icon, size: 18, color: AppColors.textSecondaryDark),
            ),
            prefixIconConstraints:
                const BoxConstraints(minWidth: 0, minHeight: 0),
            suffixIcon: suffix != null
                ? Padding(
                    padding: const EdgeInsets.only(right: 14),
                    child: suffix)
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
              borderSide:
                  const BorderSide(color: AppColors.primary, width: 2),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: AppColors.danger),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide:
                  const BorderSide(color: AppColors.danger, width: 2),
            ),
            hintStyle: const TextStyle(
                color: AppColors.textSecondaryDark, fontSize: 14),
            errorStyle:
                const TextStyle(color: AppColors.danger, fontSize: 12),
          ),
        ),
      ],
    );
  }
}
