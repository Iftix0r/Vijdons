import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../models/driver_model.dart';

class ProfileScreen extends StatelessWidget {
  final DriverModel? driver;
  final VoidCallback onLogout;

  const ProfileScreen({super.key, required this.driver, required this.onLogout});

  @override
  Widget build(BuildContext context) {
    if (driver == null) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primary));
    }
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Profil', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const SizedBox(height: 20),

            // Avatar + name
            Center(
              child: Column(
                children: [
                  Container(
                    width: 80, height: 80,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: [Color(0xFFFBBF24), Color(0xFFF59E0B)]),
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [BoxShadow(color: AppTheme.primary.withOpacity(.3), blurRadius: 16, offset: const Offset(0, 6))],
                    ),
                    child: Center(
                      child: Text(
                        driver!.fullName.isNotEmpty ? driver!.fullName[0].toUpperCase() : 'H',
                        style: const TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(driver!.fullName, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(driver!.phoneNumber, style: const TextStyle(color: Colors.grey, fontSize: 14)),
                  const SizedBox(height: 10),
                  _approvalBadge(),
                ],
              ),
            ),
            const SizedBox(height: 28),

            // Info card
            Container(
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.grey.withOpacity(.15)),
              ),
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _infoRow(Icons.directions_car_rounded, 'Mashina modeli', driver!.carModel),
                  const Divider(height: 20),
                  _infoRow(Icons.confirmation_number_outlined, 'Davlat raqami', driver!.carNumber),
                  const Divider(height: 20),
                  _infoRow(Icons.phone_outlined, 'Telefon', driver!.phoneNumber),
                  const Divider(height: 20),
                  _infoRow(
                    driver!.isOnDuty ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                    'Holati',
                    driver!.isOnDuty ? 'Ish navbatida' : 'Dam olmoqda',
                    color: driver!.isOnDuty ? AppTheme.success : Colors.grey,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 28),

            // Logout
            SizedBox(
              height: 52,
              child: OutlinedButton.icon(
                onPressed: () => _confirmLogout(context),
                icon: const Icon(Icons.logout_rounded),
                label: const Text('Chiqish', style: TextStyle(fontWeight: FontWeight.bold)),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.danger,
                  side: const BorderSide(color: AppTheme.danger),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _approvalBadge() {
    Color color;
    String label;
    switch (driver!.approvalStatus) {
      case 'approved':
        color = AppTheme.success; label = 'Tasdiqlangan'; break;
      case 'rejected':
        color = AppTheme.danger;  label = 'Rad etilgan';  break;
      default:
        color = AppTheme.warning; label = 'Kutilmoqda';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
      decoration: BoxDecoration(color: color.withOpacity(.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: color.withOpacity(.3))),
      child: Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold)),
    );
  }

  Widget _infoRow(IconData icon, String label, String value, {Color? color}) => Row(
    children: [
      Icon(icon, size: 20, color: color ?? AppTheme.primary),
      const SizedBox(width: 12),
      Text(label, style: const TextStyle(color: Colors.grey, fontSize: 13)),
      const Spacer(),
      Text(value, style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: color)),
    ],
  );

  void _confirmLogout(BuildContext ctx) {
    showDialog(
      context: ctx,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text('Chiqish', style: TextStyle(fontWeight: FontWeight.bold)),
        content: const Text("Hisobdan chiqishni istaysizmi?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Bekor qilish')),
          ElevatedButton(
            onPressed: () { Navigator.pop(ctx); onLogout(); },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.danger, foregroundColor: Colors.white, elevation: 0),
            child: const Text('Chiqish'),
          ),
        ],
      ),
    );
  }
}
