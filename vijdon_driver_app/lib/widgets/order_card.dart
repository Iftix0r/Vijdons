import 'package:flutter/material.dart';
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
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: _statusColor().withValues(alpha: order.isPending ? 0.5 : 0.25),
          width: order.isPending ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: _statusColor().withValues(alpha: order.isPending ? 0.12 : 0.06),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          // ── Header ─────────────────────────────────────────────────────────
          _buildHeader(context),
          // ── Body ───────────────────────────────────────────────────────────
          _buildBody(),
          // ── Actions ────────────────────────────────────────────────────────
          if (_showActions()) _buildActions(),
        ],
      ),
    ), // Container
    ); // GestureDetector
  }

  Widget _buildHeader(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: _statusColor().withValues(alpha: isDark ? 0.12 : 0.07),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(19)),
      ),
      child: Row(
        children: [
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
          // Client name
          Expanded(
            child: Text(
              order.clientName.isNotEmpty ? order.clientName : 'Nomsiz mijoz',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              overflow: TextOverflow.ellipsis,
            ),
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
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (order.isPending) ...[
                  Container(
                    width: 6, height: 6,
                    decoration: BoxDecoration(color: _statusColor(), shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 4),
                ],
                Text(order.statusLabel, style: TextStyle(color: _statusColor(), fontSize: 11, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
      child: Column(
        children: [
          // Route
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                _routeRow(Icons.my_location_rounded, AppTheme.success, 'Qayerdan', order.fromAddress),
                Padding(
                  padding: const EdgeInsets.only(left: 9),
                  child: Row(
                    children: [
                      Container(
                        width: 1.5,
                        height: 18,
                        color: Colors.grey.withValues(alpha: 0.25),
                        margin: const EdgeInsets.symmetric(vertical: 2),
                      ),
                    ],
                  ),
                ),
                _routeRow(Icons.location_on_rounded, AppTheme.danger, 'Qayerga', order.toAddress),
              ],
            ),
          ),
          const SizedBox(height: 10),
          // Phone + price row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppTheme.info.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.phone_rounded, size: 13, color: AppTheme.info),
                    const SizedBox(width: 5),
                    Text(order.clientPhone, style: const TextStyle(fontSize: 12, color: AppTheme.info, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
              const Spacer(),
              if (order.price != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppTheme.success.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.payments_rounded, size: 13, color: AppTheme.success),
                      const SizedBox(width: 5),
                      Text('${order.price} so\'m', style: const TextStyle(fontSize: 12, color: AppTheme.success, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _routeRow(IconData icon, Color color, String label, String text) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: 20, height: 20,
        decoration: BoxDecoration(color: color.withValues(alpha: 0.12), shape: BoxShape.circle),
        child: Icon(icon, size: 12, color: color),
      ),
      const SizedBox(width: 10),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
            Text(text, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600), maxLines: 2, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
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
      onPressed: () => onAction(action),
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
      width: 44,
      height: 44,
      child: OutlinedButton(
        onPressed: () => onAction('cancel'),
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
}
