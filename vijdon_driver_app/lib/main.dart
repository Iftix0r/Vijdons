import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'core/notification_service.dart';

const String kBaseUrl = 'https://vijdontaxi.uz/driver/';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.init();
  await NotificationService.clearBadge();
  runApp(const VijdonDriverApp());
}

class VijdonDriverApp extends StatelessWidget {
  const VijdonDriverApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vijdon Driver',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFFFFD600)),
      home: const DriverWebView(),
    );
  }
}

class DriverWebView extends StatefulWidget {
  const DriverWebView({super.key});
  @override
  State<DriverWebView> createState() => _DriverWebViewState();
}

class _DriverWebViewState extends State<DriverWebView> {
  WebViewController? _ctrl;
  bool _loading = true;
  bool _firstLoad = true;
  Timer? _locationTimer;

  @override
  void initState() {
    super.initState();
    _requestPermissionsAndInit();
  }

  @override
  void dispose() {
    _locationTimer?.cancel();
    super.dispose();
  }

  Future<void> _requestPermissionsAndInit() async {
    // Ketma-ket so'raymiz — Android bir vaqtda hammani ko'rsatmaydi

    // 1. Joylashuv — eng muhim
    await Permission.locationWhenInUse.request();
    final locStatus = await Permission.location.request();

    // locationAlways faqat locationWhenInUse granted bo'lsa so'rash mumkin
    if (locStatus.isGranted) {
      await Permission.locationAlways.request();
    }

    // 2. Bildirishnoma
    await Permission.notification.request();

    // 3. Kamera
    await Permission.camera.request();

    // 4. Galereya / media
    // Android 13+ READ_MEDIA_IMAGES, pastroq READ_EXTERNAL_STORAGE
    await Permission.photos.request();
    await Permission.videos.request();
    await Permission.mediaLibrary.request();

    // 5. Mikrofon (WebView audio/video uchun)
    await Permission.microphone.request();

    _initWebView();
    _startLocationUpdates();
  }

  void _initWebView() {
    final ctrl = WebViewController(
      onPermissionRequest: (request) => request.grant(),
    )
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel(
        'FlutterNotify',
        onMessageReceived: (msg) {
          final count = int.tryParse(msg.message) ?? 1;
          if (count == 0) {
            NotificationService.clearBadge();
          } else {
            NotificationService.notifyNewOrder(count);
          }
        },
      )
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) {
          if (_firstLoad) setState(() => _loading = true);
        },
        onPageFinished: (_) async {
          if (_firstLoad) {
            setState(() { _loading = false; _firstLoad = false; });
          }
          await _injectLocation();
          await _injectNotificationBridge();
        },
        onNavigationRequest: (request) {
          final url = request.url;
          // tel:, sms:, tg:, https://t.me/ — tashqi ilova orqali ochish
          if (url.startsWith('tel:') ||
              url.startsWith('sms:') ||
              url.startsWith('tg:') ||
              url.startsWith('https://t.me/') ||
              url.startsWith('http://t.me/') ||
              url.startsWith('whatsapp:') ||
              url.startsWith('mailto:')) {
            launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
            return NavigationDecision.prevent;
          }
          return NavigationDecision.navigate;
        },
      ))
      ..loadRequest(Uri.parse(kBaseUrl));
    setState(() => _ctrl = ctrl);
  }

  void _startLocationUpdates() {
    _locationTimer = Timer.periodic(const Duration(seconds: 15), (_) async {
      try {
        final pos = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high,
            timeLimit: Duration(seconds: 8),
          ),
        );
        _sendLocation(pos.latitude, pos.longitude);
      } catch (_) {}
    });
  }

  Future<void> _injectLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      _sendLocation(pos.latitude, pos.longitude);
    } catch (_) {}
  }


  void _sendLocation(double lat, double lng) {
    _ctrl?.runJavaScript(
      "window.dispatchEvent(new CustomEvent('vijdon_location',"
      "{detail:{lat:$lat,lng:$lng}}))",
    );
  }

  Future<void> _injectNotificationBridge() async {
    await _ctrl?.runJavaScript("""
      (function() {
        if (window._vijdonNotifyInjected) return;
        window._vijdonNotifyInjected = true;
        const _orig = window.__vijdonOrderCount || 0;
        window.__vijdonOrderCount = _orig;
        window.vijdonNotifyNewOrder = function(count) {
          FlutterNotify.postMessage(String(count || 1));
        };
      })();
    """);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1C1C1E),
      body: SafeArea(
        child: Stack(
          children: [
            if (_ctrl != null) WebViewWidget(controller: _ctrl!),
            if (_loading || _ctrl == null)
              const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('V',
                      style: TextStyle(
                        fontSize: 64,
                        fontWeight: FontWeight.w900,
                        color: Color(0xFFFFD600),
                      ),
                    ),
                    SizedBox(height: 24),
                    CircularProgressIndicator(
                      color: Color(0xFFFFD600),
                      strokeWidth: 2,
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
