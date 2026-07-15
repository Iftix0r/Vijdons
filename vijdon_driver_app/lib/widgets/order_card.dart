import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class OrderCard extends StatelessWidget {
  final OrderModel order;
  final void Function(String action) onAction;
  final VoidCallback? onTap;
  final double? liveKm;    // taximetr bosib o'tilgan km (on_way paytida)
  final double? liveFare;  // taximetr hisoblangan narx

  const OrderCard({
    super.key,
    required this.order,
    required this.onAction,
    this.onTap,
    this.liveKm,
    this.liveFare,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final color = _statusColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: isDark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: color.withValues(alpha: order.isPending ? 0.4 : 0.15),
            width: order.isPending ? 1.5 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: order.isPending ? 0.12 : 0.04),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(21),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(context, isDark, color),
              _buildBody(context, isDark, color),
              if (_showActions()) _buildActions(context, color),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, bool isDark, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: isDark ? 0.08 : 0.05),
        border: Border(
          bottom: BorderSide(
            color: isDark ? AppColors.borderDark : AppColors.borderLight,
            width: 0.8,
          ),
        ),
      ),
      child: Row(
        children: [
          if (order.isPending) ...[
            _PulsingDot(color: color),
            if (order.secondsLeft != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.danger.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.timer_rounded, color: AppColors.danger, size: 14),
                    const SizedBox(width: 4),
                    Text(
                      '${order.secondsLeft} s',
                      style: const TextStyle(
                        color: AppColors.danger,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
          
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(8),
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.3),
                  blurRadius: 6,
                  offset: const Offset(0, 2),
                )
              ],
            ),
            child: Text(
              '#${order.id}',
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 12,
                letterSpacing: 0.5,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              order.clientName.isNotEmpty ? order.clientName : 'Nomsiz mijoz',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          
          if (order.createdAt.isNotEmpty)
            Text(
              _timeAgo(order.createdAt),
              style: TextStyle(
                fontSize: 11,
                color: isDark ? Colors.grey.shade400 : AppColors.textSecondary,
                fontWeight: FontWeight.w700,
              ),
            ),
          const SizedBox(width: 8),

          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: color.withValues(alpha: 0.25)),
            ),
            child: Text(
              order.statusLabel,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, bool isDark, Color color) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Route Details
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isDark ? AppColors.surfaceDark : const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: isDark ? AppColors.borderDark : AppColors.borderLight),
            ),
            child: Column(
              children: [
                _routeRow(Icons.radio_button_checked_rounded, AppColors.success, 'MIJOZ MANZILI', order.fromAddress),
                if (order.toAddress.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.only(left: 9),
                    child: Row(
                      children: [
                        Column(
                          children: List.generate(
                            3,
                            (_) => Container(
                              margin: const EdgeInsets.symmetric(vertical: 2.5),
                              width: 2, height: 4,
                              decoration: BoxDecoration(
                                color: isDark ? Colors.grey.shade700 : Colors.grey.shade300,
                                borderRadius: BorderRadius.circular(1),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  _routeRow(Icons.location_on_rounded, AppColors.danger, 'QAYERGA', order.toAddress),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Chips Info Row
          Row(
            children: [
              _infoChip(Icons.phone_iphone_rounded, order.clientPhone, AppColors.info, isDark,
                  onTap: order.isAccepted || order.isOnWay || order.isArrived
                      ? () => _call(order.clientPhone)
                      : null),
              const Spacer(),
              _infoChip(
                order.paymentType == 'card' ? Icons.credit_card_rounded : Icons.payments_rounded,
                order.paymentType == 'card' ? 'Karta' : 'Naqd',
                order.paymentType == 'card' ? AppColors.info : AppColors.success,
                isDark,
              ),
              if (order.distanceKm != null && !order.isOnWay) ...[ 
                const SizedBox(width: 8),
                _infoChip(Icons.map_rounded, '${order.distanceKm!.toStringAsFixed(1)} km', AppColors.purple, isDark),
              ],
              if (order.price != null && !order.isOnWay) ...[
                const SizedBox(width: 8),
                _infoChip(Icons.monetization_on_rounded, '${order.price} so\'m', AppColors.success, isDark),
              ],
            ],
          ),

          // 🚖 Taximetr qatori (faqat yo'lda ketayotganda)
          if (order.isOnWay && liveKm != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppColors.primary.withValues(alpha: 0.12),
                    AppColors.success.withValues(alpha: 0.08),
                  ],
                ),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.25)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.speed_rounded, color: AppColors.primary, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'TAXIMETR',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                      color: AppColors.primary,
                      letterSpacing: 0.8,
                    ),
                  ),
                  const Spacer(),
                  Icon(Icons.straighten_rounded, size: 14, color: Colors.grey.shade500),
                  const SizedBox(width: 4),
                  Text(
                    '${liveKm!.toStringAsFixed(2)} km',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(width: 16),
                  const Icon(Icons.monetization_on_rounded, size: 14, color: AppColors.success),
                  const SizedBox(width: 4),
                  Text(
                    '${liveFare!.toStringAsFixed(0)} so\'m',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                      color: AppColors.success,
                    ),
                  ),
                ],
              ),
            ),
          ],

          if (order.note.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.notes_rounded, size: 14, color: AppColors.warning),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        order.note,
                        style: const TextStyle(fontSize: 12, color: AppColors.warning, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // Commission info
          if (order.commission != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.danger.withValues(alpha: 0.15)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.remove_circle_outline_rounded, size: 14, color: AppColors.danger),
                    const SizedBox(width: 6),
                    Text(
                      'Tizim komissiyasi: ${order.commission} so\'m',
                      style: const TextStyle(fontSize: 12, color: AppColors.danger, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _infoChip(IconData icon, String label, Color chipColor, bool isDark, {VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: chipColor.withValues(alpha: onTap != null ? 0.15 : 0.08),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: chipColor.withValues(alpha: onTap != null ? 0.4 : 0.15)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(onTap != null ? Icons.call_rounded : icon, size: 13, color: chipColor),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: chipColor, fontWeight: FontWeight.w800),
            ),
          ],
        ),
      ),
    );
  }

  void _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Widget _routeRow(IconData icon, Color markerColor, String label, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(icon, size: 20, color: markerColor),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(fontSize: 9, color: Colors.grey, fontWeight: FontWeight.w700, letterSpacing: 0.2),
              ),
              const SizedBox(height: 2),
              Text(
                text,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildActions(BuildContext context, Color color) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Row(
        children: [
          if (order.isPending)
            Expanded(child: _actionBtn('Qabul qilish', Icons.check_circle_rounded, AppColors.primary, 'accept')),
          if (order.isAccepted)
            Expanded(child: _actionBtn("Yo'lga chiqdim", Icons.directions_car_rounded, AppColors.purple, 'on_way')),
          if (order.isOnWay)
            Expanded(child: _actionBtn('Yetib keldim', Icons.location_on_rounded, AppColors.info, 'arrived')),
          if (order.isArrived)
            Expanded(child: _actionBtn('Yakunlash', Icons.flag_rounded, AppColors.success, 'complete')),
          if (order.isAccepted || order.isOnWay || order.isArrived) ...[
            const SizedBox(width: 10),
            _cancelBtn(),
          ],
        ],
      ),
    );
  }

  Widget _actionBtn(String label, IconData icon, Color actionColor, String action) {
    return ElevatedButton.icon(
      onPressed: () {
        HapticFeedback.lightImpact();
        onAction(action);
      },
      icon: Icon(icon, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w900)),
      style: ElevatedButton.styleFrom(
        backgroundColor: actionColor,
        foregroundColor: Colors.white,
        elevation: 2,
        shadowColor: actionColor.withValues(alpha: 0.3),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
    );
  }

  Widget _cancelBtn() {
    return SizedBox(
      width: 48,
      height: 48,
      child: OutlinedButton(
        onPressed: () {
          HapticFeedback.lightImpact();
          onAction('cancel');
        },
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.danger,
          side: const BorderSide(color: AppColors.danger, width: 1.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          padding: EdgeInsets.zero,
        ),
        child: const Icon(Icons.close_rounded, size: 20),
      ),
    );
  }

  Color _statusColor() {
    switch (order.status) {
      case 'pending':   return AppColors.warning;
      case 'accepted':  return AppColors.info;
      case 'on_way':    return AppColors.purple;
      case 'arrived':   return AppColors.primary;
      case 'completed': return AppColors.success;
      case 'cancelled': return AppColors.danger;
      default:          return Colors.grey;
    }
  }

  bool _showActions() => order.isPending || order.isAccepted || order.isOnWay || order.isArrived;

  String _timeAgo(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1) return 'Hozir';
      if (diff.inMinutes < 60) return '${diff.inMinutes} daq';
      if (diff.inHours < 24) return '${diff.inHours} soat';
      return '${diff.inDays} kun';
    } catch (_) {
      return '';
    }
  }
}

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
    _a = Tween<double>(begin: 0.3, end: 1.0).animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 10),
      child: AnimatedBuilder(
        animation: _a,
        builder: (_, __) => Container(
          width: 9, height: 9,
          decoration: BoxDecoration(
            color: widget.color.withValues(alpha: _a.value),
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: widget.color.withValues(alpha: _a.value * 0.6),
                blurRadius: 6,
                spreadRadius: 1,
              )
            ],
          ),
        ),
      ),
    );
  }
}
