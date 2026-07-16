import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/api_service.dart';
import '../core/constants.dart';
import '../core/theme.dart';
import '../models/order_model.dart';
import 'home_screen.dart' show ActiveOrderSheet;

class HistoryScreen extends StatefulWidget {
  final Future<void> Function(OrderModel, String)? onOrderAction;
  // Taximetr ma'lumotlari HomeScreen dan uzatiladi
  final double?      liveKm;
  final double?      liveFare;
  final bool         taxiPaused;
  final String?      taxiDuration;
  final VoidCallback? onTaxiPause;
  final int?         activeOrderId; // qaysi buyurtmada taximetr ishlayapti

  const HistoryScreen({
    super.key,
    this.onOrderAction,
    this.liveKm,
    this.liveFare,
    this.taxiPaused = false,
    this.taxiDuration,
    this.onTaxiPause,
    this.activeOrderId,
  });
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
  Timer? _timer;
  int    _tick    = 0;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 3), (_) {
      _tick++;
      final hasActive = _all.any((o) => o.isActive);
      if (hasActive || _tick % 4 == 0) _load(silent: true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent && mounted) setState(() => _loading = true);
    try {
      // Tarix + faol buyurtmalarni birgalikda yuklaymiz
      final results = await Future.wait([
        ApiService.getMyOrders(),
        ApiService.getAvailableOrders(),
      ]);
      if (!mounted) return;
      final history = results[0].map((e) => OrderModel.fromJson(e)).toList();
      final active  = results[1]
          .map((e) => OrderModel.fromJson(e))
          .where((o) => o.isActive)
          .toList();
      // Faol buyurtmalar tepada, tarix pastda; takrorlanmasin
      final historyIds = history.map((o) => o.id).toSet();
      final merged = [
        ...active.where((o) => !historyIds.contains(o.id)),
        ...history,
      ];
      setState(() {
        _all = merged;
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
      'active'    => _all.where((o) => o.isActive).toList(),
      _           => List.from(_all),
    };
  }

  Future<void> _orderAction(OrderModel order, String action) async {
    HapticFeedback.mediumImpact();
    try {
      if (widget.onOrderAction != null) {
        await widget.onOrderAction!(order, action);
        await _load();
        return;
      }
      final ep = {
        'on_way':   AppConstants.onWayOrder(order.id),
        'arrived':  AppConstants.arrivedOrder(order.id),
        'complete': AppConstants.completeOrder(order.id),
        'cancel':   AppConstants.cancelOrder(order.id),
      }[action];
      if (ep == null) return;
      await ApiService.orderAction(ep);
      await _load();
    } catch (e) {
      if (mounted) _snack(e.toString());
    }
  }

  void _showActiveOrderSheet(OrderModel order) {
    HapticFeedback.selectionClick();
    final isThisActive = widget.activeOrderId == order.id;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => ActiveOrderSheet(
        order: order,
        onAction: (a) { Navigator.pop(context); _orderAction(order, a); },
        liveKm:       isThisActive ? widget.liveKm       : null,
        liveFare:     isThisActive ? widget.liveFare     : null,
        taxiPaused:   isThisActive && widget.taxiPaused,
        taxiDuration: isThisActive ? widget.taxiDuration : null,
        onTaxiPause:  isThisActive ? widget.onTaxiPause  : null,
      ),
    );
  }

  double get _totalEarnings => _all
      .where((o) => o.isCompleted)
      .fold(0.0, (s, o) => s + (double.tryParse(o.price ?? '') ?? 0));

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, style: const TextStyle(fontWeight: FontWeight.bold)),
      backgroundColor: AppColors.danger,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      margin: const EdgeInsets.all(20),
    ));
  }

  Color _statusColor(String s) => switch (s) {
    'completed' => AppColors.success,
    'cancelled' => AppColors.danger,
    'on_way'    => AppColors.purple,
    'accepted'  => AppColors.info,
    _           => AppColors.warning,
  };

  IconData _statusIcon(OrderModel o) {
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
          // ── Header ────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
            child: Row(
              children: [
                Text(
                  'Tarix',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.8,
                    color: dark ? Colors.white : AppColors.textPrimary,
                  ),
                ),
                const Spacer(),
                if (!_loading)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '${_all.length} ta',
                      style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: AppColors.primary),
                    ),
                  ),
              ],
            ),
          ),

          // ── Earnings summary card ─────────────────────────────────────
          if (!_loading && _all.isNotEmpty) ...[
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: _earningsCard(dark),
            ),
            const SizedBox(height: 12),

            // Stats row
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _statPill(
                    _all.where((o) => o.isCompleted).length.toString(),
                    'Yakunlandi',
                    AppColors.success,
                    dark,
                  ),
                  const SizedBox(width: 10),
                  _statPill(
                    _all.where((o) => o.isCancelled).length.toString(),
                    'Bekor',
                    AppColors.danger,
                    dark,
                  ),
                  const SizedBox(width: 10),
                  _statPill(
                    _all.where((o) => o.isActive).length.toString(),
                    'Faol',
                    AppColors.info,
                    dark,
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 14),

          // ── Filter chips ──────────────────────────────────────────────
          SizedBox(
            height: 40,
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
          const SizedBox(height: 12),

          // ── List ──────────────────────────────────────────────────────
          Expanded(
            child: RefreshIndicator(
              onRefresh: _load,
              color: AppColors.primary,
              child: _loading
                  ? const Center(
                      child: CircularProgressIndicator(
                          color: AppColors.primary))
                  : _shown.isEmpty
                      ? _emptyState(dark)
                      : ListView.builder(
                          padding:
                              const EdgeInsets.fromLTRB(16, 0, 16, 28),
                          itemCount: _shown.length,
                          itemBuilder: (ctx, i) =>
                              _orderTile(_shown[i], dark),
                        ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Earnings card ─────────────────────────────────────────────────────────

  Widget _earningsCard(bool dark) {
    final completed = _all.where((o) => o.isCompleted).length;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgDark,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.4 : 0.1),
            blurRadius: 20,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 52, height: 52,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Icon(Icons.payments_rounded,
                color: AppColors.primary, size: 26),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'JAMI DAROMAD',
                  style: TextStyle(
                    fontSize: 10,
                    color: AppColors.textSecondaryDark,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '${_totalEarnings.toStringAsFixed(0)} so\'m',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primary,
                    letterSpacing: -0.5,
                  ),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$completed',
                style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w900,
                    color: Colors.white),
              ),
              const Text(
                'ta buyurtma',
                style: TextStyle(
                    fontSize: 10,
                    color: AppColors.textSecondaryDark,
                    fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ── Stat pill ─────────────────────────────────────────────────────────────

  Widget _statPill(String count, String label, Color color, bool dark) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withValues(alpha: 0.2)),
        ),
        child: Column(
          children: [
            Text(
              count,
              style: TextStyle(
                  fontSize: 20, fontWeight: FontWeight.w900, color: color),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                  fontSize: 10,
                  color: Colors.grey.shade500,
                  fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }

  // ── Filter chip ───────────────────────────────────────────────────────────

  Widget _chip(String f, String label, IconData icon, bool dark) {
    final active = _filter == f;
    return GestureDetector(
      onTap: () => setState(() => _applyFilter(f)),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: BoxDecoration(
          color: active
              ? AppColors.primary
              : (dark ? AppColors.surfaceDark : Colors.white),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: active
                ? Colors.transparent
                : (dark ? AppColors.borderDark : AppColors.borderLight),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: active
                  ? AppColors.textPrimary
                  : Colors.grey.shade500,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: active
                    ? AppColors.textPrimary
                    : Colors.grey.shade500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Order tile ────────────────────────────────────────────────────────────

  Widget _orderTile(OrderModel o, bool dark) {
    final c = _statusColor(o.status);
    return GestureDetector(
      onTap: o.isActive ? () => _showActiveOrderSheet(o) : null,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: o.isActive
                ? c.withValues(alpha: 0.4)
                : (dark ? AppColors.borderDark : AppColors.borderLight),
            width: o.isActive ? 1.5 : 1,
          ),
        ),
        child: IntrinsicHeight(
          child: Row(
          children: [
            // Colored left accent bar
            Container(
              width: 4,
              decoration: BoxDecoration(
                color: c,
                borderRadius: const BorderRadius.horizontal(
                    left: Radius.circular(20)),
              ),
            ),

            // Icon
            Padding(
              padding: const EdgeInsets.all(14),
              child: Container(
                width: 46, height: 46,
                decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(_statusIcon(o), color: c, size: 22),
              ),
            ),

            // Content
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(0, 12, 14, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // ID + time + status badge
                    Row(
                      children: [
                        Text(
                          '#${o.id}',
                          style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              color: Colors.grey.shade500),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _timeAgo(o.createdAt),
                          style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade400,
                              fontWeight: FontWeight.w600),
                        ),
                        const Spacer(),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: c.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                                color: c.withValues(alpha: 0.25)),
                          ),
                          child: Text(
                            o.statusLabel,
                            style: TextStyle(
                                color: c,
                                fontSize: 10,
                                fontWeight: FontWeight.w800),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),

                    // Route
                    Text(
                      o.toAddress.isNotEmpty
                          ? '${o.fromAddress} → ${o.toAddress}'
                          : o.fromAddress,
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 13,
                        color: dark ? Colors.white : AppColors.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),

                    // Meta: phone + distance + price
                    Row(
                      children: [
                        Icon(Icons.phone_iphone_rounded,
                            size: 11, color: Colors.grey.shade400),
                        const SizedBox(width: 3),
                        Text(
                          o.clientPhone,
                          style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade500,
                              fontWeight: FontWeight.w600,
                              fontFamily: 'monospace'),
                        ),
                        if (o.distanceKm != null) ...[
                          const SizedBox(width: 10),
                          Icon(Icons.straighten_rounded,
                              size: 11,
                              color: AppColors.purple
                                  .withValues(alpha: 0.7)),
                          const SizedBox(width: 3),
                          Text(
                            '${o.distanceKm!.toStringAsFixed(1)} km',
                            style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.purple,
                                fontWeight: FontWeight.w800),
                          ),
                        ],
                        if (o.price != null && o.isCompleted) ...[
                          const Spacer(),
                          Text(
                            '${o.price} so\'m',
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w900,
                                color: AppColors.success),
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
      ),
    );
  }

  Widget _emptyState(bool dark) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: dark
                    ? AppColors.surfaceDark
                    : const Color(0xFFF2F2F2),
                borderRadius: BorderRadius.circular(24),
              ),
              child: Icon(Icons.history_rounded,
                  size: 38,
                  color: Colors.grey.shade400),
            ),
            const SizedBox(height: 20),
            Text(
              'Tarix yo\'q',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w900,
                color: dark ? Colors.white : AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Siz hali hech qanday buyurtmani\nbajarmagansiz yoki tanlangan filtr bo\'yicha\nnatija topilmadi.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey.shade500,
                  height: 1.6),
            ),
          ],
        ),
      ),
    );
  }

  String _timeAgo(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Hozir';
      if (diff.inMinutes < 60) return '${diff.inMinutes}d avval';
      if (diff.inHours < 24) return '${diff.inHours}s avval';
      return '${diff.inDays}k avval';
    } catch (_) {
      return '';
    }
  }
}
