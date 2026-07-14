import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class OrderCard extends StatelessWidget {
  final OrderModel order;
  final void Function(String action) onAction;

  const OrderCard({super.key, required this.order, required this.onAction});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _borderColor().withOpacity(.4), width: 1.5),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(.05), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: _bgColor().withOpacity(.08),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: _bgColor(), borderRadius: BorderRadius.circular(8)),
                  child: Text('#${order.id}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(order.clientName.isNotEmpty ? order.clientName : 'Nomsiz',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                ),
                _statusBadge(),
              ],
            ),
          ),

          // Body
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _addressRow(Icons.my_location_rounded, AppTheme.success, order.fromAddress),
                const Padding(
                  padding: EdgeInsets.only(left: 11),
                  child: SizedBox(height: 12,
                      child: VerticalDivider(color: Colors.grey, width: 1, thickness: 1)),
                ),
                _addressRow(Icons.location_on_rounded, AppTheme.danger, order.toAddress),
                const SizedBox(height: 12),
                Row(
                  children: [
                    const Icon(Icons.phone_outlined, size: 15, color: Colors.grey),
                    const SizedBox(width: 6),
                    Text(order.clientPhone, style: const TextStyle(fontSize: 13, color: Colors.grey)),
                    if (order.price != null) ...[
                      const Spacer(),
                      const Icon(Icons.payments_outlined, size: 15, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text('${order.price} so\'m', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                    ],
                  ],
                ),
              ],
            ),
          ),

          // Action buttons
          if (_showActions())
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Row(children: _buildActions()),
            ),
        ],
      ),
    );
  }

  Widget _addressRow(IconData icon, Color color, String text) => Row(
    children: [
      Icon(icon, color: color, size: 18),
      const SizedBox(width: 8),
      Expanded(child: Text(text, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500))),
    ],
  );

  Widget _statusBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: _bgColor().withOpacity(.15), borderRadius: BorderRadius.circular(20)),
      child: Text(order.statusLabel, style: TextStyle(color: _bgColor(), fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }

  Color _bgColor() {
    switch (order.status) {
      case 'pending':   return AppTheme.warning;
      case 'accepted':  return AppTheme.info;
      case 'on_way':    return const Color(0xFF8B5CF6);
      case 'completed': return AppTheme.success;
      case 'cancelled': return AppTheme.danger;
      default:          return Colors.grey;
    }
  }

  Color _borderColor() => _bgColor();

  bool _showActions() => order.isPending || order.isAccepted || order.isOnWay;

  List<Widget> _buildActions() {
    final btns = <Widget>[];

    if (order.isPending) {
      btns.add(_btn('Qabul qilish', Icons.check_circle_outline, AppTheme.success, 'accept'));
    }
    if (order.isAccepted) {
      btns.add(_btn("Yo'lda", Icons.directions_car_rounded, const Color(0xFF8B5CF6), 'on_way'));
    }
    if (order.isOnWay) {
      btns.add(_btn('Yakunlash', Icons.flag_rounded, AppTheme.success, 'complete'));
    }
    if (order.isAccepted || order.isOnWay) {
      btns.add(const SizedBox(width: 8));
      btns.add(_btn('Bekor', Icons.cancel_outlined, AppTheme.danger, 'cancel', outlined: true));
    }

    return btns;
  }

  Widget _btn(String label, IconData icon, Color color, String action, {bool outlined = false}) {
    return Expanded(
      child: outlined
          ? OutlinedButton.icon(
              onPressed: () => onAction(action),
              icon: Icon(icon, size: 16),
              label: Text(label, style: const TextStyle(fontSize: 13)),
              style: OutlinedButton.styleFrom(
                foregroundColor: color,
                side: BorderSide(color: color),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            )
          : ElevatedButton.icon(
              onPressed: () => onAction(action),
              icon: Icon(icon, size: 16),
              label: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(
                backgroundColor: color,
                foregroundColor: Colors.white,
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                padding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
    );
  }
}
