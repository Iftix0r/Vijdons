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
  bool   _taxiRunning  = false;   // taximetr ishlayaptimi
  double _taxiKm       = 0.0;     // bosib o'tilgan km
  double _taxiFare     = 0.0;     // hisoblangan narx (UZS)
  double? _taxiPrevLat;           // oldingi koordinata
  double? _taxiPrevLng;
  Timer?  _taxiTimer;             // 2-soniyalik GPS taymer
  // taximetr sozlamalari (TariffSettings dan olinadi, tezroq demo uchun default)
  double _baseFare     = 5000;
  double _farePerKm    = 2000;

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
            _orders[i] = OrderModel(
              id: o.id,
              clientName: o.clientName,
              clientPhone: o.clientPhone,
              driverName: o.driverName,
              fromAddress: o.fromAddress,
              toAddress: o.toAddress,
              price: o.price,
              commission: o.commission,
              distanceKm: o.distanceKm,
              status: o.status,
              statusLabel: o.statusLabel,
              createdAt: o.createdAt,
              paymentType: o.paymentType,
              note: o.note,
              secondsLeft: o.secondsLeft! - 1,
            );
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
      _taxiRunning = true;
      _taxiKm      = 0.0;
      _taxiFare    = _baseFare;  // boshlang'ich narxdan boshlanadi
      _taxiPrevLat = null;
      _taxiPrevLng = null;
    });
    _taxiTimer = Timer.periodic(const Duration(seconds: 2), (_) => _taxiTick());
  }

  void _stopTaximeter() {
    _taxiTimer?.cancel();
    _taxiTimer = null;
    if (mounted) setState(() => _taxiRunning = false);
  }

  Future<void> _taxiTick() async {
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
      final hasPermission = await _checkLocationPermission();
      if (!hasPermission) return;

      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 5),
      );
      final lat = pos.latitude;
      final lng = pos.longitude;
      if (mounted) setState(() { _lat = lat; });

      // Backend ga yuborish (alohida try/catch - manzil olishni bloklamasin)
      try { await ApiService.updateLocation(lat, lng); } catch (_) {}

      // Manzilni har doim yangilash (flag tiqilib qolmasin)
      if (!_fetchingAddress) {
        _fetchingAddress = true;
        try {
          final addr = await ApiService.reverseGeocode(lat, lng);
          if (mounted) setState(() { _address = addr ?? _address; });
        } catch (_) {}
        _fetchingAddress = false;
      }
    } catch (_) {
      _fetchingAddress = false;
    }
  }

  Future<void> _init() async {
    await Future.wait([_loadProfile(), _loadOrders(), _loadChatUnread()]);
  }

  Future<void> _loadChatUnread() async {
    try {
      final count = await ApiService.getChatUnreadCount();
      if (mounted) setState(() => _chatUnread = count);
    } catch (_) {}
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
    final ep = {
      'accept':   AppConstants.acceptOrder(order.id),
      'on_way':   AppConstants.onWayOrder(order.id),
      'arrived':  AppConstants.arrivedOrder(order.id),
      'complete': AppConstants.completeOrder(order.id),
      'cancel':   AppConstants.cancelOrder(order.id),
    }[action]!;
    try {
      await ApiService.orderAction(ep);
      _snack(_actionLabel(action), icon: _actionIcon(action));

      // ── Qabul qilinganda: ovozni to'xtat + mijozga avtomatik qo'ng'iroq ──
      if (action == 'accept') {
        await NotificationService.stopOrderSound();
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
          const HistoryScreen(),
          const ChatScreen(),
          ProfileScreen(driver: _driver, onLogout: _logout),
        ],
      ),
      bottomNavigationBar: _navBar(dark),
    );
  }

  Widget _drawer(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    return Drawer(
      backgroundColor: dark ? AppColors.cardDark : Colors.white,
      child: SafeArea(
        child: Column(
          children: [
            // Header
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
              decoration: const BoxDecoration(
                color: AppColors.primary,
                border: Border(bottom: BorderSide(
                  color: AppColors.primaryDark)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 60, height: 60,
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.15),
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Text(
                        _driver?.fullName.isNotEmpty == true
                            ? _driver!.fullName[0].toUpperCase() : '?',
                        style: const TextStyle(color: AppColors.textPrimary,
                            fontSize: 24, fontWeight: FontWeight.w900),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _driver?.fullName ?? '...',
                    style: const TextStyle(color: AppColors.textPrimary,
                        fontSize: 17, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    _driver?.phoneNumber ?? '',
                    style: TextStyle(color: AppColors.textPrimary.withValues(alpha: 0.6),
                        fontSize: 13, fontFamily: 'monospace'),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.black.withValues(alpha: 0.2)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.account_balance_wallet_rounded,
                            color: AppColors.textPrimary, size: 16),
                        const SizedBox(width: 8),
                        Text(
                          '${balance.toStringAsFixed(0)} UZS',
                          style: const TextStyle(color: AppColors.textPrimary,
                              fontWeight: FontWeight.w900, fontSize: 14),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // Menu items
            _drawerItem(dark, Icons.radar_rounded, 'Bosh sahifa', 0),
            _drawerItem(dark, Icons.history_rounded, 'Buyurtmalar tarixi', 1),
            _drawerItem(dark, Icons.chat_bubble_rounded, 'Operator Chat',
                2, badge: _chatUnread > 0 ? _chatUnread : null),
            _drawerItem(dark, Icons.person_rounded, 'Profil', 3),

            const Spacer(),

            Divider(color: dark ? AppColors.borderDark : AppColors.borderLight),
            _drawerItem(dark, Icons.logout_rounded, 'Tizimdan chiqish', -1,
                color: AppColors.danger),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }

  Widget _drawerItem(bool dark, IconData icon, String label, int index,
      {int? badge, Color? color}) {
    final active = _tab == index;
    final c = color ?? (active ? AppColors.primary : (dark ? Colors.grey.shade300 : const Color(0xFF374151)));
    return ListTile(
      onTap: () {
        Navigator.pop(context);
        if (index == -1) {
          _logout();
        } else {
          setState(() => _tab = index);
        }
      },
      leading: Container(
        width: 38, height: 38,
        decoration: BoxDecoration(
          color: c.withValues(alpha: active ? 0.15 : 0.07),
          borderRadius: BorderRadius.circular(10),
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
                  style: const TextStyle(color: Colors.white,
                      fontSize: 11, fontWeight: FontWeight.w900)),
            )
          : active
              ? Container(
                  width: 6, height: 6,
                  decoration: const BoxDecoration(
                      color: AppColors.primary, shape: BoxShape.circle),
                )
              : null,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
    );
  }

  Widget _navBar(bool dark) {
    return Container(
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        border: Border(top: BorderSide(
            color: dark ? AppColors.borderDark : AppColors.borderLight, width: 0.8)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.3 : 0.06),
            blurRadius: 24, offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: [
              _navItem(0, Icons.radar_rounded, Icons.radar, 'Asosiy', dark),
              _navItem(1, Icons.history_outlined, Icons.history, 'Tarix', dark),
              _navItem(2, Icons.chat_bubble_outline_rounded,
                  Icons.chat_bubble_rounded, 'Chat', dark, badge: _chatUnread > 0 ? _chatUnread : null),
              _navItem(3, Icons.person_outline_rounded,
                  Icons.person_rounded, 'Profil', dark,
                  dot: _driver?.isOnDuty == true),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navItem(int index, IconData icon, IconData activeIcon,
      String label, bool dark, {int? badge, bool dot = false}) {
    final active = _tab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _tab = index);
        },
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(
            color: active
                ? AppColors.primary.withValues(alpha: dark ? 0.15 : 0.1)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  Icon(
                    active ? activeIcon : icon,
                    size: 24,
                    color: active
                        ? AppColors.primary
                        : (dark ? Colors.grey.shade500 : Colors.grey.shade400),
                  ),
                  if (badge != null)
                    Positioned(
                      top: -4, right: -6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppColors.danger,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                              color: dark ? AppColors.cardDark : Colors.white, width: 1.5),
                        ),
                        child: Text('$badge',
                            style: const TextStyle(color: Colors.white,
                                fontSize: 9, fontWeight: FontWeight.w900)),
                      ),
                    )
                  else if (dot)
                    Positioned(
                      top: -2, right: -2,
                      child: Container(
                        width: 8, height: 8,
                        decoration: BoxDecoration(
                          color: AppColors.success,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: dark ? AppColors.cardDark : Colors.white, width: 1.5),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 4),
              AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 200),
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: active ? FontWeight.w900 : FontWeight.w600,
                  color: active
                      ? AppColors.primary
                      : (dark ? Colors.grey.shade500 : Colors.grey.shade400),
                ),
                child: Text(label),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _ordersTab(bool dark) {
    final onDuty = _driver?.isOnDuty ?? false;
    return SafeArea(
      child: RefreshIndicator(
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
                    // Online Stats
                    SliverToBoxAdapter(child: _onlineStatusHeader(dark)),
                    if (_activeOrderCount > 0)
                      SliverToBoxAdapter(child: _activeBadgeBanner(dark)),
                    
                    SliverToBoxAdapter(child: _ordersLabel(dark)),
                    
                    if (_loadingOrders)
                      SliverPadding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        sliver: SliverList(delegate: SliverChildBuilderDelegate(
                          (_, __) => const SkeletonCard(), childCount: 2)),
                      )
                    else if (_orders.isEmpty)
                      SliverFillRemaining(
                        hasScrollBody: false,
                        child: _searchingState(dark),
                      )
                    else
                      SliverPadding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                        sliver: SliverList(delegate: SliverChildBuilderDelegate(
                          (ctx, i) => OrderCard(
                            order: _orders[i],
                            onAction: (a) => _orderAction(_orders[i], a),
                            onTap: () => _showOrderDetail(_orders[i]),
                            liveKm:   _orders[i].isOnWay && _taxiRunning ? _taxiKm   : null,
                            liveFare: _orders[i].isOnWay && _taxiRunning ? _taxiFare : null,
                          ),
                          childCount: _orders.length,
                        )),
                      ),
                  ]
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _header(bool dark) {
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    final balanceNeg = balance < 0;
    final balColor = balanceNeg ? AppColors.danger : AppColors.primary;
    final onDuty = _driver?.isOnDuty ?? false;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        border: Border(bottom: BorderSide(
            color: dark ? AppColors.borderDark : AppColors.borderLight, width: 0.8)),
      ),
      child: Row(
        children: [
          // Hamburger menu
          Builder(
            builder: (ctx) => GestureDetector(
              onTap: () => Scaffold.of(ctx).openDrawer(),
              child: Container(
                width: 42, height: 42,
                decoration: BoxDecoration(
                  color: dark ? AppColors.surfaceDark : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: dark ? AppColors.borderDark : AppColors.borderLight),
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _menuLine(dark),
                        const SizedBox(height: 4),
                        _menuLine(dark, width: 14),
                        const SizedBox(height: 4),
                        _menuLine(dark),
                      ],
                    ),
                    if (_chatUnread > 0)
                      Positioned(
                        top: 8, right: 8,
                        child: Container(
                          width: 8, height: 8,
                          decoration: const BoxDecoration(
                              color: AppColors.danger, shape: BoxShape.circle),
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
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: -0.2),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    Container(
                      width: 6, height: 6,
                      decoration: BoxDecoration(
                        color: onDuty ? AppColors.success : Colors.grey.shade400,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      onDuty ? 'Ish navbatida' : 'Oflayn',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: onDuty ? AppColors.success : Colors.grey.shade400,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Balance
          GestureDetector(
            onTap: () => setState(() => _tab = 3),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: balColor.withValues(alpha: 0.25)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text('BALANS',
                      style: TextStyle(fontSize: 8, fontWeight: FontWeight.w800,
                          color: Colors.grey, letterSpacing: 0.5)),
                  const SizedBox(height: 1),
                  Text(
                    '${balance.toStringAsFixed(0)} UZS',
                    style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w900, color: balColor),
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
      color: dark ? Colors.grey.shade400 : const Color(0xFF374151),
      borderRadius: BorderRadius.circular(1),
    ),
  );

  Widget _onlineStatusHeader(bool dark) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.verified_user_rounded, color: AppColors.primary, size: 22),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Siz ish navbatidasiz',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Icon(
                        _address != null ? Icons.location_on_rounded : Icons.gps_fixed_rounded,
                        size: 12,
                        color: _address != null ? AppColors.primary : Colors.grey.shade400,
                      ),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          _address ?? (_lat != null ? 'Manzil aniqlanmoqda...' : 'GPS qidirilmoqda...'),
                          style: TextStyle(
                            fontSize: 11,
                            color: _address != null ? Colors.grey.shade500 : Colors.grey.shade400,
                            fontWeight: FontWeight.w700,
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
            _togglingDuty
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : OutlinedButton(
                    onPressed: _toggleDuty,
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      side: BorderSide(color: AppColors.danger.withValues(alpha: 0.5)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      foregroundColor: AppColors.danger,
                    ),
                    child: const Text('Tugatish', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900)),
                  ),
          ],
        ),
      ),
    );
  }

  Widget _offlineState(bool dark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(28, 32, 28, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Offline icon
            Container(
              width: 130, height: 130,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: dark ? AppColors.cardDark : Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: dark ? 0.3 : 0.04),
                    blurRadius: 30,
                  )
                ],
                border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight, width: 2),
              ),
              child: Center(
                child: Icon(
                  Icons.wifi_off_rounded,
                  size: 52,
                  color: dark ? Colors.grey.shade600 : Colors.grey.shade400,
                ),
              ),
            ),
            const SizedBox(height: 32),
            const Text(
              'Siz oflaynsiz',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, letterSpacing: -0.5),
            ),
            const SizedBox(height: 10),
            Text(
              'Yangi buyurtmalarni qabul qilish va boshlash uchun tizimni onlayn rejimiga o\'tkazing.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: Colors.grey.shade500, height: 1.6),
            ),
            const SizedBox(height: 40),
            SizedBox(
              width: double.infinity, height: 56,
              child: ElevatedButton(
                onPressed: _togglingDuty ? null : _toggleDuty,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.black,
                  shadowColor: AppColors.primary.withValues(alpha: 0.3),
                  elevation: 6,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: _togglingDuty
                    ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.black, strokeWidth: 3))
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.power_settings_new_rounded, size: 20),
                          SizedBox(width: 10),
                          Text('ISH NAVBATINI BOSHLASH', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
                        ],
                      ),
              ),
            ),
          ],
        ),
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
            // Radar Wave Animation
            const SizedBox(
              width: 160, height: 160,
              child: _RadarScanner(),
            ),
            const SizedBox(height: 32),
            const Text(
              'Buyurtmalar qidirilmoqda...',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            Text(
              'Yaqin atrofdagi faol arizalar qidirilmoqda.\nKutish: ${_nextRefreshIn}s',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade500, height: 1.5),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _activeBadgeBanner(bool dark) => Padding(
    padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.info.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.info.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            width: 8, height: 8,
            decoration: const BoxDecoration(color: AppColors.info, shape: BoxShape.circle),
          ),
          const SizedBox(width: 10),
          Text(
            '$_activeOrderCount ta faol buyurtma davom etmoqda',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: AppColors.info),
          ),
        ],
      ),
    ),
  );

  Widget _ordersLabel(bool dark) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
    child: Row(
      children: [
        const Text('ATROFDAGI BUYURTMALAR', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Colors.grey, letterSpacing: 0.8)),
        const Spacer(),
        if (!_loadingOrders && _orders.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '${_orders.length} ta',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppColors.primary),
            ),
          ),
      ],
    ),
  );

  void _showOrderDetail(OrderModel order) {
    HapticFeedback.selectionClick();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _OrderDetailSheet(
        order: order,
        onAction: (a) { Navigator.pop(context); _orderAction(order, a); },
        liveKm:   order.isOnWay && _taxiRunning ? _taxiKm   : null,
        liveFare: order.isOnWay && _taxiRunning ? _taxiFare : null,
      ),
    );
  }
}

