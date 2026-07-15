import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:geolocator/geolocator.dart';
import '../core/api_service.dart';
import '../core/constants.dart';
import '../core/notification_service.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';
import '../models/order_model.dart';
import '../widgets/order_card.dart';
import '../widgets/skeleton_card.dart';
import 'login_screen.dart';
import 'history_screen.dart';
import 'profile_screen.dart';

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
  // Yangi buyurtmalarni aniqlash uchun avvalgi ID'lar ro'yxati
  final Set<int> _knownOrderIds = {};
  bool _firstLoad = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _init();
    _refreshTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      setState(() => _nextRefreshIn = 30 - (t.tick % 30));
      if (t.tick % 30 == 0) _loadOrders(silent: true);
      if (_driver?.isOnDuty == true && t.tick % 15 == 0) {
        _updateDriverLocation();
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _loadOrders(silent: true);
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
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
      await ApiService.updateLocation(pos.latitude, pos.longitude);
    } catch (_) {}
  }

  Future<void> _init() async {
    await Future.wait([_loadProfile(), _loadOrders()]);
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiService.getProfile();
      if (mounted) setState(() => _driver = DriverModel.fromJson(data));
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

        // Faqat ish navbatida bo'lganda yangi buyurtmalarni aniqlash
        if (!_firstLoad && _driver?.isOnDuty == true) {
          final pendingOrders = orders.where((o) => o.isPending).toList();
          final newOrders = pendingOrders
              .where((o) => !_knownOrderIds.contains(o.id))
              .toList();

          if (newOrders.isNotEmpty) {
            // Ovoz va bildirishnoma chiqar
            await NotificationService.notifyNewOrder(newOrders.length);
            // Haptic feedback qo'shimcha
            HapticFeedback.vibrate();
          }
        }

        // Barcha ko'rinayotgan buyurtma ID'larini yangilash
        _knownOrderIds.clear();
        _knownOrderIds.addAll(orders.map((o) => o.id));
        _firstLoad = false;

        setState(() {
          _orders = orders;
          _activeOrderCount = orders.where((o) => o.isAccepted || o.isOnWay).length;
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
    HapticFeedback.lightImpact();
    final ep = {
      'accept':   AppConstants.acceptOrder(order.id),
      'on_way':   AppConstants.onWayOrder(order.id),
      'complete': AppConstants.completeOrder(order.id),
      'cancel':   AppConstants.cancelOrder(order.id),
    }[action]!;
    try {
      await ApiService.orderAction(ep);
      _snack(_actionLabel(action), icon: _actionIcon(action));
      await Future.wait([_loadOrders(silent: true), _loadProfile()]);
    } catch (e) {
      _snack(e.toString(), error: true);
    }
  }

  String _actionLabel(String a) => const {
    'accept':   'Buyurtma qabul qilindi ✓',
    'on_way':   "Yo'lda ketmoqdasiz 🚗",
    'complete': 'Buyurtma yakunlandi 🏁',
    'cancel':   'Buyurtma bekor qilindi',
  }[a] ?? '';

  IconData _actionIcon(String a) => const {
    'accept':   Icons.check_circle_rounded,
    'on_way':   Icons.directions_car_rounded,
    'complete': Icons.flag_rounded,
    'cancel':   Icons.cancel_rounded,
  }[a] ?? Icons.info_rounded;

  void _snack(String msg, {bool error = false, IconData? icon}) {
    ScaffoldMessenger.of(context)
      ..clearSnackBars()
      ..showSnackBar(SnackBar(
        content: Row(children: [
          if (icon != null) ...[Icon(icon, color: Colors.white, size: 18), const SizedBox(width: 10)],
          Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
        backgroundColor: error ? AppColors.danger : const Color(0xFF0F172A),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        margin: const EdgeInsets.all(16),
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

  // ── UI ─────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _tab,
        children: [
          _ordersTab(),
          const HistoryScreen(),
          ProfileScreen(driver: _driver, onLogout: _logout),
        ],
      ),
      bottomNavigationBar: _navBar(),
    );
  }

  Widget _navBar() {
    return NavigationBar(
      selectedIndex: _tab,
      onDestinationSelected: (i) {
        HapticFeedback.selectionClick();
        setState(() => _tab = i);
      },
      height: 64,
      destinations: [
        NavigationDestination(
          icon: Badge(
            isLabelVisible: _orders.isNotEmpty && _tab != 0,
            label: Text('${_orders.length}'),
            child: const Icon(Icons.route_outlined),
          ),
          selectedIcon: const Icon(Icons.route),
          label: 'Buyurtmalar',
        ),
        const NavigationDestination(
          icon: Icon(Icons.history_outlined),
          selectedIcon: Icon(Icons.history),
          label: 'Tarix',
        ),
        NavigationDestination(
          icon: Badge(
            isLabelVisible: _driver?.isOnDuty == true && _tab != 2,
            backgroundColor: AppColors.success,
            child: const Icon(Icons.person_outline_rounded),
          ),
          selectedIcon: const Icon(Icons.person_rounded),
          label: 'Profil',
        ),
      ],
    );
  }

  Widget _ordersTab() {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _init,
        color: AppColors.amber,
        strokeWidth: 2.5,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _header()),
            SliverToBoxAdapter(child: _dutyBanner()),
            if (_activeOrderCount > 0)
              SliverToBoxAdapter(child: _activeBadgeBanner()),
            SliverToBoxAdapter(child: _ordersLabel()),
            if (_loadingOrders)
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList(delegate: SliverChildBuilderDelegate(
                  (_, __) => const SkeletonCard(), childCount: 3)),
              )
            else if (_orders.isEmpty)
              SliverFillRemaining(child: _emptyState())
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList(delegate: SliverChildBuilderDelegate(
                  (ctx, i) => OrderCard(
                    order: _orders[i],
                    onAction: (a) => _orderAction(_orders[i], a),
                    onTap: () => _showOrderDetail(_orders[i]),
                  ),
                  childCount: _orders.length,
                )),
              ),
          ],
        ),
      ),
    );
  }

  Widget _header() {
    final hour = DateTime.now().hour;
    final greeting = hour < 5 ? 'Yaxshi tun 🌙'
        : hour < 12 ? 'Xayrli tong ☀️'
        : hour < 17 ? 'Xayrli kun 🌤'
        : hour < 21 ? 'Xayrli kech 🌆'
        : 'Yaxshi tun 🌙';
    final balance = double.tryParse(_driver?.balance ?? '') ?? 0;
    final balanceNeg = balance < 0;
    final balColor = balanceNeg ? AppColors.danger : AppColors.success;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(greeting,
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontWeight: FontWeight.w500)),
                const SizedBox(height: 2),
                Text(
                  _driver?.fullName ?? 'Yuklanmoqda...',
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, letterSpacing: -0.5),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                ),
                if (_driver != null)
                  GestureDetector(
                    onTap: () => setState(() => _tab = 2),
                    child: Container(
                      margin: const EdgeInsets.only(top: 5),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: balColor.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: balColor.withValues(alpha: 0.25)),
                      ),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        Icon(Icons.account_balance_wallet_rounded, size: 13, color: balColor),
                        const SizedBox(width: 5),
                        Text(
                          '${balance.toStringAsFixed(0)} UZS',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: balColor),
                        ),
                      ]),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          // Logo + refresh countdown
          Column(children: [
            Container(
              width: 48, height: 48,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF4ADE80), Color(0xFF16A34A)],
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [BoxShadow(color: AppColors.green.withValues(alpha: 0.35), blurRadius: 12, offset: const Offset(0, 4))],
              ),
              child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 26),
            ),
            const SizedBox(height: 4),
            Text('${_nextRefreshIn}s',
                style: TextStyle(fontSize: 10, color: Colors.grey.shade400, fontWeight: FontWeight.w600)),
          ]),
        ],
      ),
    );
  }

  Widget _dutyBanner() {
    final onDuty = _driver?.isOnDuty ?? false;
    final dark   = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
      child: GestureDetector(
        onTap: _togglingDuty ? null : _toggleDuty,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          decoration: BoxDecoration(
            gradient: onDuty
                ? const LinearGradient(
                    colors: [Color(0xFF059669), Color(0xFF10B981)],
                    begin: Alignment.topLeft, end: Alignment.bottomRight)
                : LinearGradient(colors: dark
                    ? [AppColors.cardDark, AppColors.surfaceDark]
                    : [const Color(0xFFF8FAFC), const Color(0xFFEEF2FF)]),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: onDuty ? Colors.transparent : Colors.grey.withValues(alpha: 0.15),
            ),
            boxShadow: onDuty
                ? [BoxShadow(color: AppColors.success.withValues(alpha: 0.4), blurRadius: 20, offset: const Offset(0, 8))]
                : [],
          ),
          child: Row(children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Icon(key: ValueKey(onDuty),
                onDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                color: onDuty ? Colors.white : Colors.grey.shade400, size: 28),
            ),
            const SizedBox(width: 14),
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 250),
                  child: Text(key: ValueKey(onDuty),
                    onDuty ? 'Ish navbatidasiz' : 'Ish navbatida emassiz',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14,
                        color: onDuty ? Colors.white : null)),
                ),
                Text(
                  onDuty ? '30s da avtomatik yangilanadi' : 'Bosing va ish boshlang',
                  style: TextStyle(fontSize: 11,
                      color: onDuty ? Colors.white60 : Colors.grey.shade500),
                ),
              ],
            )),
            _togglingDuty
                ? const SizedBox(width: 24, height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                : Switch.adaptive(
                    value: onDuty, onChanged: (_) => _toggleDuty(),
                    activeThumbColor: Colors.white,
                    activeTrackColor: Colors.white30,
                    inactiveThumbColor: Colors.grey.shade400,
                    inactiveTrackColor: Colors.grey.shade300,
                  ),
          ]),
        ),
      ),
    );
  }

  Widget _activeBadgeBanner() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.info.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.info.withValues(alpha: 0.2)),
      ),
      child: Row(children: [
        Container(width: 8, height: 8, decoration: const BoxDecoration(color: AppColors.info, shape: BoxShape.circle)),
        const SizedBox(width: 10),
        Text('$_activeOrderCount ta faol buyurtma davom etmoqda',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.info)),
      ]),
    ),
  );

  Widget _ordersLabel() => Padding(
    padding: const EdgeInsets.fromLTRB(20, 4, 20, 10),
    child: Row(children: [
      const Text('Yangi buyurtmalar', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      const Spacer(),
      if (!_loadingOrders && _orders.isNotEmpty)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: AppColors.amber.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text('${_orders.length} ta',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.amber)),
        ),
    ]),
  );

  Widget _emptyState() => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 80, height: 80,
          decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(24)),
          child: Icon(Icons.inbox_rounded, size: 42, color: Colors.grey.shade300)),
        const SizedBox(height: 18),
        const Text('Yangi buyurtmalar yo\'q',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
        const SizedBox(height: 8),
        Text('Buyurtma kelganda bu yerda ko\'rinadi.\n30 soniyada avtomatik yangilanadi.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.grey.shade500, height: 1.6)),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: _loadOrders,
          icon: const Icon(Icons.refresh_rounded, size: 16),
          label: const Text('Hozir yangilash'),
          style: OutlinedButton.styleFrom(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            side: BorderSide(color: Colors.grey.withValues(alpha: 0.3)),
          ),
        ),
      ]),
    ),
  );

  // ── Order detail bottom sheet ──────────────────────────────────────────────

  void _showOrderDetail(OrderModel order) {
    HapticFeedback.selectionClick();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _OrderDetailSheet(
        order: order,
        onAction: (a) { Navigator.pop(context); _orderAction(order, a); },
      ),
    );
  }
}

