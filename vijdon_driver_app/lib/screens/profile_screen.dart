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
      return const Center(child: CircularProgressIndicator(color: AppColors.primary));
    }
    final dark = Theme.of(context).brightness == Brightness.dark;
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 20),
            const Text(
              'Profil',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, letterSpacing: -0.5),
            ),
            const SizedBox(height: 20),

            // ── Hero Card ──────────────────────────────────────────────────
            _heroCard(dark),
            const SizedBox(height: 16),

            // ── Balance Card ───────────────────────────────────────────────
            _balanceCard(dark),
            const SizedBox(height: 14),

            // ── Car Card ───────────────────────────────────────────────────
            _infoCard(context, 'MASHINA MA\'LUMOTLARI', Icons.directions_car_rounded, [
              _row(context, Icons.directions_car_filled_outlined, AppColors.info, 'Model', driver!.carModel),
              _divider(dark),
              _row(context, Icons.credit_card_rounded, AppColors.info, 'Davlat raqami', driver!.carNumber, mono: true),
            ], dark),
            const SizedBox(height: 14),

            // ── Contact Card ───────────────────────────────────────────────
            _infoCard(context, 'ALOQA MA\'LUMOTLARI', Icons.phone_iphone_rounded, [
              _row(context, Icons.phone_iphone_rounded, AppColors.success, 'Telefon raqam', driver!.phoneNumber, mono: true,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: driver!.phoneNumber));
                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                      content: const Text('Nusxalandi', style: TextStyle(fontWeight: FontWeight.bold)),
                      duration: const Duration(seconds: 1),
                      behavior: SnackBarBehavior.floating,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ));
                  }),
            ], dark),
            const SizedBox(height: 14),

            // ── Status Card ────────────────────────────────────────────────
            _infoCard(context, 'TIZIMDAGI HOLAT', Icons.info_outline_rounded, [
              _row(context,
                driver!.isOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                driver!.isOnDuty ? AppColors.success : Colors.grey,
                'Navbat holati',
                driver!.isOnDuty ? 'Ish navbatida (Faol)' : 'Dam olmoqda (Noaktiv)',
                valueColor: driver!.isOnDuty ? AppColors.success : Colors.grey,
              ),
              _divider(dark),
              _row(context, Icons.verified_rounded,
                driver!.approvalStatus == 'approved' ? AppColors.success : AppColors.warning,
                'Tizim tasdig\'i', _approvalLabel(),
                valueColor: driver!.approvalStatus == 'approved' ? AppColors.success
                    : driver!.approvalStatus == 'rejected' ? AppColors.danger : AppColors.warning,
              ),
            ], dark),
            const SizedBox(height: 32),

            // ── Logout Button ──────────────────────────────────────────────
            SizedBox(
              height: 54,
              child: OutlinedButton.icon(
                onPressed: () => _confirmLogout(context),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Tizimdan chiqish',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.danger,
                  side: const BorderSide(color: AppColors.danger, width: 1.5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _heroCard(bool dark) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: dark
              ? [const Color(0xFF0F2921), const Color(0xFF0A1412)]
              : [const Color(0xFF0F172A), const Color(0xFF1E293B)],
          begin: Alignment.topLeft, end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.3 : 0.15),
            blurRadius: 18,
            offset: const Offset(0, 6),
          )
        ],
      ),
      child: Row(
        children: [
          // Avatar with shining pulse border
          Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.primary.withValues(alpha: 0.4), width: 2),
            ),
            child: Container(
              width: 68, height: 68,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.primary, AppColors.primaryDark],
                  begin: Alignment.topLeft, end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.4),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: Center(
                child: Text(
                  driver!.fullName.isNotEmpty ? driver!.fullName[0].toUpperCase() : 'H',
                  style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900),
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  driver!.fullName,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: -0.2),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  driver!.phoneNumber,
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.white.withValues(alpha: 0.6),
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    _approvalBadge(),
                    const SizedBox(width: 8),
                    if (driver!.isOnDuty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppColors.success.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: AppColors.success.withValues(alpha: 0.4)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(width: 6, height: 6, decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle)),
                            const SizedBox(width: 5),
                            const Text('Online', style: TextStyle(color: AppColors.success, fontSize: 10, fontWeight: FontWeight.w900)),
                          ],
                        ),
                      ),
                  ],
                ),
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
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: color.withValues(alpha: 0.2)),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: dark ? 0.05 : 0.04),
            blurRadius: 16,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 50, height: 50,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isNegative
                    ? [const Color(0xFFEF4444), const Color(0xFFDC2626)]
                    : [AppColors.primary, AppColors.primaryDark],
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 10, offset: const Offset(0, 4))
              ],
            ),
            child: const Icon(Icons.account_balance_wallet_rounded, color: Colors.white, size: 22),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Balans hisobi',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontWeight: FontWeight.w800, letterSpacing: 0.2),
                ),
                const SizedBox(height: 3),
                Text(
                  '${balance.toStringAsFixed(0)} UZS',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: color, letterSpacing: -0.5),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              isNegative ? 'Qarzdorlik' : 'Faol',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: color),
            ),
          ),
        ],
      ),
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
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: c),
          const SizedBox(width: 5),
          Text(label, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w900)),
        ],
      ),
    );
  }

  String _approvalLabel() {
    return switch (driver!.approvalStatus) {
      'approved' => 'Tasdiqlangan',
      'rejected' => 'Rad etilgan',
      _          => 'Tekshirilmoqda',
    };
  }

  Widget _infoCard(BuildContext ctx, String title, IconData titleIcon, List<Widget> children, bool dark) {
    return Container(
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.2 : 0.02),
            blurRadius: 10,
            offset: const Offset(0, 2),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: Text(
              title,
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Colors.grey.shade500, letterSpacing: 0.8),
            ),
          ),
          ...children,
          const SizedBox(height: 6),
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
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 18, color: iconColor),
            ),
            const SizedBox(width: 12),
            Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey)),
            const Spacer(),
            Text(
              value,
              style: TextStyle(
                fontSize: 13, fontWeight: FontWeight.w800,
                color: valueColor,
                fontFamily: mono ? 'monospace' : null,
              ),
            ),
            if (onTap != null) ...[
              const SizedBox(width: 6),
              Icon(Icons.copy_rounded, size: 14, color: Colors.grey.shade400),
            ],
          ],
        ),
      ),
    );
  }

  Widget _divider(bool dark) => Divider(height: 1, indent: 62, color: dark ? AppColors.borderDark : AppColors.borderLight);

  void _confirmLogout(BuildContext ctx) {
    final dark = Theme.of(ctx).brightness == Brightness.dark;
    showModalBottomSheet(
      context: ctx,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(26)),
          border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight, width: 0.8),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 38, height: 4,
                decoration: BoxDecoration(
                  color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Container(
              width: 56, height: 56,
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: const Center(
                child: Icon(Icons.logout_rounded, color: AppColors.danger, size: 26),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Tizimdan chiqish',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            Text(
              "Haqiqatan ham hisobingizdan chiqmoqchimisiz?",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey.shade500, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(ctx),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      side: BorderSide(color: dark ? AppColors.borderDark : AppColors.borderLight),
                      foregroundColor: dark ? Colors.grey.shade300 : AppColors.textPrimary,
                    ),
                    child: const Text('Bekor qilish', style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      onLogout();
                    },
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      backgroundColor: AppColors.danger,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    child: const Text('Chiqish', style: TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }
}
