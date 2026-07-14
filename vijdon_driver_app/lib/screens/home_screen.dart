import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';
import '../models/order_model.dart';
import '../widgets/order_card.dart';
import 'login_screen.dart';
import 'history_screen.dart';
import 'profile_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;
  DriverModel? _driver;
  List<OrderModel> _orders = [];
  bool _loadingOrders = false;
  bool _togglingDuty  = false;

  @override
  void initState() {
    super.initState();
    _loadProfile();
    _loadOrders();
  }

  Future<void> _loadProfile() async {
    try {
      final data = await ApiService.getProfile();
      if (mounted) setState(() => _driver = DriverModel.fromJson(data));
    } catch (_) {}
  }

  Future<void> _loadOrders() async {
    setState(() => _loadingOrders = true);
    try {
      final list = await ApiService.getAvailableOrders();
      if (mounted) setState(() => _orders = list.map((e) => OrderModel.fromJson(e)).toList());
    } catch (e) {
      if (mounted) _showSnack(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _loadingOrders = false);
    }
  }

  Future<void> _toggleDuty() async {
    setState(() => _togglingDuty = true);
    try {
      final data = await ApiService.toggleDuty();
      setState(() {
        if (_driver != null) {
          _driver = DriverModel(
            id: _driver!.id, fullName: _driver!.fullName,
            phoneNumber: _driver!.phoneNumber, carModel: _driver!.carModel,
            carNumber: _driver!.carNumber, isActive: _driver!.isActive,
            isOnDuty: data['is_on_duty'] ?? !_driver!.isOnDuty,
            approvalStatus: _driver!.approvalStatus,
          );
        }
      });
    } catch (e) {
      _showSnack(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _togglingDuty = false);
    }
  }

  Future<void> _orderAction(OrderModel order, String action) async {
    final endpoint = {
      'accept':   AppConstants.acceptOrder(order.id),
      'on_way':   AppConstants.onWayOrder(order.id),
      'complete': AppConstants.completeOrder(order.id),
      'cancel':   AppConstants.cancelOrder(order.id),
    }[action]!;

    try {
      await ApiService.orderAction(endpoint);
      _showSnack(_actionLabel(action));
      _loadOrders();
    } catch (e) {
      _showSnack(e.toString(), error: true);
    }
  }

  String _actionLabel(String action) {
    return {'accept': 'Buyurtma qabul qilindi', 'on_way': "Yo'lda", 'complete': 'Buyurtma yakunlandi', 'cancel': 'Bekor qilindi'}[action] ?? '';
  }

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: error ? AppTheme.danger : AppTheme.success),
    );
  }

  Future<void> _logout() async {
    await ApiService.logout();
    if (mounted) Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _tab == 0 ? _ordersTab() : _tab == 1 ? const HistoryScreen() : ProfileScreen(driver: _driver, onLogout: _logout),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.route_outlined), selectedIcon: Icon(Icons.route), label: 'Buyurtmalar'),
          NavigationDestination(icon: Icon(Icons.history_outlined), selectedIcon: Icon(Icons.history), label: 'Tarix'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profil'),
        ],
      ),
    );
  }

  Widget _ordersTab() {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () async { await _loadProfile(); await _loadOrders(); },
        color: AppTheme.primary,
        child: CustomScrollView(
          slivers: [
            // App bar
            SliverToBoxAdapter(child: _header()),
            // Duty toggle
            SliverToBoxAdapter(child: _dutyToggle()),
            // Orders
            _loadingOrders
                ? const SliverFillRemaining(child: Center(child: CircularProgressIndicator(color: AppTheme.primary)))
                : _orders.isEmpty
                    ? SliverFillRemaining(child: _emptyState())
                    : SliverPadding(
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

  Widget _header() => Padding(
    padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
    child: Row(
      children: [
        Container(
          width: 42, height: 42,
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFFFBBF24), Color(0xFFF59E0B)]),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.local_taxi_rounded, color: Colors.white, size: 22),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('VijdonTaxi', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
              Text(_driver?.fullName ?? 'Yuklanmoqda...', style: const TextStyle(fontSize: 12, color: Colors.grey)),
            ],
          ),
        ),
        IconButton(
          onPressed: _loadOrders,
          icon: const Icon(Icons.refresh_rounded),
          tooltip: 'Yangilash',
        ),
      ],
    ),
  );

  Widget _dutyToggle() {
    final onDuty = _driver?.isOnDuty ?? false;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: InkWell(
        onTap: _togglingDuty ? null : _toggleDuty,
        borderRadius: BorderRadius.circular(16),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            gradient: onDuty
                ? const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF059669)])
                : LinearGradient(colors: [Colors.grey.shade200, Colors.grey.shade300]),
            borderRadius: BorderRadius.circular(16),
            boxShadow: onDuty
                ? [BoxShadow(color: AppTheme.success.withOpacity(.3), blurRadius: 12, offset: const Offset(0, 4))]
                : [],
          ),
          child: Row(
            children: [
              Icon(onDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                  color: onDuty ? Colors.white : Colors.grey, size: 28),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(onDuty ? 'Ish navbatidasiz' : 'Ish navbatida emassiz',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15,
                            color: onDuty ? Colors.white : Colors.grey.shade700)),
                    Text(onDuty ? 'Buyurtmalar kelmoqda' : "Bosing va ish boshlang",
                        style: TextStyle(fontSize: 12, color: onDuty ? Colors.white70 : Colors.grey)),
                  ],
                ),
              ),
              _togglingDuty
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                  : Switch(
                      value: onDuty,
                      onChanged: (_) => _toggleDuty(),
                      activeColor: Colors.white,
                      activeTrackColor: Colors.white30,
                    ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _emptyState() => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.inbox_rounded, size: 64, color: Colors.grey.shade300),
        const SizedBox(height: 12),
        const Text('Hozircha buyurtmalar yo\'q', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const Text('Yangi buyurtma kelganda shu yerda ko\'rinadi', style: TextStyle(color: Colors.grey, fontSize: 13)),
        const SizedBox(height: 20),
        TextButton.icon(onPressed: _loadOrders, icon: const Icon(Icons.refresh), label: const Text('Yangilash')),
      ],
    ),
  );
}
