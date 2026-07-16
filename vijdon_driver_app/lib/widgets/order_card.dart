import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class OrderCard extends StatelessWidget {
  final OrderModel order;
  final void Function(String action) onAction;
  final VoidCallback? onTap;
  final double? liveKm;
  final double? liveFare;

  const OrderCard({
    super.key,
    required this.order,
    required this.onAction,
    this.onTap,
    this.liveKm,
    this.liveFare,
  });

  Color _statusColor() => switch (order.status) {
    'pending'   => AppColors.primary,
    'accepted'  => AppColors.info,
    'on_way'    => AppColors.purple,
    'arrived'   => AppColors.warning,
    'completed' => AppColors.success,
    'cancelled' => AppColors.danger,
    _           => Colors.grey,
  };

  bool _showActions() =>
      order.isPending || order.isAccepted || order.isOnWay || order.isArrived;

  @override
  Widget build(BuildContext context) {
    final dark  = Theme.of(context).brightness == Brightness.dark;
    final color = _statusColor();

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 14),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: order.isPending
                ? color.withValues(alpha: 0.5)
                : (dark ? AppColors.borderDark : AppColors.borderLight),
            width: order.isPending ? 1.5 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: order.isPending
                  ? color.withValues(alpha: 0.08)
                  : Colors.black.withValues(alpha: dark ? 0.2 : 0.03),
              blurRadius: 20,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(23),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(context, dark, color),
              // Pending uchun driver→mijoz masofa/vaqt + reyting banner
              if (order.isPending) _buildPendingBanner(context, dark),
              _buildBody(context, dark, color),
              if (_showActions()) _buildActions(context, color),
            ],
          ),
        ),
      ),
    );
  }

  // ── Header ─────────────────────────────────────────────────────────────────

  Widget _buildHeader(BuildContext context, bool dark, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
      color: color.withValues(alpha: dark ? 0.07 : 0.04),
      child: Row(
        children: [
          if (order.isPending) _PulsingDot(color: color),

          // Timer badge
          if (order.isPending && order.secondsLeft != null)
            Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: AppColors.danger.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.timer_rounded,
                      color: AppColors.danger, size: 13),
                  const SizedBox(width: 4),
                  Text(
                    '${order.secondsLeft}s',
                    style: const TextStyle(
                        color: AppColors.danger,
                        fontWeight: FontWeight.w900,
                        fontSize: 12),
                  ),
                ],
              ),
            ),

          // Order ID
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(9),
            ),
            child: Text(
              '#${order.id}',
              style: TextStyle(
                color: (color == AppColors.primary || color == AppColors.warning)
                    ? AppColors.textPrimary
                    : Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 10),

          Expanded(
            child: Text(
              order.clientName.isNotEmpty ? order.clientName : 'Mijoz',
              style: TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 14,
                color: dark ? Colors.white : AppColors.textPrimary,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),

          if (order.createdAt.isNotEmpty)
            Text(
              _timeAgo(order.createdAt),
              style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey.shade500,
                  fontWeight: FontWeight.w600),
            ),
          const SizedBox(width: 8),

          // Status badge
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
                  fontWeight: FontWeight.w800),
            ),
          ),
        ],
      ),
    );
  }

  // ── Pending banner: haydovchi→mijoz masofa + reyting ──────────────────────

  Widget _buildPendingBanner(BuildContext context, bool dark) {
    final hasDistance = order.driverDistanceKm != null;
    final hasRating   = order.clientRating != null;
    if (!hasDistance && !hasRating) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: dark ? AppColors.surfaceDark : const Color(0xFFF5F5F5),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: dark ? AppColors.borderDark : AppColors.borderLight),
        ),
        child: Row(
          children: [
            // Haydovchidan mijozgacha
            if (hasDistance) ...[
              Container(
                width: 32, height: 32,
                decoration: BoxDecoration(
                  color: AppColors.info.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: const Icon(Icons.near_me_rounded,
                    color: AppColors.info, size: 16),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${order.driverDistanceKm!.toStringAsFixed(1)} km',
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w900,
                        color: AppColors.info),
                  ),
                  Text(
                    order.driverEtaMinutes != null
                        ? '~${order.driverEtaMinutes} daq'
                        : 'uzoqlik',
                    style: TextStyle(
                        fontSize: 10,
                        color: Colors.grey.shade500,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ],

            if (hasDistance && hasRating)
              Container(
                width: 1, height: 30,
                margin: const EdgeInsets.symmetric(horizontal: 14),
                color: dark ? AppColors.borderDark : AppColors.borderLight,
              ),

            // Mijoz reytingi
            if (hasRating) ...[
              Container(
                width: 32, height: 32,
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: const Icon(Icons.star_rounded,
                    color: AppColors.warning, size: 16),
              ),
              const SizedBox(width: 8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    order.clientRating!.toStringAsFixed(1),
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w900,
                        color: AppColors.warning),
                  ),
                  Text(
                    order.clientTripsCount != null
                        ? '${order.clientTripsCount} safar'
                        : 'reyting',
                    style: TextStyle(
                        fontSize: 10,
                        color: Colors.grey.shade500,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ],

            const Spacer(),

            // To'lov turi
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: (order.paymentType == 'card'
                        ? AppColors.info
                        : AppColors.success)
                    .withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: (order.paymentType == 'card'
                          ? AppColors.info
                          : AppColors.success)
                      .withValues(alpha: 0.25),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    order.paymentType == 'card'
                        ? Icons.credit_card_rounded
                        : Icons.payments_rounded,
                    size: 13,
                    color: order.paymentType == 'card'
                        ? AppColors.info
                        : AppColors.success,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    order.paymentType == 'card' ? 'Karta' : 'Naqd',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w800,
                      color: order.paymentType == 'card'
                          ? AppColors.info
                          : AppColors.success,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Body ───────────────────────────────────────────────────────────────────

  Widget _buildBody(BuildContext context, bool dark, Color color) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Route block
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: dark
                  ? AppColors.surfaceDark
                  : const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: dark
                      ? AppColors.borderDark
                      : AppColors.borderLight),
            ),
            child: Column(
              children: [
                _routeRow(Icons.radio_button_checked_rounded,
                    AppColors.success, 'QAYERDAN', order.fromAddress, dark),
                if (order.toAddress.isNotEmpty) ...[
                  Padding(
                    padding: const EdgeInsets.only(left: 10),
                    child: Row(
                      children: List.generate(
                        4,
                        (_) => Container(
                          margin:
                              const EdgeInsets.symmetric(vertical: 2.5),
                          width: 2, height: 4,
                          decoration: BoxDecoration(
                            color: dark
                                ? Colors.grey.shade700
                                : Colors.grey.shade300,
                            borderRadius: BorderRadius.circular(1),
                          ),
                        ),
                      ),
                    ),
                  ),
                  _routeRow(Icons.location_on_rounded, AppColors.danger,
                      'QAYERGA', order.toAddress, dark),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Info chips (accepted/on_way/arrived holatida to'liq ma'lumot)
          Row(
            children: [
              _infoChip(
                Icons.phone_iphone_rounded,
                order.clientPhone,
                AppColors.info,
                dark,
                onTap: (order.isAccepted || order.isOnWay || order.isArrived)
                    ? () => _call(order.clientPhone)
                    : null,
              ),
              const Spacer(),
              if (!order.isPending) ...[
                _infoChip(
                  order.paymentType == 'card'
                      ? Icons.credit_card_rounded
                      : Icons.payments_rounded,
                  order.paymentType == 'card' ? 'Karta' : 'Naqd',
                  order.paymentType == 'card'
                      ? AppColors.info
                      : AppColors.success,
                  dark,
                ),
                if (order.distanceKm != null && !order.isOnWay) ...[
                  const SizedBox(width: 8),
                  _infoChip(Icons.straighten_rounded,
                      '${order.distanceKm!.toStringAsFixed(1)} km',
                      AppColors.purple, dark),
                ],
                if (order.price != null && !order.isOnWay) ...[
                  const SizedBox(width: 8),
                  _infoChip(Icons.monetization_on_rounded,
                      "${order.price} so'm", AppColors.success, dark),
                ],
              ],
            ],
          ),

          // Taximeter row (on_way)
          if (order.isOnWay && liveKm != null) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 30, height: 30,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.speed_rounded,
                        color: AppColors.primary, size: 16),
                  ),
                  const SizedBox(width: 10),
                  const Text(
                    'TAXIMETR',
                    style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primary,
                        letterSpacing: 0.8),
                  ),
                  const Spacer(),
                  Icon(Icons.straighten_rounded,
                      size: 13, color: Colors.grey.shade500),
                  const SizedBox(width: 4),
                  Text(
                    '${liveKm!.toStringAsFixed(2)} km',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                        color: dark ? Colors.white : AppColors.textPrimary),
                  ),
                  const SizedBox(width: 14),
                  const Icon(Icons.monetization_on_rounded,
                      size: 13, color: AppColors.success),
                  const SizedBox(width: 4),
                  Text(
                    "${liveFare!.toStringAsFixed(0)} so'm",
                    style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w900,
                        color: AppColors.success),
                  ),
                ],
              ),
            ),
          ],

          // Note
          if (order.note.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 9),
              decoration: BoxDecoration(
                color: AppColors.warning.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: AppColors.warning.withValues(alpha: 0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.notes_rounded,
                      size: 14, color: AppColors.warning),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      order.note,
                      style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.warning,
                          fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Commission
          if (order.commission != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: AppColors.danger.withValues(alpha: 0.15)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.remove_circle_outline_rounded,
                      size: 13, color: AppColors.danger),
                  const SizedBox(width: 6),
                  Text(
                    "Komissiya: ${order.commission} so'm",
                    style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.danger,
                        fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  Widget _buildActions(BuildContext context, Color color) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Row(
        children: [
          // Asosiy harakat tugmasi
          if (order.isPending)
            Expanded(
              child: _actionBtn(context, 'Qabul qilish',
                  Icons.check_circle_rounded, AppColors.primary, 'accept'),
            ),
          if (order.isAccepted)
            Expanded(
              child: _actionBtn(context, "Yo'lga chiqdim",
                  Icons.directions_car_rounded, AppColors.purple, 'on_way'),
            ),
          if (order.isOnWay)
            Expanded(
              child: _actionBtn(context, 'Yetib keldim',
                  Icons.location_on_rounded, AppColors.info, 'arrived'),
            ),
          if (order.isArrived)
            Expanded(
              child: _actionBtn(context, 'Yakunlash',
                  Icons.flag_rounded, AppColors.success, 'complete'),
            ),

          const SizedBox(width: 10),

          // Pending → Rad etish (reject)
          if (order.isPending) _iconBtn(
            context,
            icon: Icons.close_rounded,
            color: AppColors.danger,
            action: 'reject',
            tooltip: "Rad etish",
          ),

          // Accepted/on_way/arrived → Bekor qilish (cancel)
          if (order.isAccepted || order.isOnWay || order.isArrived) _iconBtn(
            context,
            icon: Icons.cancel_outlined,
            color: AppColors.danger,
            action: 'cancel',
            tooltip: "Bekor qilish",
          ),
        ],
      ),
    );
  }

  Widget _actionBtn(BuildContext context, String label, IconData icon,
      Color btnColor, String action) {
    final isYellow = btnColor == AppColors.primary;
    return SizedBox(
      height: 50,
      child: ElevatedButton.icon(
        onPressed: () {
          HapticFeedback.mediumImpact();
          onAction(action);
        },
        icon: Icon(icon, size: 17),
        label: Text(label,
            style: const TextStyle(
                fontSize: 13, fontWeight: FontWeight.w900)),
        style: ElevatedButton.styleFrom(
          backgroundColor: btnColor,
          foregroundColor: isYellow ? AppColors.textPrimary : Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14)),
          padding: EdgeInsets.zero,
        ),
      ),
    );
  }

  Widget _iconBtn(BuildContext context,
      {required IconData icon,
      required Color color,
      required String action,
      required String tooltip}) {
    return Tooltip(
      message: tooltip,
      child: SizedBox(
        width: 50, height: 50,
        child: OutlinedButton(
          onPressed: () {
            HapticFeedback.mediumImpact();
            onAction(action);
          },
          style: OutlinedButton.styleFrom(
            foregroundColor: color,
            side: BorderSide(color: color, width: 1.5),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14)),
            padding: EdgeInsets.zero,
          ),
          child: Icon(icon, size: 20),
        ),
      ),
    );
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  Widget _routeRow(IconData icon, Color markerColor, String label,
      String text, bool dark) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(icon, size: 18, color: markerColor),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: TextStyle(
                      fontSize: 9,
                      color: Colors.grey.shade500,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3)),
              const SizedBox(height: 2),
              Text(text,
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: dark
                          ? Colors.white
                          : AppColors.textPrimary),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis),
            ],
          ),
        ),
      ],
    );
  }

  Widget _infoChip(IconData icon, String label, Color chipColor, bool dark,
      {VoidCallback? onTap}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: chipColor.withValues(
              alpha: onTap != null ? 0.12 : 0.07),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
              color: chipColor.withValues(
                  alpha: onTap != null ? 0.35 : 0.15)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(onTap != null ? Icons.call_rounded : icon,
                size: 13, color: chipColor),
            const SizedBox(width: 5),
            Text(label,
                style: TextStyle(
                    fontSize: 12,
                    color: chipColor,
                    fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  String _timeAgo(String iso) {
    try {
      final dt   = DateTime.parse(iso).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inMinutes < 1)  return 'Hozir';
      if (diff.inMinutes < 60) return '${diff.inMinutes}d avval';
      if (diff.inHours < 24)   return '${diff.inHours}s avval';
      return '${diff.inDays}k avval';
    } catch (_) {
      return '';
    }
  }
}

// ── Pulsing dot ────────────────────────────────────────────────────────────

class _PulsingDot extends StatefulWidget {
  final Color color;
  const _PulsingDot({required this.color});
  @override
  State<_PulsingDot> createState() => _PulsingDotState();
}

class _PulsingDotState extends State<_PulsingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _scale;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 900))
      ..repeat(reverse: true);
    _scale   = Tween<double>(begin: 0.7, end: 1.3)
        .animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
    _opacity = Tween<double>(begin: 0.6, end: 1.0)
        .animate(CurvedAnimation(parent: _c, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: Opacity(
          opacity: _opacity.value,
          child: Transform.scale(
            scale: _scale.value,
            child: Container(
              width: 8, height: 8,
              decoration: BoxDecoration(
                color: widget.color,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                      color: widget.color.withValues(alpha: 0.5),
                      blurRadius: 4,
                      spreadRadius: 1)
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
