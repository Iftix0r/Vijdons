import 'dart:async';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:webview_flutter/webview_flutter.dart';

const String kBaseUrl = 'https://vijdontaxi.uz/driver/';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
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
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) => setState(() => _loading = true),
        onPageFinished: (_) async {
          setState(() => _loading = false);
          await _injectLocation();
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
