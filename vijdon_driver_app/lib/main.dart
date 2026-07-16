import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'core/notification_service.dart';

const String kBaseUrl = 'https://vijdontaxi.uz/driver/';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await NotificationService.init();
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
  late final WebViewController _ctrl;
  bool _loading = true;
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
    await [
      Permission.location,
      Permission.locationWhenInUse,
      Permission.notification,
    ].request();
    _initWebView();
    _startLocationUpdates();
  }

  void _initWebView() {
    _ctrl = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel(
        'FlutterNotify',
        onMessageReceived: (msg) {
          final count = int.tryParse(msg.message) ?? 1;
          NotificationService.notifyNewOrder(count);
        },
      )
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) => setState(() => _loading = true),
        onPageFinished: (_) async {
          setState(() => _loading = false);
          await _injectLocation();
          await _injectNotificationBridge();
        },
      ))
      ..loadRequest(Uri.parse(kBaseUrl));
  }

  void _startLocationUpdates() {
    _locationTimer = Timer.periodic(const Duration(seconds: 15), (_) async {
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 8),
        );
        _sendLocation(pos.latitude, pos.longitude);
      } catch (_) {}
    });
  }

  Future<void> _injectLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 8),
      );
      _sendLocation(pos.latitude, pos.longitude);
    } catch (_) {}
  }

  void _sendLocation(double lat, double lng) {
    _ctrl.runJavaScript(
      "window.dispatchEvent(new CustomEvent('vijdon_location',"
      "{detail:{lat:$lat,lng:$lng}}))",
    );
  }

  Future<void> _injectNotificationBridge() async {
    await _ctrl.runJavaScript("""
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
            WebViewWidget(controller: _ctrl),
            if (_loading)
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
