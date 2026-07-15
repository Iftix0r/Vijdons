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
  String _filter  = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await ApiService.getMyOrders();
      if (!mounted) return;
      final orders = list.map((e) => OrderModel.fromJson(e)).toList();
      setState(() {
        _all = orders;
        _applyFilter(_filter);
      });
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

  double get _totalEarnings {
    return _all.where((o) => o.isCompleted).fold(0.0, (sum, o) {
      final p = double.tryParse(o.price ?? '') ?? 0;
      return sum + p;
    });
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(fontWeight: FontWeight.bold)),
      backgroundColor: AppColors.danger,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: const EdgeInsets.all(20),
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
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Header ────────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 10),
            child: Row(
              children: [
                const Text(
                  'Tarix',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.5),
                ),
                const Spacer(),
                if (!_loading)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '${_all.length} ta',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppColors.primary),
                    ),
                  ),
              ],
            ),
          ),

          // ── Earnings summary card ─────────────────────────────────────────
          if (!_loading && _all.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 14),
              child: Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF10B981), Color(0xFF059669)],
                    begin: Alignment.topLeft, end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.success.withValues(alpha: 0.3),
                      blurRadius: 18,
                      offset: const Offset(0, 8),
                    )
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      width: 48, height: 48,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Center(
                        child: Icon(Icons.payments_rounded, color: Colors.white, size: 24),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Jami daromad',
                            style: TextStyle(fontSize: 12, color: Colors.white70, fontWeight: FontWeight.w700, letterSpacing: 0.2),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            '${_totalEarnings.toStringAsFixed(0)} UZS',
                            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: -0.5),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Text(
                            '${_all.where((o) => o.isCompleted).length}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Colors.white),
                          ),
                          const Text(
                            'yakunlandi',
                            style: TextStyle(fontSize: 9, color: Colors.white70, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // ── Stats row ─────────────────────────────────────────────────────
          if (!_loading && _all.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: Row(
                children: [
                  _statPill(_all.where((o) => o.isCompleted).length.toString(), 'Yakunlandi', AppColors.success),
                  const SizedBox(width: 10),
                  _statPill(_all.where((o) => o.isCancelled).length.toString(), 'Bekor bo\'ldi', AppColors.danger),
                  const SizedBox(width: 10),
                  _statPill(_all.where((o) => o.isActive).length.toString(), 'Faol', AppColors.info),
                ],
              ),
            ),

          // ── Filter chips ──────────────────────────────────────────────────
          SizedBox(
            height: 38,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: [
                _chip('all',       'Barchasi',       Icons.list_rounded, dark),
                _chip('completed', 'Yakunlangan',    Icons.check_circle_outline_rounded, dark),
                _chip('active',    'Faol',           Icons.directions_car_filled_outlined, dark),
                _chip('cancelled', 'Bekor qilingan', Icons.cancel_outlined, dark),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // ── List ──────────────────────────────────────────────────────────
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              color: AppColors.primary,
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
                  : _shown.isEmpty
                      ? _emptyState(dark)
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

  Widget _chip(String f, String label, IconData icon, bool dark) {
    final active = _filter == f;
    return GestureDetector(
      onTap: () => setState(() => _applyFilter(f)),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: active ? AppColors.primary : (dark ? AppColors.surfaceDark : Colors.grey.shade100),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: active ? Colors.transparent : (dark ? AppColors.borderDark : AppColors.borderLight),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: active ? Colors.white : Colors.grey.shade500),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: active ? Colors.white : Colors.grey.shade500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statPill(String count, String label, Color color) => Expanded(
    child: Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Column(
        children: [
          Text(count, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: color)),
          const SizedBox(height: 2),
          Text(
            label,
            style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w800, letterSpacing: 0.2),
          ),
        ],
      ),
    ),
  );

  Widget _orderTile(OrderModel o, bool dark) {
    final c = _color(o.status);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.2 : 0.02),
            blurRadius: 10,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: IntrinsicHeight(
        child: Row(
          children: [
            Container(
              width: 5,
              decoration: BoxDecoration(
                color: c,
                borderRadius: const BorderRadius.horizontal(left: Radius.circular(18)),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(_icon(o), color: c, size: 22),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 14, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      children: [
                        Text('#${o.id}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Colors.grey.shade500)),
                        const SizedBox(width: 8),
                        Text(_timeAgo(o.createdAt), style: TextStyle(fontSize: 11, color: Colors.grey.shade400, fontWeight: FontWeight.w600)),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: c.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: c.withValues(alpha: 0.25)),
                          ),
                          child: Text(
                            o.statusLabel,
                            style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${o.fromAddress} → ${o.toAddress}',
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Icon(Icons.phone_iphone_rounded, size: 12, color: Colors.grey.shade400),
                        const SizedBox(width: 4),
                        Text(o.clientPhone, style: TextStyle(fontSize: 11, color: Colors.grey.shade500, fontWeight: FontWeight.bold, fontFamily: 'monospace')),
                        if (o.distanceKm != null) ...[
                          const SizedBox(width: 10),
                          Icon(Icons.straighten_rounded, size: 12, color: AppColors.purple.withValues(alpha: 0.7)),
                          const SizedBox(width: 4),
                          Text(
                            '${o.distanceKm!.toStringAsFixed(1)} km',
                            style: TextStyle(fontSize: 11, color: AppColors.purple, fontWeight: FontWeight.w800),
                          ),
                        ],
                        if (o.price != null) ...[
                          const Spacer(),
                          Text(
                            '${o.price} so\'m',
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: AppColors.success),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyState(bool dark) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 80, height: 80,
            decoration: BoxDecoration(
              color: dark ? AppColors.surfaceDark : Colors.grey.shade100,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: dark ? AppColors.borderDark : Colors.grey.shade200),
            ),
            child: Icon(Icons.history_rounded, size: 36, color: Colors.grey.shade400),
          ),
          const SizedBox(height: 18),
          const Text('Tarix bo\'sh', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 6),
          Text(
            'Hozircha birorta ham buyurtma yakunlanmagan.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.grey.shade500),
          ),
        ],
      ),
    ),
  );

  String _timeAgo(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Hozir';
      if (diff.inMinutes < 60) return '${diff.inMinutes} daq oldin';
      if (diff.inHours < 24) return '${diff.inHours} soat oldin';
      return '${diff.inDays} kun oldin';
    } catch (_) {
      return '';
    }
  }
}
