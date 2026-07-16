import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/api_service.dart';
import '../core/constants.dart';
import '../core/notification_service.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';
import '../models/order_model.dart';
import '../widgets/order_card.dart';
import '../widgets/skeleton_card.dart';
import 'history_screen.dart';
import 'login_screen.dart';
import 'profile_screen.dart';
import 'chat_screen.dart';
import 'map_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  int _tab = 0;
  DriverModel? _driver;
  List<OrderModel> _orders = [];
  bool _loadingOrders = true;
  bool _togglingDuty  = false;
  Timer? _refreshTimer;
  int _activeOrderCount = 0;
  int _nextRefreshIn = 30;
  final Set<int> _knownOrderIds = {};
  bool _firstLoad = true;
  double? _lat;
  String? _address;
  bool _fetchingAddress = false;
  int _chatUnread = 0;

  // ── Taximetr holatlar ───────────────────────────────────────────────────────
  bool   _taxiRunning  = false;
  bool   _taxiPaused   = false;   // ← YANGI: pause holati
  double _taxiKm       = 0.0;
  double _taxiFare     = 0.0;
  double? _taxiPrevLat;
  double? _taxiPrevLng;
  Timer?  _taxiTimer;
  double _baseFare     = 5000;
  double _farePerKm    = 2000;
  // Pause vaqtini hisoblash uchun
  DateTime? _taxiPauseStart;
  Duration  _taxiTotalPaused = Duration.zero;  // jami to'xtatilgan vaqt
  DateTime? _taxiStartTime;                    // taximetr boshlangan vaqt

  // ── Destination Mode ────────────────────────────────────────────────────────
  bool   _destMode    = false;
  String _destAddress = '';
  double? _destLat;
  double? _destLng;
  bool   _settingDest = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _init();
    // Manzilni darhol olish (timer kutmasdan)
    Future.delayed(const Duration(seconds: 2), _updateDriverLocation);
    _refreshTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;

      // Har soniyada ekrandagi yangi buyurtmalarni vaqtini 1 ga kamaytirib turamiz (smooth countdown)
      setState(() {
        for (var i = 0; i < _orders.length; i++) {
          final o = _orders[i];
          if (o.isPending && o.secondsLeft != null && o.secondsLeft! > 0) {
            _orders[i] = o.copyWithSecondsLeft(o.secondsLeft! - 1);
          }
        }
      });

      final onDuty = _driver?.isOnDuty ?? false;

      setState(() {
        // Vizual kutish vaqti har doim 30 soniyadan orqaga sanaydi, haydovchi adashmasligi uchun
        _nextRefreshIn = 30 - (t.tick % 30);
      });

      // Orqa fonda esa navbatchilikda har 2 sekundda, off-duty bo'lsa har 30 sekundda yuklaymiz
      final orderInterval = onDuty ? 2 : 30;
      if (t.tick % orderInterval == 0) {
        _loadOrders(silent: true);
      }
      if (t.tick % 15 == 0) _updateDriverLocation();
      if (t.tick % 10 == 0) _loadChatUnread();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _loadOrders(silent: true);
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _taxiTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // ── Taximetr metodlari ──────────────────────────────────────────────────────

  void _startTaximeter() {
    if (_taxiRunning) return;
    setState(() {
      _taxiRunning      = true;
      _taxiPaused       = false;
      _taxiKm           = 0.0;
      _taxiFare         = _baseFare;
      _taxiPrevLat      = null;
      _taxiPrevLng      = null;
      _taxiStartTime    = DateTime.now();
      _taxiTotalPaused  = Duration.zero;
      _taxiPauseStart   = null;
    });
    _taxiTimer = Timer.periodic(const Duration(seconds: 2), (_) => _taxiTick());
  }

  void _pauseTaximeter() {
    if (!_taxiRunning || _taxiPaused) return;
    setState(() {
      _taxiPaused     = true;
      _taxiPauseStart = DateTime.now();
      _taxiPrevLat    = null;  // GPS o'rnini reset — qayta boshlanganda yangi nuqtadan
      _taxiPrevLng    = null;
    });
  }

  void _resumeTaximeter() {
    if (!_taxiRunning || !_taxiPaused) return;
    setState(() {
      if (_taxiPauseStart != null) {
        _taxiTotalPaused += DateTime.now().difference(_taxiPauseStart!);
        _taxiPauseStart   = null;
      }
      _taxiPaused  = false;
      _taxiPrevLat = null;
      _taxiPrevLng = null;
    });
  }

  void _stopTaximeter() {
    _taxiTimer?.cancel();
    _taxiTimer = null;
    if (_taxiPaused && _taxiPauseStart != null) {
      _taxiTotalPaused += DateTime.now().difference(_taxiPauseStart!);
    }
    if (mounted) setState(() {
      _taxiRunning    = false;
      _taxiPaused     = false;
      _taxiPauseStart = null;
    });
  }

  // Taximetr ishlayotgan umumiy vaqt (pause vaqtisiz)
  Duration get _taxiNetDuration {
    if (_taxiStartTime == null) return Duration.zero;
    final total = DateTime.now().difference(_taxiStartTime!);
    final paused = _taxiPaused && _taxiPauseStart != null
        ? _taxiTotalPaused + DateTime.now().difference(_taxiPauseStart!)
        : _taxiTotalPaused;
    final net = total - paused;
    return net.isNegative ? Duration.zero : net;
  }

  String get _taxiDurationLabel {
    final d = _taxiNetDuration;
    final h = d.inHours;
    final m = d.inMinutes % 60;
    final s = d.inSeconds % 60;
    if (h > 0) return '${h}s ${m}d';
    if (m > 0) return '${m}d ${s}s';
    return '${s}s';
  }

  Future<void> _taxiTick() async {
    if (_taxiPaused) return;  // ← Pause bo'lsa GPS o'lchamaydi
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 3),
      );
      final lat = pos.latitude;
      final lng = pos.longitude;

      if (!mounted) return;

      if (_taxiPrevLat != null && _taxiPrevLng != null) {
        final distM = Geolocator.distanceBetween(
          _taxiPrevLat!, _taxiPrevLng!, lat, lng,
        );
        if (distM > 3) {  // 3 metrdan kichik harakat hisoblanmaydi (GPS shimirilishi)
          final addedKm = distM / 1000.0;
          setState(() {
            _taxiKm   += addedKm;
            _taxiFare  = _baseFare + (_taxiKm * _farePerKm);
          });
        }
      }

      setState(() {
        _taxiPrevLat = lat;
        _taxiPrevLng = lng;
      });

      // Joylashuvni backend ga ham yuborib qo'yamiz
      try { await ApiService.updateLocation(lat, lng); } catch (_) {}
    } catch (_) {}
  }

  void _callClient(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Future<bool> _checkLocationPermission() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return false;

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return false;
    }
    if (permission == LocationPermission.deniedForever) return false;
    return true;
  }

  Future<void> _updateDriverLocation() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        if (mounted) setState(() => _address = 'GPS o\'chirilgan');
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        if (mounted) setState(() => _address = 'GPS ruxsati berilmagan');
        return;
      }

      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );
      final lat = pos.latitude;
      final lng = pos.longitude;
      if (mounted) setState(() { _lat = lat; });

      try { await ApiService.updateLocation(lat, lng); } catch (_) {}

      if (!_fetchingAddress) {
        _fetchingAddress = true;
        try {
          final addr = await ApiService.reverseGeocode(lat, lng);
          if (mounted) setState(() { _address = addr ?? '$lat, $lng'; });
        } catch (_) {
          if (mounted) setState(() { _address = '$lat, $lng'; });
        }
        _fetchingAddress = false;
      }
    } catch (e) {
      _fetchingAddress = false;
      if (mounted && _address == null) setState(() => _address = 'Manzil aniqlanmadi');
    }
  }

  Future<void> _init() async {
    await Future.wait([
      _loadProfile(),
      _loadOrders(),
      _loadChatUnread(),
      _loadTariff(),
      _loadDestinationMode(),
    ]);
  }

  Future<void> _loadChatUnread() async {
    try {
      final count = await ApiService.getChatUnreadCount();
      if (mounted) setState(() => _chatUnread = count);
    } catch (_) {}
  }

  // ── Tariff yuklash ────────────────────────────────────────────────────────

  Future<void> _loadTariff() async {
    try {
      final data = await ApiService.getTariff();
      if (mounted) {
        setState(() {
          _baseFare  = double.tryParse(data['base_price']?.toString() ?? '') ?? _baseFare;
          _farePerKm = double.tryParse(data['price_per_km']?.toString() ?? '') ?? _farePerKm;
        });
      }
    } catch (_) {}
  }

  // ── Destination mode ──────────────────────────────────────────────────────

  Future<void> _loadDestinationMode() async {
    try {
      final data = await ApiService.getDestinationMode();
      if (mounted) {
        setState(() {
          _destMode    = data['destination_mode'] as bool? ?? false;
          _destAddress = data['destination_address'] as String? ?? '';
          _destLat     = (data['destination_lat'] as num?)?.toDouble();
          _destLng     = (data['destination_lng'] as num?)?.toDouble();
        });
      }
    } catch (_) {}
  }

  Future<void> _toggleDestinationMode() async {
    if (_settingDest) return;

    if (_destMode) {
      // O'chirish
      setState(() => _settingDest = true);
      try {
        await ApiService.setDestinationMode(enabled: false);
        setState(() {
          _destMode    = false;
          _destAddress = '';
          _destLat     = null;
          _destLng     = null;
        });
        _snack("Yo'nalish rejimi o'chirildi", icon: Icons.navigation_outlined);
        await _loadOrders(silent: true);
      } catch (e) {
        _snack(e.toString(), error: true);
      } finally {
        if (mounted) setState(() => _settingDest = false);
      }
    } else {
      // Yoqish — hozirgi manzilni yo'nalish sifatida belgilash
      await _showDestinationSheet();
    }
  }

  Future<void> _showDestinationSheet() async {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final addrCtrl = TextEditingController(text: _address ?? '');

    await showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSheetState) => Padding(
          padding: EdgeInsets.only(
              bottom: MediaQuery.of(context).viewInsets.bottom),
          child: Container(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 28),
            decoration: BoxDecoration(
              color: dark ? AppColors.cardDark : Colors.white,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(28)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Center(
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 12),
                    width: 36, height: 4,
                    decoration: BoxDecoration(
                      color: dark
                          ? Colors.grey.shade700
                          : Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
                // Header
                Row(
                  children: [
                    Container(
                      width: 44, height: 44,
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(13),
                      ),
                      child: const Icon(Icons.navigation_rounded,
                          color: AppColors.primary, size: 22),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "Uyga yo'nalish rejimi",
                            style: TextStyle(
                              fontSize: 17, fontWeight: FontWeight.w900,
                              color: dark ? Colors.white : AppColors.textPrimary,
                              letterSpacing: -0.3,
                            ),
                          ),
                          Text(
                            'Faqat uy yo\'nalishi bo\'yicha buyurtmalar',
                            style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey.shade500),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Manzil input
                Text(
                  "YO'NALISH MANZILI",
                  style: TextStyle(
                    fontSize: 10, fontWeight: FontWeight.w900,
                    color: Colors.grey.shade500, letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: addrCtrl,
                  style: TextStyle(
                    fontSize: 14, fontWeight: FontWeight.w600,
                    color: dark ? Colors.white : AppColors.textPrimary,
                  ),
                  decoration: InputDecoration(
                    hintText: 'Masalan: Yunusobod, 19-kvartal',
                    filled: true,
                    fillColor: dark
                        ? AppColors.surfaceDark
                        : const Color(0xFFF2F2F2),
                    prefixIcon: const Icon(Icons.location_on_rounded,
                        color: AppColors.danger, size: 20),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide.none,
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide.none,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: const BorderSide(
                          color: AppColors.primary, width: 2),
                    ),
                  ),
                ),

                // Hozirgi manzil tugmasi
                if (_lat != null) ...[
                  const SizedBox(height: 10),
                  GestureDetector(
                    onTap: () {
                      addrCtrl.text = _address ?? '';
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.info.withValues(alpha: 0.07),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: AppColors.info.withValues(alpha: 0.2)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.my_location_rounded,
                              size: 14, color: AppColors.info),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Hozirgi manzilni ishlatish: ${_address ?? ''}',
                              style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.info,
                                  fontWeight: FontWeight.w700),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 20),

                // Yoqish tugmasi
                SizedBox(
                  height: 54,
                  child: ElevatedButton.icon(
                    onPressed: () async {
                      final addr = addrCtrl.text.trim();
                      if (addr.isEmpty) {
                        return;
                      }
                      Navigator.pop(ctx);
                      setState(() => _settingDest = true);
                      try {
                        // Koordinata: hozirgi joylashuv yoki null
                        final lat = _lat;
                        final lng = (await _getCurrentLng());
                        await ApiService.setDestinationMode(
                          enabled: true,
                          lat: lat,
                          lng: lng,
                          address: addr,
                        );
                        setState(() {
                          _destMode    = true;
                          _destAddress = addr;
                          _destLat     = lat;
                          _destLng     = lng;
                        });
                        _snack("Yo'nalish rejimi yoqildi",
                            icon: Icons.navigation_rounded);
                        await _loadOrders(silent: true);
                      } catch (e) {
                        _snack(e.toString(), error: true);
                      } finally {
                        if (mounted) setState(() => _settingDest = false);
                      }
                    },
                    icon: const Icon(Icons.navigation_rounded, size: 18),
                    label: const Text("Yo'nalishni belgilash",
                        style: TextStyle(
                            fontSize: 15, fontWeight: FontWeight.w900)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<double?> _getCurrentLng() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      ).timeout(const Duration(seconds: 5));
      return pos.longitude;
    } catch (_) {
      return null;
    }
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiService.getProfile();
      if (mounted) {
        setState(() {
          _driver = DriverModel.fromJson(data);
        });
      }
    } on ApiException catch (e) {
      if (e.isUnauthorized && mounted) _forceLogout();
    } catch (_) {}
  }

  Future<void> _loadOrders({bool silent = false}) async {
    if (!silent) setState(() => _loadingOrders = true);
    try {
      final list = await ApiService.getAvailableOrders();
      if (mounted) {
        final orders = list.map((e) => OrderModel.fromJson(e)).toList();

        // ── Faol buyurtmalar (isActive) doim tepada, pending lar keyin ──
        orders.sort((a, b) {
          int priority(OrderModel o) {
            if (o.isActive) return 0;  // accepted/on_way/arrived → tepa
            if (o.isPending) return 1; // pending → o'rta
            return 2;                  // boshqalar → past
          }
          final pd = priority(a) - priority(b);
          if (pd != 0) return pd;
          // Bir xil prioritet bo'lsa — yangirog'i tepada
          return b.createdAt.compareTo(a.createdAt);
        });

        final pendingOrders = orders.where((o) => o.isPending).toList();
        if (pendingOrders.isEmpty) {
          NotificationService.stopOrderSound();
        }

        if (!_firstLoad && _driver?.isOnDuty == true) {
          final newOrders = pendingOrders
              .where((o) => !_knownOrderIds.contains(o.id))
              .toList();

          if (newOrders.isNotEmpty) {
            await NotificationService.notifyNewOrder(newOrders.length);
            HapticFeedback.vibrate();
          }
        }

        _knownOrderIds.clear();
        _knownOrderIds.addAll(orders.map((o) => o.id));
        _firstLoad = false;

        setState(() {
          _orders = orders;
          // Faqat pending buyurtmalar asosiy ekranda ko'rsatiladi
          // isActive buyurtmalar Tarix ekraniga o'tadi
          _activeOrderCount = orders.where((o) => o.isActive).length;
          _loadingOrders = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loadingOrders = false);
        if (!silent) _snack(e.toString(), error: true);
      }
    }
  }

  Future<void> _toggleDuty() async {
    HapticFeedback.mediumImpact();
    setState(() => _togglingDuty = true);
    try {
      final data = await ApiService.toggleDuty();
      final nowOnDuty = data['is_on_duty'] as bool? ?? !(_driver?.isOnDuty ?? false);
      if (mounted && _driver != null) {
        setState(() {
          _driver = DriverModel(
            id: _driver!.id, fullName: _driver!.fullName,
            phoneNumber: _driver!.phoneNumber, carModel: _driver!.carModel,
            carNumber: _driver!.carNumber, isActive: _driver!.isActive,
            isOnDuty: nowOnDuty, approvalStatus: _driver!.approvalStatus,
            balance: _driver!.balance,
          );
        });
      }
      _snack(
        nowOnDuty ? 'Ish navbati boshlandi 🟢' : 'Ish navbati tugatildi',
        icon: nowOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
      );
      if (nowOnDuty) {
        _updateDriverLocation();
      }
    } catch (e) {
      _snack(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _togglingDuty = false);
    }
  }

  Future<void> _orderAction(OrderModel order, String action) async {
    HapticFeedback.mediumImpact();

    // ── Reject (rad etish) alohida API ─────────────────────────────────────
    if (action == 'reject') {
      try {
        await ApiService.rejectOrder(order.id);
        _snack('Buyurtma rad etildi', icon: Icons.close_rounded);
        await _loadOrders(silent: true);
      } catch (e) {
        _snack(e.toString(), error: true);
      }
      return;
    }

    final ep = {
      'accept':   AppConstants.acceptOrder(order.id),
      'on_way':   AppConstants.onWayOrder(order.id),
      'arrived':  AppConstants.arrivedOrder(order.id),
      'complete': AppConstants.completeOrder(order.id),
      'cancel':   AppConstants.cancelOrder(order.id),
    }[action];
    if (ep == null) return;
    try {
      await ApiService.orderAction(ep);
      _snack(_actionLabel(action), icon: _actionIcon(action));

      // ── Qabul qilinganda: ovozni to'xtat + mijozga avtomatik qo'ng'iroq + Tarix tabiga o'tish ──
      if (action == 'accept') {
        await NotificationService.stopOrderSound();
        if (mounted) setState(() => _tab = 1);
        if (order.clientPhone.isNotEmpty &&
            !order.clientPhone.contains('*')) {
          await Future.delayed(const Duration(milliseconds: 600));
          _callClient(order.clientPhone);
        }
      }

      // ── Yo'lga chiqdim: taximeterni ishga tush ──────────────────────────
      if (action == 'on_way') {
        _startTaximeter();
      }

      // ── Yetib keldim yoki yakunlash: taximeterni to'xtat ───────────────
      if (action == 'arrived' || action == 'complete' || action == 'cancel') {
        _stopTaximeter();
      }

      await Future.wait([_loadOrders(silent: true), _loadProfile()]);
    } on ApiException catch (e) {
      if (e.statusCode == 409) {
        if (mounted) {
          setState(() => _orders.removeWhere((o) => o.id == order.id));
          _snack('Bu buyurtmani boshqa haydovchi qabul qildi', error: true, icon: Icons.person_rounded);
        }
        await _loadOrders(silent: true);
      } else {
        _snack(e.toString(), error: true);
      }
    } catch (e) {
      _snack(e.toString(), error: true);
    }
  }

  String _actionLabel(String a) => const {
    'accept':   'Buyurtma qabul qilindi ✓',
    'on_way':   "Yo'lda ketmoqdasiz 🚗",
    'arrived':  'Yetib keldingiz 📍',
    'complete': 'Buyurtma yakunlandi 🏁',
    'cancel':   'Buyurtma bekor qilindi',
    'reject':   'Buyurtma rad etildi',
  }[a] ?? '';

  IconData _actionIcon(String a) => const {
    'accept':   Icons.check_circle_rounded,
    'on_way':   Icons.directions_car_rounded,
    'arrived':  Icons.location_on_rounded,
    'complete': Icons.flag_rounded,
    'cancel':   Icons.cancel_rounded,
  }[a] ?? Icons.info_rounded;

  void _snack(String msg, {bool error = false, IconData? icon}) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(
        content: Row(children: [
          if (icon != null) ...[Icon(icon, color: Colors.white, size: 20), const SizedBox(width: 12)],
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13))),
        ]),
        backgroundColor: error ? AppColors.danger : (dark ? AppColors.cardDark : AppColors.textPrimary),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: const EdgeInsets.all(20),
        elevation: 4,
        duration: Duration(seconds: error ? 4 : 2),
      ));
  }

  void _forceLogout() async {
    await ApiService.logout();
    if (mounted) {
      Navigator.pushAndRemoveUntil(context,
          MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false);
    }
  }

  Future<void> _logout() async {
    await ApiService.logout();
    if (mounted) {
      Navigator.pushAndRemoveUntil(context,
          MaterialPageRoute(builder: (_) => const LoginScreen()), (_) => false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      drawer: _drawer(dark),
      body: IndexedStack(
        index: _tab,
        children: [
          _ordersTab(dark),
          HistoryScreen(onOrderAction: _orderAction),
          const ChatScreen(),
          ProfileScreen(driver: _driver, onLogout: _logout),
        ],
      ),
      bottomNavigationBar: _navBar(dark),
    );
  }

  Widget _drawer(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    final balNeg = balance < 0;
    return Drawer(
      backgroundColor: dark ? AppColors.bgDark : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(right: Radius.circular(0)),
      ),
      child: Column(
        children: [
          // ── Header (qora fon, sariq accent) ─────────────────────────────
          Container(
            width: double.infinity,
            padding: EdgeInsets.fromLTRB(
                20, MediaQuery.of(context).padding.top + 28, 20, 24),
            color: AppColors.bgDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Avatar
                Container(
                  width: 64, height: 64,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Center(
                    child: Text(
                      _driver?.fullName.isNotEmpty == true
                          ? _driver!.fullName[0].toUpperCase() : '?',
                      style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 26, fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Text(
                  _driver?.fullName ?? '...',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18, fontWeight: FontWeight.w900,
                      letterSpacing: -0.3),
                ),
                const SizedBox(height: 3),
                Text(
                  _driver?.phoneNumber ?? '',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 13, fontFamily: 'monospace'),
                ),
                const SizedBox(height: 14),
                // Balance pill
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceDark,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: (balNeg ? AppColors.danger : AppColors.primary)
                            .withValues(alpha: 0.35)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.account_balance_wallet_rounded,
                          color: balNeg ? AppColors.danger : AppColors.primary,
                          size: 16),
                      const SizedBox(width: 8),
                      Text(
                        '${balance.toStringAsFixed(0)} UZS',
                        style: TextStyle(
                            color: balNeg ? AppColors.danger : AppColors.primary,
                            fontWeight: FontWeight.w900, fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── Menu ─────────────────────────────────────────────────────────
          Expanded(
            child: Container(
              color: dark ? AppColors.cardDark : Colors.white,
              child: Column(
                children: [
                  const SizedBox(height: 12),
                  _drawerItem(dark, Icons.radar_rounded, 'Bosh sahifa', 0),
                  _drawerItem(dark, Icons.history_rounded, 'Tarix', 1),
                  _drawerItem(dark, Icons.chat_bubble_rounded, 'Operator Chat',
                      2, badge: _chatUnread > 0 ? _chatUnread : null),
                  _drawerItem(dark, Icons.person_rounded, 'Profil', 3),
                  const Spacer(),
                  Divider(
                      height: 1,
                      color: dark ? AppColors.borderDark : AppColors.borderLight),
                  _drawerItem(dark, Icons.logout_rounded, 'Tizimdan chiqish', -1,
                      color: AppColors.danger),
                  const SizedBox(height: 8),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _drawerItem(bool dark, IconData icon, String label, int index,
      {int? badge, Color? color}) {
    final active = _tab == index && index != -1;
    final baseColor = dark ? Colors.grey.shade300 : const Color(0xFF1A1A1A);
    final c = color ?? (active ? AppColors.primary : baseColor);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
      child: ListTile(
        onTap: () {
          Navigator.pop(context);
          if (index == -1) {
            _logout();
          } else {
            setState(() => _tab = index);
          }
        },
        leading: Container(
          width: 40, height: 40,
          decoration: BoxDecoration(
            color: active
                ? AppColors.primary.withValues(alpha: 0.15)
                : (dark ? AppColors.surfaceDark : const Color(0xFFF3F4F6)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, size: 20, color: c),
        ),
        title: Text(
          label,
          style: TextStyle(
            fontWeight: active ? FontWeight.w900 : FontWeight.w600,
            fontSize: 14, color: c,
          ),
        ),
        trailing: badge != null
            ? Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.danger,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text('$badge',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w900)),
              )
            : active
                ? Container(
                    width: 6, height: 6,
                    decoration: const BoxDecoration(
                        color: AppColors.primary, shape: BoxShape.circle),
                  )
                : null,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        minLeadingWidth: 0,
      ),
    );
  }

  Widget _navBar(bool dark) {
    return Container(
      decoration: BoxDecoration(
        color: dark ? AppColors.bgDark : Colors.white,
        border: Border(
          top: BorderSide(
            color: dark ? AppColors.borderDark : AppColors.borderLight,
            width: 0.5,
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
          child: Row(
            children: [
              _navItem(0, Icons.radar_rounded, Icons.radar, 'Asosiy', dark),
              _navItem(1, Icons.history_outlined, Icons.history_rounded,
                  'Tarix', dark),
              _navItem(
                2,
                Icons.chat_bubble_outline_rounded,
                Icons.chat_bubble_rounded,
                'Chat',
                dark,
                badge: _chatUnread > 0 ? _chatUnread : null,
              ),
              _navItem(
                3,
                Icons.person_outline_rounded,
                Icons.person_rounded,
                'Profil',
                dark,
                dot: _driver?.isOnDuty == true,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navItem(int index, IconData icon, IconData activeIcon,
      String label, bool dark, {int? badge, bool dot = false}) {
    final active = _tab == index;
    final activeColor = dark ? AppColors.primary : AppColors.textPrimary;
    final inactiveColor =
        dark ? Colors.grey.shade600 : Colors.grey.shade400;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _tab = index);
        },
        behavior: HitTestBehavior.opaque,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
              decoration: BoxDecoration(
                color: active
                    ? (dark
                        ? AppColors.primary.withValues(alpha: 0.12)
                        : AppColors.textPrimary.withValues(alpha: 0.08))
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Stack(
                clipBehavior: Clip.none,
                alignment: Alignment.center,
                children: [
                  Icon(
                    active ? activeIcon : icon,
                    size: 24,
                    color: active ? activeColor : inactiveColor,
                  ),
                  if (badge != null)
                    Positioned(
                      top: -5, right: -8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppColors.danger,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: dark ? AppColors.bgDark : Colors.white,
                              width: 1.5),
                        ),
                        child: Text('$badge',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 9,
                                fontWeight: FontWeight.w900)),
                      ),
                    )
                  else if (dot)
                    Positioned(
                      top: -3, right: -3,
                      child: Container(
                        width: 7, height: 7,
                        decoration: BoxDecoration(
                          color: AppColors.success,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: dark ? AppColors.bgDark : Colors.white,
                              width: 1.5),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 2),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 200),
              style: TextStyle(
                fontSize: 10,
                fontWeight:
                    active ? FontWeight.w800 : FontWeight.w500,
                color: active ? activeColor : inactiveColor,
              ),
              child: Text(label),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ordersTab(bool dark) {
    final onDuty = _driver?.isOnDuty ?? false;
    return RefreshIndicator(
      onRefresh: _init,
      color: AppColors.primary,
      strokeWidth: 2.5,
      child: Column(
        children: [
          _header(dark),
          Expanded(
            child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                if (!onDuty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: _offlineState(dark),
                  )
                else ...[
                  SliverToBoxAdapter(child: _onlineStatusHeader(dark)),
                  if (_activeOrderCount > 0)
                    SliverToBoxAdapter(child: _activeBadgeBanner(dark)),
                  SliverToBoxAdapter(child: _ordersLabel(dark)),
                  if (_loadingOrders)
                    SliverPadding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      sliver: SliverList(
                          delegate: SliverChildBuilderDelegate(
                              (_, __) => const SkeletonCard(),
                              childCount: 2)),
                    )
                  else if (_orders.where((o) => o.isPending).isEmpty)
                    SliverFillRemaining(
                      hasScrollBody: false,
                      child: _searchingState(dark),
                    )
                  else
                    _buildOrdersSliver(),
                ]
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _header(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    final balNeg = balance < 0;
    final balColor = balNeg ? AppColors.danger : AppColors.primary;
    final onDuty = _driver?.isOnDuty ?? false;

    return Container(
      padding: EdgeInsets.fromLTRB(
          16, MediaQuery.of(context).padding.top + 10, 16, 12),
      color: dark ? AppColors.bgDark : Colors.white,
      child: Row(
        children: [
          // Hamburger
          Builder(
            builder: (ctx) => GestureDetector(
              onTap: () => Scaffold.of(ctx).openDrawer(),
              child: Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: dark ? AppColors.surfaceDark : const Color(0xFFF2F2F2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _menuLine(dark),
                        const SizedBox(height: 5),
                        _menuLine(dark, width: 12),
                        const SizedBox(height: 5),
                        _menuLine(dark),
                      ],
                    ),
                    if (_chatUnread > 0)
                      Positioned(
                        top: 8, right: 8,
                        child: Container(
                          width: 8, height: 8,
                          decoration: const BoxDecoration(
                              color: AppColors.danger,
                              shape: BoxShape.circle),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),

          // Name + status
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _driver?.fullName ?? 'Yuklanmoqda...',
                  style: TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w900,
                    letterSpacing: -0.3,
                    color: dark ? Colors.white : AppColors.textPrimary,
                  ),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    Container(
                      width: 7, height: 7,
                      decoration: BoxDecoration(
                        color: onDuty
                            ? AppColors.success
                            : Colors.grey.shade500,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      onDuty ? 'Ish navbatida' : 'Oflayn',
                      style: TextStyle(
                        fontSize: 11, fontWeight: FontWeight.w700,
                        color: onDuty
                            ? AppColors.success
                            : Colors.grey.shade500,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Balance chip
          GestureDetector(
            onTap: () => setState(() => _tab = 3),
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF2F2F2),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                    color: balColor.withValues(alpha: 0.35), width: 1.2),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'BALANS',
                    style: TextStyle(
                        fontSize: 8, fontWeight: FontWeight.w800,
                        color: Colors.grey.shade500, letterSpacing: 0.8),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    '${balance.toStringAsFixed(0)} so\'m',
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                        color: balColor),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _menuLine(bool dark, {double width = 18}) => Container(
    width: width, height: 2,
    decoration: BoxDecoration(
      color: dark ? Colors.grey.shade500 : const Color(0xFF1A1A1A),
      borderRadius: BorderRadius.circular(1),
    ),
  );

  Widget _onlineStatusHeader(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    final balNeg = balance < 0;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
      child: Column(
        children: [
          // ── Destination mode banner ──────────────────────────────────────
          if (_destMode)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color: AppColors.primary.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 32, height: 32,
                      decoration: BoxDecoration(
                        color: AppColors.primary.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(9),
                      ),
                      child: const Icon(Icons.navigation_rounded,
                          color: AppColors.primary, size: 17),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            "Yo'nalish rejimi faol",
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w900,
                              color: AppColors.primary,
                            ),
                          ),
                          Text(
                            _destAddress.isNotEmpty
                                ? _destAddress
                                : 'Belgilangan yo\'nalish',
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.grey.shade500,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: _settingDest ? null : _toggleDestinationMode,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppColors.danger.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: AppColors.danger
                                  .withValues(alpha: 0.25)),
                        ),
                        child: Text(
                          "O'chirish",
                          style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: AppColors.danger),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // ── Stat kartalar ──────────────────────────────────────────────
          Row(
            children: [
              _statusCard(
                Icons.list_alt_rounded,
                '$_activeOrderCount ta',
                'Faol buyurtma',
                AppColors.info,
                dark,
              ),
              const SizedBox(width: 10),
              _statusCard(
                Icons.account_balance_wallet_rounded,
                "${balance.toStringAsFixed(0)} so'm",
                balNeg ? 'Qarzdorlik' : 'Balans',
                balNeg ? AppColors.danger : AppColors.success,
                dark,
              ),
            ],
          ),
          const SizedBox(height: 10),

          // ── Joylashuv + Tugatish ──────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: dark ? AppColors.cardDark : Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                  color: AppColors.success.withValues(alpha: 0.25)),
            ),
            child: Row(
              children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.success.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.wifi_rounded,
                      color: AppColors.success, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Ish navbatidasiz',
                        style: TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 13,
                          color: AppColors.success,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Icon(
                            _address != null
                                ? Icons.location_on_rounded
                                : Icons.gps_fixed_rounded,
                            size: 11,
                            color: Colors.grey.shade500,
                          ),
                          const SizedBox(width: 3),
                          Expanded(
                            child: Text(
                              _address ??
                                  (_lat != null
                                      ? 'Manzil aniqlanmoqda...'
                                      : 'GPS qidirilmoqda...'),
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey.shade500,
                                fontWeight: FontWeight.w600,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
                _togglingDuty
                    ? const SizedBox(
                        width: 22, height: 22,
                        child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: AppColors.danger))
                    : GestureDetector(
                        onTap: _toggleDuty,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 8),
                          decoration: BoxDecoration(
                            color: AppColors.danger
                                .withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: AppColors.danger
                                    .withValues(alpha: 0.3)),
                          ),
                          child: const Text(
                            'Tugatish',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w900,
                              color: AppColors.danger,
                            ),
                          ),
                        ),
                      ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusCard(
      IconData icon, String value, String label, Color color, bool dark) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: color.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value,
                    style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w900,
                        color: color),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 1),
                  Text(
                    label,
                    style: TextStyle(
                        fontSize: 10, color: Colors.grey.shade500,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _offlineState(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 8, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),

            // ── Katta Yandex-uslub pulse tugmasi ─────────────────────────
            _OfflinePulseButton(
              onTap: _togglingDuty ? null : _toggleDuty,
              loading: _togglingDuty,
            ),
            const SizedBox(height: 28),

            Text(
              'Oflayn',
              style: TextStyle(
                fontSize: 30, fontWeight: FontWeight.w900,
                letterSpacing: -1,
                color: dark ? Colors.white : AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Ish navbatini boshlang va\nbuyurtmalar qabul qiling',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14, color: Colors.grey.shade500,
                height: 1.6,
              ),
            ),
            const SizedBox(height: 28),

            // ── Tezkor statistika karta ───────────────────────────────────
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: dark ? AppColors.cardDark : Colors.white,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                    color: dark ? AppColors.borderDark : AppColors.borderLight),
              ),
              child: Row(
                children: [
                  _offlineStat(
                    Icons.account_balance_wallet_rounded,
                    '${balance.toStringAsFixed(0)}',
                    'Balans (so\'m)',
                    balance >= 0 ? AppColors.success : AppColors.danger,
                    dark,
                  ),
                  Container(
                    width: 1, height: 44,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    color: dark ? AppColors.borderDark : AppColors.borderLight,
                  ),
                  _offlineStat(
                    Icons.directions_car_rounded,
                    _driver?.carNumber ?? '—',
                    'Mashina',
                    AppColors.info,
                    dark,
                  ),
                  Container(
                    width: 1, height: 44,
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    color: dark ? AppColors.borderDark : AppColors.borderLight,
                  ),
                  _offlineStat(
                    Icons.star_rounded,
                    '5.0',
                    'Reyting',
                    AppColors.warning,
                    dark,
                  ),
                ],
              ),
            ),

            if (_driver?.approvalStatus != null &&
                _driver!.approvalStatus != 'approved') ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                      color: AppColors.warning.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 36, height: 36,
                      decoration: BoxDecoration(
                        color: AppColors.warning.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.info_outline_rounded,
                          color: AppColors.warning, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _driver!.approvalStatus == 'rejected'
                            ? "Hisobingiz rad etilgan. Administrator bilan bog'laning."
                            : 'Hisobingiz tasdiqlanishi kutilmoqda.',
                        style: const TextStyle(
                          fontSize: 13, color: AppColors.warning,
                          fontWeight: FontWeight.w700, height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _offlineStat(
      IconData icon, String value, String label, Color color, bool dark) {
    return Expanded(
      child: Column(
        children: [
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w900,
              color: dark ? Colors.white : AppColors.textPrimary,
            ),
            textAlign: TextAlign.center,
            maxLines: 1, overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(
                fontSize: 9, color: Colors.grey.shade500,
                fontWeight: FontWeight.w600),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _searchingState(bool dark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 160, height: 160,
              child: _RadarScanner(),
            ),
            const SizedBox(height: 28),
            Text(
              'Buyurtmalar qidirilmoqda',
              style: TextStyle(
                fontSize: 18, fontWeight: FontWeight.w900,
                color: dark ? Colors.white : AppColors.textPrimary,
                letterSpacing: -0.4,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Yaqin atrofdagi arizalar skanlanmoqda.\nYangilanish: ${_nextRefreshIn}s',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13, color: Colors.grey.shade500, height: 1.6,
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _activeBadgeBanner(bool dark) => GestureDetector(
    onTap: () => setState(() => _tab = 1), // Tarix ekraniga o'tish
    child: Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: AppColors.info.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.info.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Container(
              width: 8, height: 8,
              decoration: const BoxDecoration(
                  color: AppColors.info, shape: BoxShape.circle),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                '$_activeOrderCount ta faol buyurtma davom etmoqda',
                style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: AppColors.info),
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded,
                size: 13, color: AppColors.info),
          ],
        ),
      ),
    ),
  );

  Widget _ordersLabel(bool dark) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 16, 16, 10),
    child: Row(
      children: [
        Text(
          'ATROFDAGI BUYURTMALAR',
          style: TextStyle(
            fontSize: 11, fontWeight: FontWeight.w900,
            color: Colors.grey.shade500, letterSpacing: 1,
          ),
        ),
        const Spacer(),
        if (!_loadingOrders && _orders.where((o) => o.isPending).isNotEmpty)
          Container(
            margin: const EdgeInsets.only(right: 8),
            padding: const EdgeInsets.symmetric(
                horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '${_orders.where((o) => o.isPending).length} ta',
              style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary),
            ),
          ),
        // Destination mode toggle tugmasi
        GestureDetector(
          onTap: _settingDest ? null : _toggleDestinationMode,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            padding: const EdgeInsets.symmetric(
                horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: _destMode
                  ? AppColors.primary.withValues(alpha: 0.12)
                  : (dark
                      ? AppColors.surfaceDark
                      : const Color(0xFFF2F2F2)),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _destMode
                    ? AppColors.primary.withValues(alpha: 0.4)
                    : (dark
                        ? AppColors.borderDark
                        : AppColors.borderLight),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _settingDest
                    ? const SizedBox(
                        width: 12, height: 12,
                        child: CircularProgressIndicator(
                            strokeWidth: 1.5,
                            color: AppColors.primary))
                    : Icon(
                        Icons.navigation_rounded,
                        size: 13,
                        color: _destMode
                            ? AppColors.primary
                            : Colors.grey.shade500,
                      ),
                const SizedBox(width: 5),
                Text(
                  _destMode ? "Yo'nalish" : "Uy yo'nalishi",
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: _destMode
                        ? AppColors.primary
                        : Colors.grey.shade500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );

  Widget _buildOrderCard(OrderModel order) => OrderCard(
    order: order,
    onAction: (a) => _orderAction(order, a),
    onTap: () => _showOrderDetail(order),
    liveKm:       order.isOnWay && _taxiRunning ? _taxiKm   : null,
    liveFare:     order.isOnWay && _taxiRunning ? _taxiFare : null,
    taxiPaused:   order.isOnWay && _taxiRunning && _taxiPaused,
    taxiDuration: order.isOnWay && _taxiRunning ? _taxiDurationLabel : null,
    onTaxiPause:  order.isOnWay && _taxiRunning ? (_taxiPaused ? _resumeTaximeter : _pauseTaximeter) : null,
  );

  // Faqat pending buyurtmalar ko'rsatiladi — faol buyurtmalar Tarix ekranida
  Widget _buildOrdersSliver() {
    final pending = _orders.where((o) => o.isPending).toList();

    return SliverPadding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
      sliver: SliverList(
        delegate: SliverChildListDelegate(
          pending.map(_buildOrderCard).toList(),
        ),
      ),
    );
  }

  void _showOrderDetail(OrderModel order) {
    HapticFeedback.selectionClick();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _OrderDetailSheet(
        order: order,
        onAction: (a) { Navigator.pop(context); _orderAction(order, a); },
        onOpenMap: () {
          Navigator.pop(context);
          Navigator.push(context, MaterialPageRoute(
            builder: (_) => MapScreen(activeOrder: order),
          ));
        },
        liveKm:       order.isOnWay && _taxiRunning ? _taxiKm   : null,
        liveFare:     order.isOnWay && _taxiRunning ? _taxiFare : null,
        taxiPaused:   order.isOnWay && _taxiRunning && _taxiPaused,
        taxiDuration: order.isOnWay && _taxiRunning ? _taxiDurationLabel : null,
        onTaxiPause:  order.isOnWay && _taxiRunning ? (_taxiPaused ? _resumeTaximeter : _pauseTaximeter) : null,
      ),
    );
  }
}

class _OrderDetailSheet extends StatelessWidget {
  final OrderModel order;
  final void Function(String) onAction;
  final VoidCallback? onOpenMap;
  final double? liveKm;
  final double? liveFare;
  final bool taxiPaused;
  final String? taxiDuration;
  final VoidCallback? onTaxiPause;
  const _OrderDetailSheet({
    required this.order,
    required this.onAction,
    this.onOpenMap,
    this.liveKm,
    this.liveFare,
    this.taxiPaused = false,
    this.taxiDuration,
    this.onTaxiPause,
  });

  Color get _statusColor {
    return switch (order.status) {
      'pending'   => AppColors.warning,
      'accepted'  => AppColors.info,
      'on_way'    => AppColors.purple,
      'completed' => AppColors.success,
      'cancelled' => AppColors.danger,
      _           => Colors.grey,
    };
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 14, bottom: 20),
              width: 36, height: 4,
              decoration: BoxDecoration(
                color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Header row
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 18),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _statusColor,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '#${order.id}',
                    style: const TextStyle(
                        color: Colors.black,
                        fontWeight: FontWeight.w900,
                        fontSize: 13),
                  ),
                ),
                const SizedBox(width: 12),
                const Text(
                  'Buyurtma tafsiloti',
                  style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.4),
                ),
                const Spacer(),
                if (onOpenMap != null)
                  GestureDetector(
                    onTap: onOpenMap,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppColors.success.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.success.withValues(alpha: 0.3)),
                      ),
                      child: const Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.map_rounded, size: 14, color: AppColors.success),
                        SizedBox(width: 4),
                        Text('Xarita', style: TextStyle(fontSize: 11,
                            fontWeight: FontWeight.w800, color: AppColors.success)),
                      ]),
                    ),
                  )
                else
                  Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: _statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: _statusColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    order.statusLabel,
                    style: TextStyle(
                        color: _statusColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
          ),

          // Route card
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF7F7F7),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                    color: dark
                        ? AppColors.borderDark
                        : AppColors.borderLight),
              ),
              child: Column(
                children: [
                  _infoRow(Icons.radio_button_checked_rounded,
                      AppColors.success, 'MIJOZ MANZILI', order.fromAddress),
                  if (order.toAddress.isNotEmpty) ...[
                    Padding(
                      padding: const EdgeInsets.only(left: 15),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Column(
                          children: List.generate(
                            3,
                            (_) => Container(
                              margin: const EdgeInsets.symmetric(vertical: 2),
                              width: 2, height: 5,
                              color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                            ),
                          ),
                        ),
                      ),
                    ),
                    _infoRow(Icons.location_on_rounded, AppColors.danger, 'QAYERGA', order.toAddress),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Client and Price Details
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Container(
                        width: 44, height: 44,
                        decoration: BoxDecoration(
                          color: AppColors.info.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.person_rounded, color: AppColors.info, size: 22),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              order.clientName.isNotEmpty ? order.clientName : 'Nomsiz mijoz',
                              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
                            ),
                            const SizedBox(height: 2),
                            GestureDetector(
                              onTap: () async {
                                final uri = Uri(scheme: 'tel', path: order.clientPhone);
                                if (await canLaunchUrl(uri)) launchUrl(uri);
                              },
                              child: Row(
                                children: [
                                  const Icon(Icons.call_rounded, size: 13, color: AppColors.info),
                                  const SizedBox(width: 4),
                                  Text(
                                    order.clientPhone,
                                    style: const TextStyle(
                                      fontSize: 12, color: AppColors.info,
                                      fontFamily: 'monospace', fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (order.price != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                          decoration: BoxDecoration(
                            color: AppColors.success.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '${order.price} UZS',
                            style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.success, fontSize: 13),
                          ),
                        ),
                    ],
                  ),
                  if (order.distanceKm != null || order.commission != null) ...[
                    const SizedBox(height: 12),
                    const Divider(),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        if (order.distanceKm != null)
                          Expanded(
                            child: Row(
                              children: [
                                const Icon(Icons.map_rounded, size: 14, color: AppColors.purple),
                                const SizedBox(width: 6),
                                Text(
                                  'Masofa: ${order.distanceKm!.toStringAsFixed(1)} km',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.purple),
                                ),
                              ],
                            ),
                          ),
                        if (order.commission != null)
                          Expanded(
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                const Icon(Icons.remove_circle_outline_rounded, size: 14, color: AppColors.danger),
                                const SizedBox(width: 6),
                                Text(
                                  'Komissiya: ${order.commission} UZS',
                                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.danger),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // 🚖 Taximetr banner (yo'lda ketayotganda)
          if (order.isOnWay && liveKm != null) ...[         
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: taxiPaused
                        ? [const Color(0xFFf59e0b), const Color(0xFFd97706)]
                        : [const Color(0xFF1DB954), const Color(0xFF0d7c3b)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: (taxiPaused
                          ? const Color(0xFFf59e0b)
                          : const Color(0xFF1DB954)).withValues(alpha: 0.3),
                      blurRadius: 12, offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Icon(
                          taxiPaused ? Icons.pause_circle_filled_rounded : Icons.speed_rounded,
                          color: Colors.white, size: 28,
                        ),
                        const SizedBox(width: 14),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              taxiPaused ? 'TAXIMETR TO\'XTATILDI' : 'TAXIMETR',
                              style: const TextStyle(
                                color: Colors.white70, fontSize: 10,
                                fontWeight: FontWeight.w900, letterSpacing: 1.5,
                              ),
                            ),
                            Text(
                              '${liveKm!.toStringAsFixed(2)} km',
                              style: const TextStyle(
                                color: Colors.white, fontSize: 22,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                        const Spacer(),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            const Text('NARX', style: TextStyle(
                              color: Colors.white70, fontSize: 10,
                              fontWeight: FontWeight.w900, letterSpacing: 1.5,
                            )),
                            Text(
                              '${liveFare!.toStringAsFixed(0)} so\'m',
                              style: const TextStyle(
                                color: Colors.white, fontSize: 20,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    // Vaqt + Pause/Resume tugmasi
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        // Vaqt
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.timer_rounded, color: Colors.white70, size: 13),
                              const SizedBox(width: 5),
                              Text(
                                taxiDuration ?? '0s',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 12, fontWeight: FontWeight.w800,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const Spacer(),
                        // Pause / Resume tugmasi
                        if (onTaxiPause != null)
                          GestureDetector(
                            onTap: onTaxiPause,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: Colors.white.withValues(alpha: 0.4)),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    taxiPaused ? Icons.play_arrow_rounded : Icons.pause_rounded,
                                    color: Colors.white, size: 18,
                                  ),
                                  const SizedBox(width: 6),
                                  Text(
                                    taxiPaused ? 'Davom ettirish' : 'To\'xtatish',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 13, fontWeight: FontWeight.w900,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                    if (taxiPaused) ...[
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.info_outline_rounded, color: Colors.white70, size: 13),
                            SizedBox(width: 6),
                            Text(
                              'Yolovchi do\'kon/uyda — narx hisoblanmayapti',
                              style: TextStyle(
                                color: Colors.white70, fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],

          const SizedBox(height: 24),

          // ── Qo'ng'iroq tugmasi (accepted/on_way/arrived da) ──────────────
          if ((order.isAccepted || order.isOnWay || order.isArrived) &&
              order.clientPhone.isNotEmpty &&
              !order.clientPhone.contains('*'))
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: SizedBox(
                height: 54,
                child: ElevatedButton.icon(
                  onPressed: () async {
                    final uri = Uri(scheme: 'tel', path: order.clientPhone);
                    if (await canLaunchUrl(uri)) launchUrl(uri);
                  },
                  icon: const Icon(Icons.call_rounded, size: 20),
                  label: Text(
                    'Qo\'ng\'iroq qilish  ${order.clientPhone}',
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w900),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.success,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16)),
                    elevation: 0,
                  ),
                ),
              ),
            ),

          // Action buttons
          if (order.isPending || order.isAccepted || order.isOnWay || order.isArrived)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(
                children: [
                  if (order.isPending)
                    _actionBtn(context, 'Qabul qilish', Icons.check_circle_rounded, AppColors.primary, 'accept'),
                  if (order.isAccepted) ...[
                    _actionBtn(context, "Yo'lga chiqdim", Icons.directions_car_rounded, AppColors.purple, 'on_way'),
                    const SizedBox(height: 10),
                  ],
                  if (order.isOnWay) ...[
                    _actionBtn(context, 'Yetib keldim', Icons.location_on_rounded, AppColors.info, 'arrived'),
                    const SizedBox(height: 10),
                  ],
                  if (order.isArrived) ...[
                    _actionBtn(context, 'Yakunlash', Icons.flag_rounded, AppColors.success, 'complete'),
                    const SizedBox(height: 10),
                  ],
                  if (order.isAccepted || order.isOnWay || order.isArrived)
                    _actionBtn(context, 'Bekor qilish', Icons.cancel_rounded, AppColors.danger, 'cancel', outlined: true),
                ],
              ),
            ),

          SizedBox(height: MediaQuery.of(context).padding.bottom + 12),
        ],
      ),
    );
  }

  Widget _infoRow(IconData icon, Color color, String label, String value) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Icon(icon, size: 18, color: color),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 9, color: Colors.grey, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
            const SizedBox(height: 2),
            Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    ],
  );

  Widget _actionBtn(BuildContext ctx, String label, IconData icon, Color color, String action,
      {bool outlined = false}) {
    if (outlined) {
      return SizedBox(
        width: double.infinity, height: 52,
        child: OutlinedButton.icon(
          onPressed: () => onAction(action),
          icon: Icon(icon, size: 18),
          label: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
          style: OutlinedButton.styleFrom(
            foregroundColor: color,
            side: BorderSide(color: color.withValues(alpha: 0.6), width: 1.5),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
      );
    }
    return SizedBox(
      width: double.infinity, height: 52,
      child: ElevatedButton.icon(
        onPressed: () => onAction(action),
        icon: Icon(icon, size: 18),
        label: Text(label, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        style: ElevatedButton.styleFrom(
          backgroundColor: color, foregroundColor: Colors.black,
          elevation: 2,
          shadowColor: color.withValues(alpha: 0.3),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
    );
  }
}

// ── Yandex-uslub pulsatsiyali oflayn tugmasi ────────────────────────────────
class _OfflinePulseButton extends StatefulWidget {
  final VoidCallback? onTap;
  final bool loading;
  const _OfflinePulseButton({required this.onTap, required this.loading});
  @override
  State<_OfflinePulseButton> createState() => _OfflinePulseButtonState();
}

class _OfflinePulseButtonState extends State<_OfflinePulseButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pCtrl;

  @override
  void initState() {
    super.initState();
    _pCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
  }

  @override
  void dispose() {
    _pCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: SizedBox(
        width: 220, height: 220,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Pulsatsiyali halqa 1
            AnimatedBuilder(
              animation: _pCtrl,
              builder: (_, __) {
                final v = _pCtrl.value;
                return Container(
                  width: 130 + (80 * v),
                  height: 130 + (80 * v),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.success.withValues(alpha: (1 - v) * 0.35),
                      width: 2,
                    ),
                  ),
                );
              },
            ),
            // Pulsatsiyali halqa 2 (kechiktirilgan)
            AnimatedBuilder(
              animation: _pCtrl,
              builder: (_, __) {
                final v = (_pCtrl.value + 0.5) % 1.0;
                return Container(
                  width: 130 + (80 * v),
                  height: 130 + (80 * v),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.success.withValues(alpha: (1 - v) * 0.35),
                      width: 2,
                    ),
                  ),
                );
              },
            ),
            // Yashil glow
            Container(
              width: 136, height: 136,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.success.withValues(alpha: 0.07),
              ),
            ),
            // Asosiy tugma
            Container(
              width: 118, height: 118,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(
                  colors: [AppColors.success, Color(0xFF16a34a)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.success.withValues(alpha: 0.45),
                    blurRadius: 30, spreadRadius: 6,
                  ),
                ],
              ),
              child: widget.loading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 3,
                      ))
                  : const Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.power_settings_new_rounded,
                          size: 42, color: Colors.white,
                        ),
                        SizedBox(height: 5),
                        Text(
                          'BOSHLASH',
                          style: TextStyle(
                            color: Colors.white, fontSize: 11,
                            fontWeight: FontWeight.w900, letterSpacing: 1.5,
                          ),
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

class _RadarScanner extends StatefulWidget {
  const _RadarScanner();
  @override
  State<_RadarScanner> createState() => _RadarScannerState();
}

class _RadarScannerState extends State<_RadarScanner> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (ctx, child) {
        return CustomPaint(
          painter: _RadarPainter(_c.value),
          child: Center(
            child: Container(
              width: 56, height: 56,
              decoration: BoxDecoration(
                color: AppColors.primary,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.4),
                    blurRadius: 16,
                  )
                ],
              ),
              child: const Icon(Icons.navigation_rounded, color: Colors.black, size: 26),
            ),
          ),
        );
      },
    );
  }
}

class _RadarPainter extends CustomPainter {
  final double progress;
  _RadarPainter(this.progress);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    for (int i = 0; i < 3; i++) {
      final currentProgress = (progress + i / 3) % 1.0;
      final radius = maxRadius * currentProgress;
      final opacity = (1.0 - currentProgress).clamp(0.0, 1.0);

      final paint = Paint()
        ..color = AppColors.primary.withValues(alpha: opacity * 0.25)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(center, radius, paint);

      final borderPaint = Paint()
        ..color = AppColors.primary.withValues(alpha: opacity * 0.5)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0;

      canvas.drawCircle(center, radius, borderPaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
