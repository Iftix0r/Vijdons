import 'package:flutter/cupertino.dart';
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
    _ac    = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _fade  = CurvedAnimation(parent: _ac, curve: Curves.easeOut);
    _slide = Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero)
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
    if (_phoneCtr.text.trim().length < 9) {
      _snack("Noto'g'ri telefon raqami");
      return;
    }
    if (_passCtr.text.length < 6) {
      _snack('Kamida 6 ta belgi kiriting');
      return;
    }
    FocusScope.of(context).unfocus();
    HapticFeedback.lightImpact();
    setState(() => _loading = true);
    try {
      await ApiService.login(_phoneCtr.text.trim(), _passCtr.text);
      if (!mounted) return;
      HapticFeedback.mediumImpact();
      Navigator.pushReplacement(context, CupertinoPageRoute(
        builder: (_) => const HomeScreen(),
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
        content: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600)),
        backgroundColor: AppColors.danger,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        duration: const Duration(seconds: 3),
      ));
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).padding.bottom;
    final top    = MediaQuery.of(context).padding.top;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: AppColors.bgDark,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
      child: Scaffold(
        backgroundColor: AppColors.bgDark,
        resizeToAvoidBottomInset: true,
        body: FadeTransition(
          opacity: _fade,
          child: SlideTransition(
            position: _slide,
            child: Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: EdgeInsets.fromLTRB(24, top + 52, 24, 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // ── Logo ──────────────────────────────────────────
                        Center(child: _logoBox()),
                        const SizedBox(height: 36),

                        // ── Title ─────────────────────────────────────────
                        const Text(
                          'Kirish',
                          style: TextStyle(
                            fontSize: 34, fontWeight: FontWeight.w700,
                            color: Colors.white, letterSpacing: -1.0,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Haydovchi hisobingizga kiring',
                          style: TextStyle(
                            fontSize: 15, color: Colors.grey.shade500,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                        const SizedBox(height: 36),

                        // ── Fields card (iOS grouped style) ───────────────
                        Container(
                          decoration: BoxDecoration(
                            color: AppColors.cardDark,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Column(
                            children: [
                              // Phone
                              _iosField(
                                controller: _phoneCtr,
                                placeholder: '+998 90 000 00 00',
                                icon: CupertinoIcons.phone_fill,
                                keyboardType: TextInputType.phone,
                                textInputAction: TextInputAction.next,
                              ),
                              Container(height: 0.5, color: AppColors.borderDark,
                                  margin: const EdgeInsets.only(left: 52)),
                              // Password
                              _iosField(
                                controller: _passCtr,
                                placeholder: 'Parol',
                                icon: CupertinoIcons.lock_fill,
                                obscure: _obscure,
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) => _login(),
                                suffix: CupertinoButton(
                                  padding: const EdgeInsets.only(right: 4),
                                  minSize: 0,
                                  onPressed: () => setState(() => _obscure = !_obscure),
                                  child: Icon(
                                    _obscure
                                        ? CupertinoIcons.eye_slash_fill
                                        : CupertinoIcons.eye_fill,
                                    size: 18,
                                    color: Colors.grey.shade500,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 28),

                        // ── Login button ──────────────────────────────────
                        _primaryBtn(
                          label: 'Kirish',
                          loading: _loading,
                          onTap: _loading ? null : _login,
                        ),
                        const SizedBox(height: 12),

                        // ── Register link ─────────────────────────────────
                        CupertinoButton(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          onPressed: () => Navigator.push(context,
                              CupertinoPageRoute(
                                  builder: (_) => const RegisterScreen())),
                          child: Text(
                            "Ro'yxatdan o'tish",
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: AppColors.info,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                // Bottom safe area
                SizedBox(height: bottom),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _logoBox() {
    return Container(
      width: 88, height: 88,
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.35),
            blurRadius: 24, offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Center(
        child: Text(
          'V',
          style: TextStyle(
            fontSize: 48, fontWeight: FontWeight.w900,
            color: Colors.black,
            letterSpacing: -2,
            height: 1,
          ),
        ),
      ),
    );
  }

  Widget _iosField({
    required TextEditingController controller,
    required String placeholder,
    required IconData icon,
    TextInputType keyboardType = TextInputType.text,
    bool obscure = false,
    Widget? suffix,
    TextInputAction textInputAction = TextInputAction.next,
    ValueChanged<String>? onSubmitted,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.grey.shade500),
          const SizedBox(width: 12),
          Expanded(
            child: CupertinoTextField.borderless(
              controller: controller,
              placeholder: placeholder,
              keyboardType: keyboardType,
              obscureText: obscure,
              textInputAction: textInputAction,
              onSubmitted: onSubmitted,
              style: const TextStyle(
                fontSize: 16, color: Colors.white, fontWeight: FontWeight.w400,
              ),
              placeholderStyle: TextStyle(
                fontSize: 16, color: Colors.grey.shade600,
              ),
              padding: const EdgeInsets.symmetric(vertical: 14),
              suffix: suffix,
            ),
          ),
        ],
      ),
    );
  }

  Widget _primaryBtn({
    required String label,
    required bool loading,
    VoidCallback? onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        height: 56,
        decoration: BoxDecoration(
          color: loading
              ? AppColors.primary.withValues(alpha: 0.6)
              : AppColors.primary,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Center(
          child: loading
              ? const CupertinoActivityIndicator(color: Colors.black)
              : Text(
                  label,
                  style: const TextStyle(
                    fontSize: 17, fontWeight: FontWeight.w600,
                    color: Colors.black,
                  ),
                ),
        ),
      ),
    );
  }
}
