import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';

class ProfileScreen extends StatelessWidget {
  final DriverModel? driver;
  final VoidCallback onLogout;
  const ProfileScreen({super.key, required this.driver, required this.onLogout});

  @override
  Widget build(BuildContext context) {
    if (driver == null) {
      return const Center(child: CircularProgressIndicator(color: AppColors.amber));
    }
    final dark = Theme.of(context).brightness == Brightness.dark;
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 18),
            const Text('Profil',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.5)),
            const SizedBox(height: 20),

            // ── Hero card ──────────────────────────────────────────────────
            _heroCard(),
            const SizedBox(height: 14),

            // ── Balance card ───────────────────────────────────────────────
            _balanceCard(dark),
            const SizedBox(height: 12),

            // ── Car card ───────────────────────────────────────────────────
            _infoCard(context, 'Mashina', Icons.directions_car_rounded, [
              _row(context, Icons.directions_car_rounded, AppColors.info, 'Model', driver!.carModel),
              _divider(),
              _row(context, Icons.tag_rounded, AppColors.info, 'Davlat raqami', driver!.carNumber, mono: true),
            ]),
            const SizedBox(height: 12),

            // ── Contact card ───────────────────────────────────────────────
            _infoCard(context, 'Aloqa', Icons.phone_rounded, [
              _row(context, Icons.phone_rounded, AppColors.success, 'Telefon', driver!.phoneNumber, mono: true,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: driver!.phoneNumber));
                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('Nusxalandi'),
                      duration: Duration(seconds: 1),
                      behavior: SnackBarBehavior.floating,
                    ));
                  }),
            ]),
            const SizedBox(height: 12),

            // ── Status card ────────────────────────────────────────────────
            _infoCard(context, 'Holat', Icons.info_outline_rounded, [
              _row(context,
                driver!.isOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                driver!.isOnDuty ? AppColors.success : Colors.grey,
                'Navbat holati',
                driver!.isOnDuty ? 'Ish navbatidasiz' : 'Dam olmoqda',
                valueColor: driver!.isOnDuty ? AppColors.success : Colors.grey,
              ),
              _divider(),
              _row(context, Icons.verified_rounded,
                driver!.approvalStatus == 'approved' ? AppColors.success : AppColors.warning,
                'Tasdiqlash', _approvalLabel(),
                valueColor: driver!.approvalStatus == 'approved' ? AppColors.success
                    : driver!.approvalStatus == 'rejected' ? AppColors.danger : AppColors.warning,
              ),
            ]),
            const SizedBox(height: 28),

            // ── Logout ─────────────────────────────────────────────────────
            SizedBox(
              height: 54,
              child: OutlinedButton.icon(
                onPressed: () => _confirmLogout(context),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Hisobdan chiqish',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.danger,
                  side: BorderSide(color: AppColors.danger.withValues(alpha: 0.5), width: 1.5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _heroCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1A3A5C), Color(0xFF0F2340)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [BoxShadow(color: const Color(0xFF0F2340).withValues(alpha: 0.5), blurRadius: 20, offset: const Offset(0, 8))],
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 68, height: 68,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF4ADE80), Color(0xFF16A34A)],
                begin: Alignment.topLeft, end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(22),
              boxShadow: [BoxShadow(color: AppColors.green.withValues(alpha: 0.5), blurRadius: 14, offset: const Offset(0, 4))],
            ),
            child: Center(
              child: Text(
                driver!.fullName.isNotEmpty ? driver!.fullName[0].toUpperCase() : 'H',
                style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(driver!.fullName,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                    overflow: TextOverflow.ellipsis),
                const SizedBox(height: 3),
                Text(driver!.phoneNumber,
                    style: TextStyle(fontSize: 13, color: Colors.white.withValues(alpha: 0.55), fontFamily: 'monospace')),
                const SizedBox(height: 10),
                Row(children: [
                  _approvalBadge(),
                  const SizedBox(width: 8),
                  if (driver!.isOnDuty)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.success.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppColors.success.withValues(alpha: 0.5)),
                      ),
                      child: Row(mainAxisSize: MainAxisSize.min, children: [
                        Container(width: 6, height: 6, decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle)),
                        const SizedBox(width: 5),
                        const Text('Online', style: TextStyle(color: AppColors.success, fontSize: 11, fontWeight: FontWeight.bold)),
                      ]),
                    ),
                ]),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _balanceCard(bool dark) {
    final balance = double.tryParse(driver!.balance) ?? 0;
    final isNegative = balance < 0;
    final color = isNegative ? AppColors.danger : AppColors.success;

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.25)),
        boxShadow: dark
            ? []
            : [BoxShadow(color: color.withValues(alpha: 0.1), blurRadius: 16, offset: const Offset(0, 4))],
      ),
      child: Row(children: [
        Container(
          width: 52, height: 52,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isNegative
                  ? [const Color(0xFFEF4444), const Color(0xFFDC2626)]
                  : [const Color(0xFF34D399), const Color(0xFF10B981)],
            ),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: color.withValues(alpha: 0.35), blurRadius: 12, offset: const Offset(0, 4))],
          ),
          child: const Icon(Icons.account_balance_wallet_rounded, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 16),
        Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Joriy balans', style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontWeight: FontWeight.w500)),
            const SizedBox(height: 3),
            Text(
              '${balance.toStringAsFixed(0)} UZS',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: color, letterSpacing: -0.5),
            ),
          ],
        )),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            isNegative ? 'Qarzdor' : 'Yaxshi',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color),
          ),
        ),
      ]),
    );
  }

  Widget _approvalBadge() {
    Color c; String label; IconData icon;
    switch (driver!.approvalStatus) {
      case 'approved':
        c = AppColors.success; label = 'Tasdiqlangan'; icon = Icons.verified_rounded; break;
      case 'rejected':
        c = AppColors.danger;  label = 'Rad etilgan';  icon = Icons.cancel_rounded;   break;
      default:
        c = AppColors.warning; label = 'Kutilmoqda';   icon = Icons.access_time_rounded;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.18),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.4)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 12, color: c),
        const SizedBox(width: 5),
        Text(label, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.bold)),
      ]),
    );
  }

  String _approvalLabel() {
    return switch (driver!.approvalStatus) {
      'approved' => 'Tasdiqlangan',
      'rejected' => 'Rad etilgan',
      _          => 'Admin tekshirmoqda',
    };
  }

  Widget _infoCard(BuildContext ctx, String title, IconData titleIcon, List<Widget> children) {
    final dark = Theme.of(ctx).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: dark ? AppColors.borderDark : Colors.grey.withValues(alpha: 0.12)),
        boxShadow: dark ? [] : [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 2))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
            child: Text(title,
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700,
                    color: Colors.grey.shade500, letterSpacing: 0.8)),
          ),
          ...children,
          const SizedBox(height: 4),
        ],
      ),
    );
  }

  Widget _row(
    BuildContext ctx,
    IconData icon, Color iconColor,
    String label, String value, {
    bool mono = false,
    Color? valueColor,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(children: [
          Container(
            width: 34, height: 34,
            decoration: BoxDecoration(color: iconColor.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, size: 17, color: iconColor),
          ),
          const SizedBox(width: 12),
          Text(label, style: TextStyle(fontSize: 13, color: Colors.grey.shade500)),
          const Spacer(),
          Text(value,
              style: TextStyle(
                fontSize: 13, fontWeight: FontWeight.w600,
                color: valueColor,
                fontFamily: mono ? 'monospace' : null,
              )),
          if (onTap != null) ...[
            const SizedBox(width: 6),
            Icon(Icons.copy_rounded, size: 14, color: Colors.grey.shade400),
          ],
        ]),
      ),
    );
  }

  Widget _divider() => const Divider(height: 1, indent: 62);

  void _confirmLogout(BuildContext ctx) {
    showModalBottomSheet(
      context: ctx,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(ctx).brightness == Brightness.dark ? AppColors.cardDark : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 40, height: 4,
                decoration: BoxDecoration(color: Colors.grey.withValues(alpha: 0.3), borderRadius: BorderRadius.circular(2))),
            const SizedBox(height: 20),
            Container(
              width: 56, height: 56,
              decoration: BoxDecoration(color: AppColors.danger.withValues(alpha: 0.1), shape: BoxShape.circle),
              child: const Icon(Icons.logout_rounded, color: AppColors.danger, size: 26),
            ),
            const SizedBox(height: 14),
            const Text('Hisobdan chiqish',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text("Rostdan ham chiqmoqchimisiz?",
                style: TextStyle(fontSize: 14, color: Colors.grey.shade500)),
            const SizedBox(height: 24),
            Row(children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(ctx),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    side: BorderSide(color: Colors.grey.withValues(alpha: 0.3)),
                  ),
                  child: const Text('Bekor qilish', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton(
                  onPressed: () { Navigator.pop(ctx); onLogout(); },
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    backgroundColor: AppColors.danger,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: const Text('Chiqish', style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ]),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}
