import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';

class ProfileScreen extends StatefulWidget {
  final DriverModel? driver;
  final VoidCallback onLogout;
  const ProfileScreen({super.key, required this.driver, required this.onLogout});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  DriverModel? get driver => widget.driver;
  String? _localPhotoUrl;
  bool _uploading = false;

  Future<void> _pickAndUpload() async {
    final picker = ImagePicker();
    final dark = Theme.of(context).brightness == Brightness.dark;

    // Galereya yoki kamera tanlash
    await showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 36, height: 4,
              decoration: BoxDecoration(
                color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            _sourceBtn(Icons.photo_library_rounded, 'Galereyadan tanlash', () async {
              Navigator.pop(context);
              final f = await picker.pickImage(source: ImageSource.gallery, imageQuality: 80);
              if (f != null) _upload(File(f.path));
            }, dark),
            const SizedBox(height: 10),
            _sourceBtn(Icons.camera_alt_rounded, 'Kameradan olish', () async {
              Navigator.pop(context);
              final f = await picker.pickImage(source: ImageSource.camera, imageQuality: 80);
              if (f != null) _upload(File(f.path));
            }, dark),
          ],
        ),
      ),
    );
  }

  Widget _sourceBtn(IconData icon, String label, VoidCallback onTap, bool dark) {
    return SizedBox(
      width: double.infinity, height: 52,
      child: ElevatedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 20),
        label: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
        style: ElevatedButton.styleFrom(
          backgroundColor: dark ? AppColors.surfaceDark : const Color(0xFFF2F2F2),
          foregroundColor: dark ? Colors.white : AppColors.textPrimary,
          elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
    );
  }

  Future<void> _upload(File file) async {
    setState(() => _uploading = true);
    try {
      final url = await ApiService.uploadPhoto(file);
      if (mounted) setState(() { _localPhotoUrl = url; _uploading = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _uploading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(e.toString()),
          backgroundColor: AppColors.danger,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          margin: const EdgeInsets.all(16),
        ));
      }
    }
  }

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
            const SizedBox(height: 24),
            Text('Profil', style: TextStyle(
              fontSize: 28, fontWeight: FontWeight.w900,
              letterSpacing: -0.8,
              color: dark ? Colors.white : AppColors.textPrimary,
            )),
            const SizedBox(height: 20),
            _heroCard(dark),
            const SizedBox(height: 14),
            _balanceCard(dark),
            const SizedBox(height: 14),
            _infoCard("MASHINA MA'LUMOTLARI", Icons.directions_car_rounded, [
              _row(context, Icons.directions_car_filled_outlined, AppColors.info, 'Model', driver!.carModel, dark),
              _divider(dark),
              _row(context, Icons.credit_card_rounded, AppColors.info, 'Davlat raqami', driver!.carNumber, dark, mono: true),
            ], dark),
            const SizedBox(height: 14),
            _infoCard("ALOQA MA'LUMOTLARI", Icons.phone_iphone_rounded, [
              _row(context, Icons.phone_iphone_rounded, AppColors.success, 'Telefon', driver!.phoneNumber, dark,
                mono: true,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: driver!.phoneNumber));
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                    content: const Text('Nusxalandi', style: TextStyle(fontWeight: FontWeight.bold)),
                    duration: const Duration(seconds: 1),
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ));
                },
              ),
            ], dark),
            const SizedBox(height: 14),
            _infoCard('TIZIMDAGI HOLAT', Icons.info_outline_rounded, [
              _row(context,
                driver!.isOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                driver!.isOnDuty ? AppColors.success : Colors.grey,
                'Navbat',
                driver!.isOnDuty ? 'Faol (Ish navbatida)' : 'Dam olmoqda',
                dark,
                valueColor: driver!.isOnDuty ? AppColors.success : Colors.grey,
              ),
              _divider(dark),
              _row(context, Icons.verified_rounded,
                driver!.approvalStatus == 'approved' ? AppColors.success : AppColors.warning,
                "Tizim tasdig'i", _approvalLabel(), dark,
                valueColor: driver!.approvalStatus == 'approved'
                    ? AppColors.success
                    : driver!.approvalStatus == 'rejected' ? AppColors.danger : AppColors.warning,
              ),
            ], dark),
            const SizedBox(height: 28),
            SizedBox(
              height: 54,
              child: OutlinedButton.icon(
                onPressed: () => _confirmLogout(context, dark),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Tizimdan chiqish',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
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

  // ── Hero card ─────────────────────────────────────────────────────────────

  Widget _heroCard(bool dark) {
    final photoUrl = _localPhotoUrl ?? driver!.photoUrl;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.bgDark,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: dark ? 0.4 : 0.12),
            blurRadius: 20, offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          // Avatar — bosilsa rasm yuklash
          GestureDetector(
            onTap: _uploading ? null : _pickAndUpload,
            child: Stack(
              children: [
                Container(
                  width: 72, height: 72,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withValues(alpha: 0.35),
                        blurRadius: 14, offset: const Offset(0, 5),
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: _uploading
                        ? const Center(child: SizedBox(width: 24, height: 24,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)))
                        : photoUrl != null
                            ? Image.network(photoUrl, fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => _avatarLetter())
                            : _avatarLetter(),
                  ),
                ),
                // Kamera ikonkasi
                Positioned(
                  right: 0, bottom: 0,
                  child: Container(
                    width: 22, height: 22,
                    decoration: BoxDecoration(
                      color: AppColors.primary,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.bgDark, width: 2),
                    ),
                    child: const Icon(Icons.camera_alt_rounded, size: 11, color: Colors.black),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(driver!.fullName,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900,
                      color: Colors.white, letterSpacing: -0.3),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(driver!.phoneNumber,
                  style: TextStyle(fontSize: 13,
                    color: Colors.white.withValues(alpha: 0.5),
                    fontFamily: 'monospace', fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 10),
                Row(children: [
                  _approvalBadge(),
                  const SizedBox(width: 8),
                  if (driver!.isOnDuty) _onlineBadge(),
                ]),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _avatarLetter() => Center(
    child: Text(
      driver!.fullName.isNotEmpty ? driver!.fullName[0].toUpperCase() : 'H',
      style: const TextStyle(color: AppColors.textPrimary, fontSize: 30, fontWeight: FontWeight.w900),
    ),
  );

  Widget _approvalBadge() {
    Color c; String label; IconData icon;
    switch (driver!.approvalStatus) {
      case 'approved': c = AppColors.success; label = 'Tasdiqlangan'; icon = Icons.verified_rounded; break;
      case 'rejected': c = AppColors.danger;  label = 'Rad etilgan';  icon = Icons.cancel_rounded;   break;
      default:         c = AppColors.warning; label = 'Kutilmoqda';   icon = Icons.access_time_rounded;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: c.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.35)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 12, color: c),
        const SizedBox(width: 5),
        Text(label, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w900)),
      ]),
    );
  }

  Widget _onlineBadge() => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
    decoration: BoxDecoration(
      color: AppColors.success.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(20),
      border: Border.all(color: AppColors.success.withValues(alpha: 0.35)),
    ),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 6, height: 6,
          decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle)),
      const SizedBox(width: 5),
      const Text('Online', style: TextStyle(color: AppColors.success, fontSize: 10, fontWeight: FontWeight.w900)),
    ]),
  );

  // ── Balance card ──────────────────────────────────────────────────────────

  Widget _balanceCard(bool dark) {
    final balance = double.tryParse(driver!.balance) ?? 0;
    final isNeg = balance < 0;
    final color = isNeg ? AppColors.danger : AppColors.success;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(children: [
        Container(
          width: 52, height: 52,
          decoration: BoxDecoration(
            color: isNeg ? AppColors.danger.withValues(alpha: 0.1) : AppColors.primary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Icon(Icons.account_balance_wallet_rounded,
              color: isNeg ? AppColors.danger : AppColors.primary, size: 24),
        ),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Balans hisobi', style: TextStyle(fontSize: 12, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text("${balance.toStringAsFixed(0)} so'm",
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: color, letterSpacing: -0.5)),
        ])),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withValues(alpha: 0.2)),
          ),
          child: Text(isNeg ? 'Qarzdorlik' : 'Faol',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: color)),
        ),
      ]),
    );
  }

  // ── Info card ─────────────────────────────────────────────────────────────

  Widget _infoCard(String title, IconData titleIcon, List<Widget> children, bool dark) {
    return Container(
      decoration: BoxDecoration(
        color: dark ? AppColors.cardDark : Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Container(width: 3, height: 12,
                decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(2))),
            const SizedBox(width: 8),
            Text(title, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900,
                color: Colors.grey.shade500, letterSpacing: 1)),
          ]),
        ),
        ...children,
        const SizedBox(height: 6),
      ]),
    );
  }

  Widget _row(BuildContext ctx, IconData icon, Color iconColor, String label, String value, bool dark,
      {bool mono = false, Color? valueColor, VoidCallback? onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(children: [
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(color: iconColor.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, size: 18, color: iconColor),
          ),
          const SizedBox(width: 12),
          Text(label, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Colors.grey.shade500)),
          const Spacer(),
          Text(value, style: TextStyle(
            fontSize: 13, fontWeight: FontWeight.w800,
            color: valueColor ?? (dark ? Colors.white : AppColors.textPrimary),
            fontFamily: mono ? 'monospace' : null,
          )),
          if (onTap != null) ...[const SizedBox(width: 6), Icon(Icons.copy_rounded, size: 13, color: Colors.grey.shade400)],
        ]),
      ),
    );
  }

  Widget _divider(bool dark) => Divider(
      height: 1, indent: 62,
      color: dark ? AppColors.borderDark : AppColors.borderLight);

  String _approvalLabel() => switch (driver!.approvalStatus) {
    'approved' => 'Tasdiqlangan',
    'rejected' => 'Rad etilgan',
    _          => 'Tekshirilmoqda',
  };

  // ── Logout confirm ────────────────────────────────────────────────────────

  void _confirmLogout(BuildContext ctx, bool dark) {
    showModalBottomSheet(
      context: ctx,
      backgroundColor: Colors.transparent,
      builder: (_) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        ),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Center(child: Container(width: 36, height: 4,
              decoration: BoxDecoration(color: dark ? Colors.grey.shade700 : Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2)))),
          const SizedBox(height: 24),
          Center(child: Container(
            width: 62, height: 62,
            decoration: BoxDecoration(color: AppColors.danger.withValues(alpha: 0.08), shape: BoxShape.circle),
            child: const Icon(Icons.logout_rounded, color: AppColors.danger, size: 28),
          )),
          const SizedBox(height: 16),
          const Text("Tizimdan chiqishni\ntasdiqlaysizmi?",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: -0.4)),
          const SizedBox(height: 8),
          Text("Qayta kirish uchun parolingiz kerak bo'ladi.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: Colors.grey.shade500, height: 1.5)),
          const SizedBox(height: 24),
          SizedBox(height: 52, child: ElevatedButton(
            onPressed: () { Navigator.pop(ctx); widget.onLogout(); },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.danger, foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            child: const Text('Ha, chiqish', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          )),
          const SizedBox(height: 10),
          SizedBox(height: 48, child: OutlinedButton(
            onPressed: () => Navigator.pop(ctx),
            style: OutlinedButton.styleFrom(
              foregroundColor: dark ? Colors.white : AppColors.textPrimary,
              side: BorderSide(color: dark ? AppColors.borderDark : AppColors.borderLight, width: 1.5),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            child: const Text('Bekor qilish', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
          )),
          const SizedBox(height: 8),
        ]),
      ),
    );
  }
}
