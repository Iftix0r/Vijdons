import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';

const String kBaseUrl   = 'https://vijdontaxi.uz/client/';
const String kUserAgent =
    'VijdonClient/1.0 (Android; WebView) vijdontaxi.uz';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VijdonClientApp());
}

class VijdonClientApp extends StatelessWidget {
  const VijdonClientApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vijdon Taxi',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.system,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFFFFD600),
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        colorSchemeSeed: const Color(0xFFFFD600),
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF000000),
      ),
      home: const ClientWebView(),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────

class ClientWebView extends StatefulWidget {
  const ClientWebView({super.key});
  @override
  State<ClientWebView> createState() => _ClientWebViewState();
}

class _ClientWebViewState extends State<ClientWebView>
    with WidgetsBindingObserver {
  WebViewController? _ctrl;
  bool _loading    = true;
  bool _firstLoad  = true;
  bool _offline    = false;
  bool _splashDone = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _requestPermissionsAndInit();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _offline) {
      _tryReload();
    }
  }

  // ── Ruxsatlar ───────────────────────────────────────────────────────────────
  Future<void> _requestPermissionsAndInit() async {
    await Permission.locationWhenInUse.request();
    _initWebView();
  }

  // ── WebView init ─────────────────────────────────────────────────────────────
  void _initWebView() {
    final ctrl = WebViewController(
      onPermissionRequest: (req) => req.grant(),
    )
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setUserAgent(kUserAgent)
      ..setBackgroundColor(Colors.transparent)
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) {
          if (mounted) setState(() { if (_firstLoad) _loading = true; });
        },
        onPageFinished: (_) async {
          if (!mounted) return;
          setState(() { _loading = false; _offline = false; _firstLoad = false; });
          await Future.delayed(const Duration(milliseconds: 300));
          if (mounted) setState(() => _splashDone = true);
        },
        onWebResourceError: (err) {
          if (err.isForMainFrame == true) {
            if (mounted) setState(() { _offline = true; _loading = false; });
          }
        },
        onNavigationRequest: (req) {
          final url = req.url;
          if (url.startsWith('tel:')  ||
              url.startsWith('sms:')  ||
              url.startsWith('tg:')   ||
              url.startsWith('https://t.me/') ||
              url.startsWith('http://t.me/')  ||
              url.startsWith('whatsapp:')     ||
              url.startsWith('mailto:')) {
            launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
            return NavigationDecision.prevent;
          }
          return NavigationDecision.navigate;
        },
      ))
      ..loadRequest(Uri.parse(kBaseUrl));

    if (Platform.isAndroid) {
      final androidCtrl = ctrl.platform as AndroidWebViewController;
      // Sahifa navigator.geolocation orqali joylashuvni so'raganda (masalan
      // "joriy manzil" tugmasi bosilganda) darhol ruxsat beramiz — ilova OS
      // darajasida joylashuv ruxsatini allaqachon olgan (yuqorida).
      androidCtrl.setGeolocationPermissionsPromptCallbacks(
        onShowPrompt: (request) async {
          return const GeolocationPermissionsResponse(allow: true, retain: true);
        },
      );
    }

    setState(() => _ctrl = ctrl);
  }

  // ── Orqaga tugma ─────────────────────────────────────────────────────────────
  Future<bool> _onBackPressed() async {
    if (_ctrl == null) return true;
    final canGoBack = await _ctrl!.canGoBack();
    if (canGoBack) {
      await _ctrl!.goBack();
      return false;
    }
    return true;
  }

  // ── Offline reload ────────────────────────────────────────────────────────────
  void _tryReload() {
    setState(() { _offline = false; _loading = true; _firstLoad = true; _splashDone = false; });
    _ctrl?.loadRequest(Uri.parse(kBaseUrl));
  }

  // ── Build ─────────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? const Color(0xFF000000) : const Color(0xFFF2F2F7);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final shouldPop = await _onBackPressed();
        if (shouldPop && context.mounted) {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        backgroundColor: bgColor,
        body: Stack(
          children: [
            if (_ctrl != null && !_offline)
              WebViewWidget(controller: _ctrl!),
            if (_offline)
              _OfflinePage(onRetry: _tryReload, isDark: isDark),
            if (!_splashDone)
              AnimatedOpacity(
                opacity: _loading ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 400),
                child: _SplashScreen(bgColor: bgColor, isDark: isDark),
              ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Splash screen widget
// ─────────────────────────────────────────────────────────────────────────────
class _SplashScreen extends StatefulWidget {
  final Color bgColor;
  final bool  isDark;
  const _SplashScreen({required this.bgColor, required this.isDark});
  @override
  State<_SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<_SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ac;
  late final Animation<double>   _scale;
  late final Animation<double>   _fade;

  @override
  void initState() {
    super.initState();
    _ac = AnimationController(vsync: this,
        duration: const Duration(milliseconds: 700));
    _scale = CurvedAnimation(parent: _ac, curve: Curves.elasticOut);
    _fade  = CurvedAnimation(parent: _ac, curve: Curves.easeIn);
    _ac.forward();
  }

  @override
  void dispose() { _ac.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: widget.bgColor,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ScaleTransition(
              scale: _scale,
              child: FadeTransition(
                opacity: _fade,
                child: Container(
                  width: 96, height: 96,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFD600),
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFFFD600).withValues(alpha: .4),
                        blurRadius: 32, spreadRadius: 4,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Text('V',
                      style: TextStyle(
                        fontSize: 56,
                        fontWeight: FontWeight.w900,
                        color: Colors.black,
                        height: 1,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: 28, height: 28,
              child: CircularProgressIndicator(
                strokeWidth: 2.5,
                color: const Color(0xFFFFD600).withValues(alpha: .7),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Offline page widget
// ─────────────────────────────────────────────────────────────────────────────
class _OfflinePage extends StatelessWidget {
  final VoidCallback onRetry;
  final bool isDark;
  const _OfflinePage({required this.onRetry, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final bg   = isDark ? const Color(0xFF000000) : const Color(0xFFF2F2F7);
    final card = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final lbl  = isDark ? Colors.white : Colors.black;
    final lbl3 = isDark
        ? Colors.white.withValues(alpha: .4)
        : Colors.black.withValues(alpha: .4);

    return Container(
      color: bg,
      child: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 88, height: 88,
                  decoration: BoxDecoration(
                    color: card,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Icon(Icons.wifi_off_rounded, size: 44, color: lbl3),
                ),
                const SizedBox(height: 24),
                Text('Internet aloqasi yo\'q',
                    style: TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w700, color: lbl)),
                const SizedBox(height: 8),
                Text('Tarmoq ulanishini tekshiring\nva qayta urinib ko\'ring',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 15, color: lbl3, height: 1.5)),
                const SizedBox(height: 32),
                GestureDetector(
                  onTap: onRetry,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 32, vertical: 16),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFD600),
                      borderRadius: BorderRadius.circular(14),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFFFFD600).withValues(alpha: .35),
                          blurRadius: 16,
                        ),
                      ],
                    ),
                    child: const Text('Qayta urinish',
                        style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            color: Colors.black)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
