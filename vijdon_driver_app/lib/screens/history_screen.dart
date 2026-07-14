import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  List<OrderModel> _all   = [];
  List<OrderModel> _shown = [];
  bool   _loading = true;
  String _filter  = 'all'; // all | completed | cancelled | active

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await ApiService.getMyOrders();
      if (!mounted) return;
      final orders = list.map((e) => OrderModel.fromJson(e)).toList();
      setState(() { _all = orders; _applyFilter(_filter); });
    } catch (e) {
      if (mounted) _snack(e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _applyFilter(String f) {
    _filter = f;
    _shown = switch (f) {
      'completed' => _all.where((o) => o.isCompleted).toList(),
      'cancelled' => _all.where((o) => o.isCancelled).toList(),
      'active'    => _all.where((o) => o.isAccepted || o.isOnWay).toList(),
      _           => List.from(_all),
    };
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: AppColors.danger,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      margin: const EdgeInsets.all(16),
    ));
  }

  Color _color(String s) => switch (s) {
    'completed' => AppColors.success,
    'cancelled' => AppColors.danger,
    'on_way'    => AppColors.purple,
    'accepted'  => AppColors.info,
    _           => AppColors.warning,
  };

  IconData _icon(OrderModel o) {
    if (o.isCompleted) return Icons.check_circle_rounded;
    if (o.isCancelled) return Icons.cancel_rounded;
    if (o.isOnWay)     return Icons.directions_car_rounded;
    return Icons.route_rounded;
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final dark = Theme.of(context).brightness == Brightness.dark;
    return SafeArea(
      child: Column(
        children: [
          // ── Header ────────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
            child: Row(
              children: [
                const Text('Tarix',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.5)),
                const Spacer(),
                if (!_loading)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppColors.amber.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text('${_all.length} ta buyurtma',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.amber)),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ── Filter chips ──────────────────────────────────────────────────
          SizedBox(
            height: 36,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              children: [
                _chip('all',       'Barchasi',     Icons.list_rounded),
                _chip('completed', 'Yakunlangan',  Icons.check_circle_rounded),
                _chip('active',    'Faol',         Icons.directions_car_rounded),
                _chip('cancelled', 'Bekor qilingan', Icons.cancel_rounded),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // ── Stats row ─────────────────────────────────────────────────────
          if (!_loading && _all.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 12),
              child: Row(children: [
                _statPill(_all.where((o) => o.isCompleted).length.toString(), 'Yakunlandi', AppColors.success),
                const SizedBox(width: 8),
                _statPill(_all.where((o) => o.isCancelled).length.toString(), 'Bekor', AppColors.danger),
                const SizedBox(width: 8),
                _statPill(_all.where((o) => o.isActive).length.toString(), 'Faol', AppColors.info),
              ]),
            ),

          // ── List ──────────────────────────────────────────────────────────
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              color: AppColors.amber,
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: AppColors.amber))
                  : _shown.isEmpty
                      ? _emptyState()
                      : ListView.builder(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                          itemCount: _shown.length,
                          itemBuilder: (ctx, i) => _orderTile(_shown[i], dark),
                        ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _chip(String f, String label, IconData icon) {
    final active = _filter == f;
    return GestureDetector(
      onTap: () => setState(() => _applyFilter(f)),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 0),
        decoration: BoxDecoration(
          color: active ? AppColors.amber : Colors.grey.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: active ? Colors.white : Colors.grey.shade500),
            const SizedBox(width: 5),
            Text(label, style: TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700,
              color: active ? Colors.white : Colors.grey.shade500,
            )),
          ],
        ),
      ),
    );
  }

  Widget _statPill(String count, String label, Color color) => Expanded(
    child: Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        children: [
          Text(count, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: color)),
          Text(label, style: TextStyle(fontSize: 10, color: color.withValues(alpha: 0.8), fontWeight: FontWeight.w600)),
        ],
      ),
    ),
  );

  Widget _orderTile(OrderModel o, bool dark) {
    final c = _color(o.status);
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.withValues(alpha: 0.15)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: IntrinsicHeight(
        child: Row(
          children: [
            // Color accent bar
            Container(
              width: 4,
              decoration: BoxDecoration(
                color: c,
                borderRadius: const BorderRadius.horizontal(left: Radius.circular(16)),
              ),
            ),
            // Icon
            Padding(
              padding: const EdgeInsets.all(14),
              child: Container(
                width: 42, height: 42,
                decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(_icon(o), color: c, size: 20),
              ),
            ),
            // Content
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 12, 12, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text('#${o.id}', style: TextStyle(
                          fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey.shade500)),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: c.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: c.withValues(alpha: 0.25)),
                          ),
                          child: Text(o.statusLabel,
                              style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      '${o.fromAddress} → ${o.toAddress}',
                      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(children: [
                      Icon(Icons.phone_rounded, size: 11, color: Colors.grey.shade400),
                      const SizedBox(width: 4),
                      Text(o.clientPhone,
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                      if (o.price != null) ...[
                        const Spacer(),
                        Icon(Icons.payments_rounded, size: 11, color: AppColors.success.withValues(alpha: 0.7)),
                        const SizedBox(width: 4),
                        Text('${o.price} so\'m',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.success)),
                      ],
                    ]),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyState() => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 72, height: 72,
          decoration: BoxDecoration(
            color: Colors.grey.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(22),
          ),
          child: Icon(Icons.history_rounded, size: 36, color: Colors.grey.shade300),
        ),
        const SizedBox(height: 14),
        const Text('Tarix bo\'sh', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 17)),
        const SizedBox(height: 6),
        Text('Birorta ham buyurtma topilmadi',
            style: TextStyle(fontSize: 13, color: Colors.grey.shade500)),
      ],
    ),
  );
}
