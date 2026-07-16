import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

const String kBaseUrl = 'https://vijdontaxi.uz/driver/';

final FlutterLocalNotificationsPlugin _notif = FlutterLocalNotificationsPlugin();

@pragma('vm:entry-point')
Future<void> _firebaseBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  _showNotification(message.notification?.title ?? 'Vijdon Driver',
      message.notification?.body ?? '');
}

void _showNotification(String title, String body) {
  _notif.show(
    DateTime.now().millisecondsSinceEpoch ~/ 1000,
    title, body,
    notificationDetails: const NotificationDetails(
      android: AndroidNotificationDetails(
        'vijdon_orders', 'Buyurtmalar',
        importance: Importance.max,
        priority: Priority.high,
        playSound: true,
      ),
    ),
  );
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseBackgroundHandler);
  await _notif.initialize(
    const InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
    ),
  );
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
    _initWebView();
    _initFcm();
    _requestPermissions();
  }

  @override
  void dispose() {
    _locationTimer?.cancel();
    super.dispose();
  }

  void _initWebView() {
    _ctrl = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) => setState(() => _loading = true),
        onPageFinished: (_) async {
          setState(() => _loading = false);
          await _injectBridge();
        },
      ))
      ..addJavaScriptChannel('NativeBridge', onMessageReceived: _onBridgeMessage)
      ..loadRequest(Uri.parse(kBaseUrl));
  }

  // ── FCM ──────────────────────────────────────────────────────────────────
  Future<void> _initFcm() async {
    await FirebaseMessaging.instance.requestPermission();
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
    }

    FirebaseMessaging.onMessage.listen((msg) {
      _showNotification(
        msg.notification?.title ?? 'Vijdon Driver',
        msg.notification?.body ?? '',
      );
      // WebView ga yangi buyurtma signali yuborish
      _ctrl.runJavaScript("window.dispatchEvent(new Event('vijdon_new_order'))");
    });

    FirebaseMessaging.instance.onTokenRefresh.listen((token) async {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
      _ctrl.runJavaScript("window.nativeFcmToken = '$token'");
    });
  }

  // ── Permissions ──────────────────────────────────────────────────────────
  Future<void> _requestPermissions() async {
    await [
      Permission.location,
      Permission.locationAlways,
      Permission.notification,
    ].request();
    _startLocationUpdates();
  }

  // ── GPS background ───────────────────────────────────────────────────────
  void _startLocationUpdates() {
    _locationTimer = Timer.periodic(const Duration(seconds: 15), (_) async {
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 8),
        );
        // WebView ga koordinata yuborish
        _ctrl.runJavaScript(
          "window.dispatchEvent(new CustomEvent('vijdon_location', "
          "{detail: {lat: ${pos.latitude}, lng: ${pos.longitude}}}))");
      } catch (_) {}
    });
  }

  // ── JS Bridge: WebView → Native ──────────────────────────────────────────
  void _onBridgeMessage(JavaScriptMessage msg) async {
    try {
      final data = jsonDecode(msg.message) as Map<String, dynamic>;
      final action = data['action'] as String?;

      switch (action) {
        case 'get_fcm_token':
          final prefs = await SharedPreferences.getInstance();
          final token = prefs.getString('fcm_token') ?? '';
          _ctrl.runJavaScript("window.nativeFcmToken = '$token';"
              "window.dispatchEvent(new CustomEvent('vijdon_fcm', {detail: '$token'}))");

        case 'get_location':
          try {
            final pos = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.high,
              timeLimit: const Duration(seconds: 8),
            );
            _ctrl.runJavaScript(
              "window.dispatchEvent(new CustomEvent('vijdon_location', "
              "{detail: {lat: ${pos.latitude}, lng: ${pos.longitude}}}))");
          } catch (_) {}

        case 'vibrate':
          HapticFeedback.mediumImpact();

        case 'open_phone':
          final phone = data['phone'] as String? ?? '';
          if (phone.isNotEmpty) {
            SystemChannels.platform.invokeMethod('SystemNavigator.pop');
          }
      }
    } catch (_) {}
  }

  // ── WebView ga inject qilinadigan JS bridge ──────────────────────────────
  Future<void> _injectBridge() async {
    final prefs = await SharedPreferences.getInstance();
    final fcmToken = prefs.getString('fcm_token') ?? '';

    await _ctrl.runJavaScript('''
      window.nativeFcmToken = '$fcmToken';
      window.VijdonNative = {
        getFcmToken: () => NativeBridge.postMessage(JSON.stringify({action: 'get_fcm_token'})),
        getLocation:  () => NativeBridge.postMessage(JSON.stringify({action: 'get_location'})),
        vibrate:      () => NativeBridge.postMessage(JSON.stringify({action: 'vibrate'})),
        callPhone: (p) => NativeBridge.postMessage(JSON.stringify({action: 'open_phone', phone: p})),
      };
      console.log('[VijdonNative] Bridge ready, FCM: $fcmToken');
    ''');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1C1C1E),
      body: Stack(
        children: [
          WebViewWidget(controller: _ctrl),
          if (_loading)
            const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('V',
                    style: TextStyle(
                      fontSize: 64, fontWeight: FontWeight.w900,
                      color: Color(0xFFFFD600),
                    ),
                  ),
                  SizedBox(height: 24),
                  CircularProgressIndicator(color: Color(0xFFFFD600), strokeWidth: 2),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