class _OrderDetailSheet extends StatelessWidget {
  final OrderModel order;
  final void Function(String) onAction;
  final double? liveKm;
  final double? liveFare;
  const _OrderDetailSheet({
    required this.order,
    required this.onAction,
    this.liveKm,
    this.liveFare,
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
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight, width: 0.8),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag Handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 18),
              width: 38, height: 4,
              decoration: BoxDecoration(
                color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          
          // Order ID + Title + Status
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: _statusColor,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '#${order.id}',
                    style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 13),
                  ),
                ),
                const SizedBox(width: 12),
                const Text(
                  'Tafsilotlar',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: -0.5),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: _statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: _statusColor.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    order.statusLabel,
                    style: TextStyle(color: _statusColor, fontSize: 12, fontWeight: FontWeight.w800),
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
                color: dark ? AppColors.surfaceDark : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
              ),
              child: Column(
                children: [
                  _infoRow(Icons.radio_button_checked_rounded, AppColors.success, 'MIJOZ MANZILI', order.fromAddress),
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
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1DB954), Color(0xFF0d7c3b)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF1DB954).withValues(alpha: 0.3),
                      blurRadius: 12, offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    const Icon(Icons.speed_rounded, color: Colors.white, size: 28),
                    const SizedBox(width: 14),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('TAXIMETR', style: TextStyle(
                          color: Colors.white70, fontSize: 10,
                          fontWeight: FontWeight.w900, letterSpacing: 1.5,
                        )),
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
              ),
            ),
            const SizedBox(height: 12),
          ],

          const SizedBox(height: 24),

          // Action buttons
          if (order.isPending || order.isAccepted || order.isOnWay)
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
