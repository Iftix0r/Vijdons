import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_service.dart';
import '../core/constants.dart';
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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _init();
    // Auto-refresh every 30 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (_tab == 0 && mounted) _loadOrders(silent: true);
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadOrders(silent: true);
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> _init() async {
    await Future.wait([_loadProfile(), _loadOrders()]);
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiService.getProfile();
      if (mounted) setState(() => _driver = DriverModel.fromJson(data));
    } catch (_) {}
  }

  Future<void> _loadOrders({bool silent = false}) async {
    if (!silent) setState(() => _loadingOrders = true);
    try {
      final list = await ApiService.getAvailableOrders();
      if (mounted) {
        setState(() {
          _orders = list.map((e) => OrderModel.fromJson(e)).toList();
          _loadingOrders = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loadingOrders = false);
        if (!silent) _showSnack(e.toString(), error: true);
      }
    }
  }

  Future<void> _toggleDuty() async {
    HapticFeedback.mediumImpact();
    setState(() => _togglingDuty = true);
    try {
      final data = await ApiService.toggleDuty();
      final nowOnDuty = data['is_on_duty'] as bool? ?? !(_driver?.isOnDuty ?? false);
      setState(() {
        if (_driver != null) {
          _driver = DriverModel(
            id: _driver!.id, fullName: _driver!.fullName,
            phoneNumber: _driver!.phoneNumber, carModel: _driver!.carModel,
            carNumber: _driver!.carNumber, isActive: _driver!.isActive,
            isOnDuty: nowOnDuty, approvalStatus: _driver!.approvalStatus,
          );
        }
      });
      _showSnack(
        nowOnDuty ? 'Ish navbati boshlandi' : 'Ish navbati tugatildi',
        error: false,
        icon: nowOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
      );
    } catch (e) {
      _showSnack(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _togglingDuty = false);
    }
  }

  Future<void> _orderAction(OrderModel order, String action) async {
    HapticFeedback.lightImpact();
    final endpoint = {
      'accept':   AppConstants.acceptOrder(order.id),
      'on_way':   AppConstants.onWayOrder(order.id),
      'complete': AppConstants.completeOrder(order.id),
      'cancel':   AppConstants.cancelOrder(order.id),
    }[action]!;

    try {
      await ApiService.orderAction(endpoint);
      _showSnack(_actionLabel(action), icon: _actionIcon(action));
      await _loadOrders(silent: true);
    } catch (e) {
      _showSnack(e.toString(), error: true);
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

  void _showSnack(String msg, {bool error = false, IconData? icon}) {
    final messenger = ScaffoldMessenger.of(context);
    messenger.clearSnackBars();
    messenger.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            if (icon != null) Icon(icon, color: Colors.white, size: 18),
            if (icon != null) const SizedBox(width: 10),
            Expanded(child: Text(msg, style: const TextStyle(fontWeight: FontWeight.w600))),
          ],
        ),
        backgroundColor: error ? AppTheme.danger : const Color(0xFF1F2937),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(16),
        duration: Duration(seconds: error ? 4 : 2),
      ),
    );
  }

  Future<void> _logout() async {
    await ApiService.logout();
    if (mounted) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
    }
  }

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
      bottomNavigationBar: _buildNavBar(),
    );
  }

  Widget _buildNavBar() {
    return NavigationBar(
      selectedIndex: _tab,
      onDestinationSelected: (i) {
        HapticFeedback.selectionClick();
        setState(() => _tab = i);
      },
      height: 64,
      destinations: [
        NavigationDestination(
          icon: const Icon(Icons.route_outlined),
          selectedIcon: const Icon(Icons.route),
          label: 'Buyurtmalar',
        ),
        const NavigationDestination(
          icon: Icon(Icons.history_outlined),
          selectedIcon: Icon(Icons.history),
          label: 'Tarix',
        ),
        NavigationDestination(
          icon: _driver?.isOnDuty == true
              ? const Icon(Icons.person_outlined)
              : const Icon(Icons.person_outline),
          selectedIcon: const Icon(Icons.person),
          label: 'Profil',
        ),
      ],
    );
  }

  Widget _ordersTab() {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _init,
        color: AppTheme.primary,
        strokeWidth: 2.5,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _header()),
            SliverToBoxAdapter(child: _dutyBanner()),
            SliverToBoxAdapter(child: _ordersHeader()),
            if (_loadingOrders)
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (_, __) => const SkeletonCard(),
                    childCount: 3,
                  ),
                ),
              )
            else if (_orders.isEmpty)
              SliverFillRemaining(child: _emptyState())
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) => OrderCard(
                      order: _orders[i],
                      onAction: (action) => _orderAction(_orders[i], action),
                    ),
                    childCount: _orders.length,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _header() => Container(
    padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
    child: Row(
      children: [
        Container(
          width: 44, height: 44,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFFBBF24), Color(0xFFF59E0B)],
              begin: Alignment.topLeft, end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [BoxShadow(color: AppTheme.primary.withValues(alpha: 0.35), blurRadius: 12, offset: const Offset(0, 4))],
          ),
          child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('VijdonTaxi', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w900, letterSpacing: -0.3)),
              Text(
                _driver != null ? _driver!.fullName : 'Yuklanmoqda...',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
              ),
            ],
          ),
        ),
        // Online indicator
        if (_driver?.isOnDuty == true)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppTheme.success.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppTheme.success.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(width: 7, height: 7, decoration: BoxDecoration(color: AppTheme.success, shape: BoxShape.circle)),
                const SizedBox(width: 5),
                const Text('Online', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.success)),
              ],
            ),
          ),
        const SizedBox(width: 8),
        IconButton(
          onPressed: () => _loadOrders(),
          icon: const Icon(Icons.refresh_rounded, size: 22),
          tooltip: 'Yangilash',
          style: IconButton.styleFrom(
            backgroundColor: Colors.grey.withValues(alpha: 0.1),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        ),
      ],
    ),
  );

  Widget _dutyBanner() {
    final onDuty = _driver?.isOnDuty ?? false;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: GestureDetector(
        onTap: _togglingDuty ? null : _toggleDuty,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeInOut,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
          decoration: BoxDecoration(
            gradient: onDuty
                ? const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF059669)], begin: Alignment.topLeft, end: Alignment.bottomRight)
                : LinearGradient(colors: [Colors.grey.shade100, Colors.grey.shade200]),
            borderRadius: BorderRadius.circular(18),
            boxShadow: onDuty
                ? [BoxShadow(color: AppTheme.success.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))]
                : [],
          ),
          child: Row(
            children: [
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: Icon(
                  key: ValueKey(onDuty),
                  onDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                  color: onDuty ? Colors.white : Colors.grey.shade500,
                  size: 30,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 250),
                      child: Text(
                        key: ValueKey(onDuty),
                        onDuty ? 'Ish navbatidasiz' : 'Ish navbatida emassiz',
                        style: TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 15,
                          color: onDuty ? Colors.white : Colors.grey.shade700,
                        ),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      onDuty ? 'Buyurtmalar kelmoqda · 30s yangilanadi' : 'Bosing va ish boshlang',
                      style: TextStyle(fontSize: 11, color: onDuty ? Colors.white60 : Colors.grey.shade500),
                    ),
                  ],
                ),
              ),
              _togglingDuty
                  ? const SizedBox(
                      width: 24, height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                    )
                  : Switch.adaptive(
                      value: onDuty,
                      onChanged: (_) => _toggleDuty(),
                      activeColor: Colors.white,
                      activeTrackColor: Colors.white30,
                      inactiveThumbColor: Colors.grey.shade400,
                      inactiveTrackColor: Colors.grey.shade300,
                    ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _ordersHeader() => Padding(
    padding: const EdgeInsets.fromLTRB(20, 4, 20, 10),
    child: Row(
      children: [
        Text(
          _orders.isEmpty && !_loadingOrders ? 'Yangi buyurtmalar' : 'Yangi buyurtmalar',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const Spacer(),
        if (!_loadingOrders && _orders.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.warning.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              '${_orders.length} ta',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.warning),
            ),
          ),
      ],
    ),
  );

  Widget _emptyState() => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 72, height: 72,
          decoration: BoxDecoration(
            color: Colors.grey.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Icon(Icons.inbox_rounded, size: 38, color: Colors.grey.shade300),
        ),
        const SizedBox(height: 16),
        const Text('Yangi buyurtmalar yo\'q', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 6),
        Text(
          'Buyurtma kelganda shu yerda ko\'rinadi.\nAvtomatik yangilanadi.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey.shade500, fontSize: 13, height: 1.5),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: _loadOrders,
          icon: const Icon(Icons.refresh_rounded, size: 16),
          label: const Text('Yangilash'),
          style: OutlinedButton.styleFrom(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            side: BorderSide(color: Colors.grey.shade300),
          ),
        ),
      ],
    ),
  );
}
