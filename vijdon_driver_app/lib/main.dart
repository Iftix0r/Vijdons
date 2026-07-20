import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'core/notification_service.dart';
import 'core/order_poll_task_handler.dart';

const String kBaseUrl      = 'https://vijdontaxi.uz/driver/';
const String kUserAgent    =
    'VijdonDriver/1.1 (Android; WebView) vijdontaxi.uz';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterForegroundTask.initCommunicationPort();
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
      // Ilova mavzusi — dark mode tizimga ergashadi
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
      home: const DriverWebView(),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────

class DriverWebView extends StatefulWidget {
  const DriverWebView({super.key});
  @override
  State<DriverWebView> createState() => _DriverWebViewState();
}

class _DriverWebViewState extends State<DriverWebView>
    with WidgetsBindingObserver {
  WebViewController? _ctrl;
  bool   _loading     = true;
  bool   _firstLoad   = true;
  bool   _offline     = false;
  bool   _splashDone  = false;
  Timer? _locationTimer;
  final  _picker      = ImagePicker();

  // ── Lifecycle ───────────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    FlutterForegroundTask.addTaskDataCallback(_onReceiveTaskData);
    WidgetsBinding.instance.addPostFrameCallback((_) => _initForegroundTask());
    _requestPermissionsAndInit();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    FlutterForegroundTask.removeTaskDataCallback(_onReceiveTaskData);
    _locationTimer?.cancel();
    super.dispose();
  }

  // Internet holatini kuzatish
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _offline) {
      _tryReload();
    }
  }

  // ── Ruxsatlar ───────────────────────────────────────────────────────────────
  Future<void> _requestPermissionsAndInit() async {
    await Permission.locationWhenInUse.request();
    final locStatus = await Permission.location.request();
    if (locStatus.isGranted) await Permission.locationAlways.request();
    await Permission.notification.request();
    await Permission.camera.request();
    await Permission.photos.request();
    await Permission.videos.request();
    await Permission.mediaLibrary.request();
    await Permission.microphone.request();

    _initWebView();
    _startLocationUpdates();
  }

  // ── WebView init ─────────────────────────────────────────────────────────────
  void _initWebView() {
    final ctrl = WebViewController(
      onPermissionRequest: (req) => req.grant(),
    )
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setUserAgent(kUserAgent)
      ..setBackgroundColor(Colors.transparent)
      ..addJavaScriptChannel('FlutterNotify',
          onMessageReceived: (msg) {
            final count = int.tryParse(msg.message) ?? 1;
            if (count == 0) {
              NotificationService.clearBadge();
            } else {
              NotificationService.notifyNewOrder(count);
            }
          })
      // Sayt har sahifa ochilishida (jumladan Liniyaga chiqish/chiqishdan
      // keyingi qayta yuklanishda) haydovchining "ish navbatida" holatini
      // shu kanal orqali bildiradi — shunga qarab fon xizmati yoqiladi/
      // o'chiriladi (base.html'dagi IS_ON_DUTY_GLOBAL orqali yuboriladi).
      ..addJavaScriptChannel('FlutterDuty',
          onMessageReceived: (msg) {
            _syncDutyService(msg.message == '1');
          })
      ..setNavigationDelegate(NavigationDelegate(
        onPageStarted: (_) {
          if (mounted) setState(() { if (_firstLoad) _loading = true; });
        },
        onPageFinished: (_) async {
          if (!mounted) return;
          setState(() { _loading = false; _offline = false; _firstLoad = false; });
          await Future.delayed(const Duration(milliseconds: 300));
          if (mounted) setState(() => _splashDone = true);
          await _injectLocation();
          await _injectNotificationBridge();
        },
        onWebResourceError: (err) {
          // Faqat asosiy sahifa yuklanmasa offline ko'rsatamiz
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

    // ── File upload (Android only) ───────────────────────────────────────────
    if (Platform.isAndroid) {
      final androidCtrl = ctrl.platform as AndroidWebViewController;
      androidCtrl.setOnShowFileSelector(_handleFileChooser);
      // Jonli ovozli aloqa ("efir") sahifa ochilishi bilan avtomatik ulanadi
      // va foydalanuvchi biror joyni bosmasdan turib kiruvchi ovozni ijro
      // etishga urinadi — standart holatda Android WebView buni "avtoijro"
      // siyosati bo'yicha bloklaydi (chunki hech qanday tegish/bosish
      // bo'lmagan). Bu ilova to'liq o'zimizniki bo'lgani uchun bu cheklovni
      // xavfsiz o'chirib qo'yamiz.
      androidCtrl.setMediaPlaybackRequiresUserGesture(false);
      // Taximetr sahifada (base.html) zaxira manba sifatida
      // navigator.geolocation.watchPosition() ni ham chaqiradi (asosiy
      // manba — native GPS bridge, bu esa faqat qo'shimcha). Bu
      // onPermissionRequest'dan BUTUNLAY BOSHQA, alohida WebView callback
      // (onGeolocationPermissionsShowPrompt) orqali so'raladi — shu
      // sozlanmagani uchun sayt so'rovi hozircha javobsiz qolardi. Ilova
      // OS darajasida joylashuv ruxsatini allaqachon olgani uchun
      // (_requestPermissionsAndInit yuqorida), bu yerda ham xavfsiz
      // avtomatik ruxsat beramiz.
      androidCtrl.setGeolocationPermissionsPromptCallbacks(
        onShowPrompt: (request) async {
          return const GeolocationPermissionsResponse(allow: true, retain: true);
        },
      );
    }

    setState(() => _ctrl = ctrl);
  }

  // ── File chooser: kamera yoki galereya ──────────────────────────────────────
  Future<List<String>> _handleFileChooser(
      FileSelectorParams params) async {
    final acceptsImage = params.acceptTypes.any(
        (t) => t.contains('image') || t.contains('*/*') || t == '');
    final acceptsVideo = params.acceptTypes.any(
        (t) => t.contains('video'));

    final action = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _FileChooserSheet(
          acceptsImage: acceptsImage, acceptsVideo: acceptsVideo),
    );
    if (action == null) return [];

    try {
      if (action == 'camera_photo') {
        final f = await _picker.pickImage(
            source: ImageSource.camera, imageQuality: 85);
        return f != null ? [f.path] : [];
      } else if (action == 'camera_video') {
        final f = await _picker.pickVideo(source: ImageSource.camera);
        return f != null ? [f.path] : [];
      } else if (action == 'gallery_image') {
        final f = await _picker.pickImage(source: ImageSource.gallery);
        return f != null ? [f.path] : [];
      } else if (action == 'gallery_video') {
        final f = await _picker.pickVideo(source: ImageSource.gallery);
        return f != null ? [f.path] : [];
      } else if (action == 'gallery_multi') {
        final files = await _picker.pickMultiImage();
        return files.map((f) => f.path).toList();
      }
    } catch (_) {}
    return [];
  }

  // ── Buyurtma kuzatuvi fon xizmati ────────────────────────────────────────────
  // Oldin bu shunchaki widget darajasidagi Timer edi — u faqat ilova jarayoni
  // tirik bo'lganda ishlardi (Android ilovani fondan "o'chirib" qo'ysa,
  // to'xtab qolardi, va yangi buyurtma bildirishnomasi faqat ilova qayta
  // ochilgandagina kelardi). Endi buyurtma so'rovi alohida fon-xizmat
  // isolate'ida (order_poll_task_handler.dart) ishlaydi — u doimiy
  // bildirishnoma bilan ko'rinib turgani uchun Android tomonidan deyarli
  // hech qachon o'chirilmaydi. Xizmat FAQAT haydovchi "ish navbatida"
  // bo'lganda ishlaydi (_syncDutyService orqali FlutterDuty kanalidan
  // boshqariladi).
  void _initForegroundTask() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'duty_service_channel',
        channelName: 'Ish navbatida',
        channelDescription:
            'Ilova fonda ishlashi va yangi buyurtmalarni o\'tkazib yubormasligi uchun',
        onlyAlertOnce: true,
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: false,
        playSound: false,
      ),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.repeat(7000),
        autoRunOnBoot: false,
        autoRunOnMyPackageReplaced: true,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  // Fon xizmatidagi isolate'dan (yangi buyurtma topilganda) kelgan signal —
  // ilova ekranda ochiq bo'lsa, sahifadagi buyurtmalar ro'yxatini ham
  // yangilaymiz (bildirishnomaning o'zi allaqachon fon isolate'ida
  // ko'rsatilgan bo'ladi).
  void _onReceiveTaskData(Object data) {
    if (data is Map && data['newOrders'] != null) {
      _ctrl?.runJavaScript('if(typeof onNewOrder==="function")onNewOrder();');
    }
  }

  Future<void> _syncDutyService(bool onDuty) async {
    if (!Platform.isAndroid) return;
    try {
      if (onDuty) {
        if (await FlutterForegroundTask.isRunningService) return;
        final NotificationPermission notifPerm =
            await FlutterForegroundTask.checkNotificationPermission();
        if (notifPerm != NotificationPermission.granted) {
          await FlutterForegroundTask.requestNotificationPermission();
        }
        // Android ilovani fondan o'chirib qo'ymasligi uchun — bu tuzatish
        // aynan MIUI kabi tizimlarda haydovchilar shikoyat qilgan "yangi
        // buyurtma bildirishnomasi ilova qayta ochilgandan keyin keladi"
        // muammosining bosh sababi edi.
        if (!await FlutterForegroundTask.isIgnoringBatteryOptimizations) {
          await FlutterForegroundTask.requestIgnoreBatteryOptimization();
        }
        await FlutterForegroundTask.startService(
          serviceId: 300,
          notificationTitle: 'Vijdon Driver — ish navbatida',
          notificationText: 'Yangi buyurtmalarni kuzatib turibmiz',
          callback: startOrderPollTask,
        );
      } else {
        if (await FlutterForegroundTask.isRunningService) {
          await FlutterForegroundTask.stopService();
        }
      }
    } catch (_) {}
  }

  // ── GPS ──────────────────────────────────────────────────────────────────────
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

  // ── JS bridge ────────────────────────────────────────────────────────────────
  Future<void> _injectNotificationBridge() async {
    await _ctrl?.runJavaScript("""
      (function(){
        if(window._vijdonNotifyInjected) return;
        window._vijdonNotifyInjected = true;
        window.vijdonNotifyNewOrder = function(count){
          FlutterNotify.postMessage(String(count||1));
        };
      })();
    """);
  }

  // ── Orqaga tugma ─────────────────────────────────────────────────────────────
  Future<bool> _onBackPressed() async {
    if (_ctrl == null) return true;
    final canGoBack = await _ctrl!.canGoBack();
    if (canGoBack) {
      await _ctrl!.goBack();
      return false; // ilovani yopma
    }
    return true; // ilova yopilsin
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
            // ── WebView ──────────────────────────────────────────────────────
            if (_ctrl != null && !_offline)
              WebViewWidget(controller: _ctrl!),

            // ── Offline sahifa ───────────────────────────────────────────────
            if (_offline)
              _OfflinePage(onRetry: _tryReload, isDark: isDark),

            // ── Splash / Loading ─────────────────────────────────────────────
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
                // Ikonka
                Container(
                  width: 88, height: 88,
                  decoration: BoxDecoration(
                    color: card,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Icon(Icons.wifi_off_rounded,
                      size: 44,
                      color: lbl3),
                ),
                const SizedBox(height: 24),
                Text('Internet aloqasi yo\'q',
                    style: TextStyle(
                        fontSize: 20, fontWeight: FontWeight.w700,
                        color: lbl)),
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

// ─────────────────────────────────────────────────────────────────────────────
// File chooser bottom sheet
// ─────────────────────────────────────────────────────────────────────────────
class _FileChooserSheet extends StatelessWidget {
  final bool acceptsImage;
  final bool acceptsVideo;
  const _FileChooserSheet(
      {required this.acceptsImage, required this.acceptsVideo});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? const Color(0xFF1C1C1E) : Colors.white;
    final lbl = isDark ? Colors.white : Colors.black;

    return Container(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      ),
      padding: const EdgeInsets.fromLTRB(0, 8, 0, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Container(
            width: 36, height: 5,
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: lbl.withValues(alpha: .2),
              borderRadius: BorderRadius.circular(3),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
            child: Text('Fayl tanlash',
                style: TextStyle(
                    fontSize: 17, fontWeight: FontWeight.w600, color: lbl)),
          ),
          const SizedBox(height: 8),
          if (acceptsImage) ...[
            _tile(context, Icons.camera_alt_rounded,
                'Kamera (rasm)', 'camera_photo', Colors.orange),
            _tile(context, Icons.photo_library_rounded,
                'Galereya (rasm)', 'gallery_image', Colors.blue),
            _tile(context, Icons.photo_library_outlined,
                'Bir nechta rasm', 'gallery_multi', Colors.purple),
          ],
          if (acceptsVideo) ...[
            _tile(context, Icons.videocam_rounded,
                'Kamera (video)', 'camera_video', Colors.red),
            _tile(context, Icons.video_library_rounded,
                'Galereya (video)', 'gallery_video', Colors.teal),
          ],
          if (!acceptsImage && !acceptsVideo) ...[
            _tile(context, Icons.camera_alt_rounded,
                'Kamera', 'camera_photo', Colors.orange),
            _tile(context, Icons.photo_library_rounded,
                'Galereya', 'gallery_image', Colors.blue),
          ],
          const SizedBox(height: 8),
          _tile(context, Icons.close_rounded, 'Bekor qilish', null,
              Colors.grey),
        ],
      ),
    );
  }

  Widget _tile(BuildContext ctx, IconData icon, String label,
      String? value, Color color) {
    final isDark = Theme.of(ctx).brightness == Brightness.dark;
    return ListTile(
      leading: Container(
        width: 40, height: 40,
        decoration: BoxDecoration(
          color: color.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: color, size: 22),
      ),
      title: Text(label,
          style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: isDark ? Colors.white : Colors.black)),
      onTap: () => Navigator.of(ctx).pop(value),
    );
  }
}
