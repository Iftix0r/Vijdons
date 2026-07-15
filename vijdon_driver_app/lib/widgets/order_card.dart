import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class OrderCard extends StatelessWidget {
  final OrderModel order;
  final void Function(String action) onAction;
  final VoidCallback? onTap;

  const OrderCard({super.key, required this.order, required this.onAction, this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          color: isDark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: _statusColor().withValues(alpha: order.isPending ? 0.5 : 0.2),
            width: order.isPending ? 1.5 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: _statusColor().withValues(alpha: order.isPending ? 0.10 : 0.05),
              blurRadius: 18,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          children: [
            _buildHeader(context, isDark),
            _buildBody(isDark),
            if (_showActions()) _buildActions(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        color: _statusColor().withValues(alpha: isDark ? 0.12 : 0.07),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(19)),
      ),
      child: Row(
        children: [
          // Pulsating dot for pending
          if (order.isPending)
            _PulsingDot(color: _statusColor()),
          // Order ID chip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
              color: _statusColor(),
              borderRadius: BorderRadius.circular(8),
              boxShadow: [BoxShadow(color: _statusColor().withValues(alpha: 0.4), blurRadius: 6, offset: const Offset(0, 2))],
            ),
            child: Text('#${order.id}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              order.clientName.isNotEmpty ? order.clientName : 'Nomsiz mijoz',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          // Time ago
          if (order.createdAt.isNotEmpty)
            Text(
              _timeAgo(order.createdAt),
              style: TextStyle(fontSize: 11, color: Colors.grey.shade500, fontWeight: FontWeight.w500),
            ),
          const SizedBox(width: 8),
          // Status badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
              color: _statusColor().withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: _statusColor().withValues(alpha: 0.3)),
            ),
            child: Text(order.statusLabel, style: TextStyle(color: _statusColor(), fontSize: 11, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(bool isDark) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
      child: Column(
        children: [
          // Route
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isDark ? AppColors.surfaceDark : Colors.grey.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.withValues(alpha: isDark ? 0.1 : 0.08)),
            ),
            child: Column(
              children: [
                _routeRow(Icons.my_location_rounded, AppTheme.success, 'Qayerdan', order.fromAddress),
                Padding(
                  padding: const EdgeInsets.only(left: 9),
                  child: Row(children: [
                    Container(width: 1.5, height: 16, color: Colors.grey.withValues(alpha: 0.25), margin: const EdgeInsets.symmetric(vertical: 2)),
                  ]),
                ),
                _routeRow(Icons.location_on_rounded, AppTheme.danger, 'Qayerga', order.toAddress),
              ],
            ),
          ),
          const SizedBox(height: 10),
          // Info chips row
          Row(
            children: [
              // Phone chip
              _infoChip(Icons.phone_rounded, order.clientPhone, AppTheme.info),
              const Spacer(),
              // Distance chip
              if (order.distanceKm != null)
                _infoChip(Icons.straighten_rounded, '${order.distanceKm!.toStringAsFixed(1)} km', AppColors.purple),
              if (order.distanceKm != null) const SizedBox(width: 6),
              // Price chip
              if (order.price != null)
                _infoChip(Icons.payments_rounded, '${order.price} so\'m', AppTheme.success),
            ],
          ),
          // Commission row
          if (order.commission != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.danger.withValues(alpha: 0.15)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.remove_circle_outline_rounded, size: 13, color: AppColors.danger),
                    const SizedBox(width: 5),
                    Text('Komissiya: ${order.commission} so\'m',
                        style: const TextStyle(fontSize: 12, color: AppColors.danger, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _infoChip(IconData icon, String label, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 12, color: color),
      const SizedBox(width: 4),
      Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
    ]),
  );

  Widget _routeRow(IconData icon, Color color, String label, String text) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: 20, height: 20,
        decoration: BoxDecoration(color: color.withValues(alpha: 0.12), shape: BoxShape.circle),
        child: Icon(icon, size: 12, color: color),
      ),
      const SizedBox(width: 10),
      Expanded(child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
          Text(text, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600), maxLines: 2, overflow: TextOverflow.ellipsis),
        ],
      )),
    ],
  );

  Widget _buildActions() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      child: Row(
        children: [
          if (order.isPending)
            Expanded(child: _actionBtn('Qabul qilish', Icons.check_circle_rounded, AppTheme.success, 'accept')),
          if (order.isAccepted)
            Expanded(child: _actionBtn("Yo'lda", Icons.directions_car_rounded, const Color(0xFF8B5CF6), 'on_way')),
          if (order.isOnWay)
            Expanded(child: _actionBtn('Yakunlash', Icons.flag_rounded, AppTheme.success, 'complete')),
          if (order.isAccepted || order.isOnWay) ...[
            const SizedBox(width: 8),
            _cancelBtn(),
          ],
        ],
      ),
    );
  }

  Widget _actionBtn(String label, IconData icon, Color color, String action) {
    return ElevatedButton.icon(
      onPressed: () {
        HapticFeedback.lightImpact();
        onAction(action);
      },
      icon: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        elevation: 0,
        shadowColor: color.withValues(alpha: 0.4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 12),
      ),
    );
  }

  Widget _cancelBtn() {
    return SizedBox(
      width: 44, height: 44,
      child: OutlinedButton(
        onPressed: () {
          HapticFeedback.lightImpact();
          onAction('cancel');
        },
        style: OutlinedButton.styleFrom(
          foregroundColor: AppTheme.danger,
          side: BorderSide(color: AppTheme.danger.withValues(alpha: 0.5)),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          padding: EdgeInsets.zero,
        ),
        child: const Icon(Icons.close_rounded, size: 18),
      ),
    );
  }

  Color _statusColor() {
    switch (order.status) {
      case 'pending':   return AppTheme.warning;
      case 'accepted':  return AppTheme.info;
      case 'on_way':    return const Color(0xFF8B5CF6);
      case 'completed': return AppTheme.success;
      case 'cancelled': return AppTheme.danger;
      default:          return Colors.grey;
    }
  }

  bool _showActions() => order.isPending || order.isAccepted || order.isOnWay;

  String _timeAgo(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Hozir';
      if (diff.inMinutes < 60) return '${diff.inMinutes} daq';
      if (diff.inHours < 24) return '${diff.inHours} soat';
      return '${diff.inDays} kun';
    } catch (_) { return ''; }
  }
}

// ── Pulsating dot for new orders ─────────────────────────────────────────────

class _PulsingDot extends StatefulWidget {
  final Color color;
  const _PulsingDot({required this.color});
  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _a;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat(reverse: true);
    _a = Tween<double>(begin: 0.4, end: 1.0).animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: AnimatedBuilder(
        animation: _a,
        builder: (_, __) => Container(
          width: 8, height: 8,
          decoration: BoxDecoration(
            color: widget.color.withValues(alpha: _a.value),
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: widget.color.withValues(alpha: _a.value * 0.5), blurRadius: 4)],
          ),
        ),
      ),
    );
  }
}