// ── Order detail sheet ─────────────────────────────────────────────────────────

class _OrderDetailSheet extends StatelessWidget {
  final OrderModel order;
  final void Function(String) onAction;
  const _OrderDetailSheet({required this.order, required this.onAction});

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
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 16),
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          // Order ID + status
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
            child: Row(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: _statusColor,
                  borderRadius: BorderRadius.circular(10),
                  boxShadow: [BoxShadow(color: _statusColor.withValues(alpha: 0.4), blurRadius: 8, offset: const Offset(0, 3))],
                ),
                child: Text('#${order.id}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
              const SizedBox(width: 12),
              Text('Buyurtma tafsilotlari',
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: _statusColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: _statusColor.withValues(alpha: 0.3)),
                ),
                child: Text(order.statusLabel,
                    style: TextStyle(color: _statusColor, fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ]),
          ),

          // Route card
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.withValues(alpha: 0.1)),
              ),
              child: Column(children: [
                _infoRow(Icons.my_location_rounded, AppColors.success, 'Qayerdan', order.fromAddress),
                Padding(
                  padding: const EdgeInsets.only(left: 16),
                  child: Column(children: List.generate(3, (_) => Container(
                    margin: const EdgeInsets.symmetric(vertical: 2),
                    width: 1.5, height: 6,
                    color: Colors.grey.withValues(alpha: 0.3),
                  ))),
                ),
                _infoRow(Icons.location_on_rounded, AppColors.danger, 'Qayerga', order.toAddress),
              ]),
            ),
          ),
          const SizedBox(height: 12),

          // Client info
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: dark ? AppColors.surfaceDark : const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.withValues(alpha: 0.1)),
              ),
              child: Column(children: [
                Row(children: [
                  Container(width: 42, height: 42,
                    decoration: BoxDecoration(
                      color: AppColors.info.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.person_rounded, color: AppColors.info, size: 20)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(order.clientName.isNotEmpty ? order.clientName : 'Nomsiz mijoz',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                      Text(order.clientPhone,
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontFamily: 'monospace')),
                    ],
                  )),
                  if (order.price != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppColors.success.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('${order.price} so\'m',
                          style: const TextStyle(fontWeight: FontWeight.bold,
                              color: AppColors.success, fontSize: 13)),
                    ),
                ]),
                if (order.distanceKm != null || order.commission != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Row(children: [
                      if (order.distanceKm != null)
                        Expanded(
                          child: Text('Masofa: ${order.distanceKm!.toStringAsFixed(1)} km',
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.info)),
                        ),
                      if (order.commission != null)
                        Expanded(
                          child: Text('Komissiya: ${order.commission} so\'m',
                              textAlign: TextAlign.right,
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.danger)),
                        ),
                    ]),
                  ),
              ]),
            ),
          ),
          const SizedBox(height: 20),

          // Action buttons
          if (order.isPending || order.isAccepted || order.isOnWay)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(children: [
                if (order.isPending)
                  _actionBtn(context, 'Qabul qilish', Icons.check_circle_rounded, AppColors.success, 'accept'),
                if (order.isAccepted) ...[
                  _actionBtn(context, "Yo'lga chiqdim", Icons.directions_car_rounded, AppColors.purple, 'on_way'),
                  const SizedBox(height: 8),
                ],
                if (order.isOnWay) ...[
                  _actionBtn(context, 'Yakunlash', Icons.flag_rounded, AppColors.success, 'complete'),
                  const SizedBox(height: 8),
                ],
                if (order.isAccepted || order.isOnWay)
                  _actionBtn(context, 'Bekor qilish', Icons.cancel_rounded, AppColors.danger, 'cancel', outlined: true),
              ]),
            ),

          SizedBox(height: MediaQuery.of(context).padding.bottom + 8),
        ],
      ),
    );
  }

  Widget _infoRow(IconData icon, Color color, String label, String value) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(width: 32, height: 32,
        decoration: BoxDecoration(color: color.withValues(alpha: 0.1), shape: BoxShape.circle),
        child: Icon(icon, size: 16, color: color)),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
      ])),
    ],
  );

  Widget _actionBtn(BuildContext ctx, String label, IconData icon, Color color, String action,
      {bool outlined = false}) {
    if (outlined) {
      return SizedBox(width: double.infinity, height: 50,
        child: OutlinedButton.icon(
          onPressed: () => onAction(action),
          icon: Icon(icon, size: 18),
          label: Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
          style: OutlinedButton.styleFrom(
            foregroundColor: color,
            side: BorderSide(color: color.withValues(alpha: 0.5), width: 1.5),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ));
    }
    return SizedBox(width: double.infinity, height: 50,
      child: ElevatedButton.icon(
        onPressed: () => onAction(action),
        icon: Icon(icon, size: 18),
        label: Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
        style: ElevatedButton.styleFrom(
          backgroundColor: color, foregroundColor: Colors.white,
          elevation: 0,
          shadowColor: color.withValues(alpha: 0.4),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ));
  }
}
