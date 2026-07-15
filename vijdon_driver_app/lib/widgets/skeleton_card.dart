import 'package:flutter/material.dart';
import '../core/theme.dart';

class SkeletonCard extends StatefulWidget {
  const SkeletonCard({super.key});
  @override
  State<SkeletonCard> createState() => _SkeletonCardState();
}

class _SkeletonCardState extends State<SkeletonCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late final Animation<double> _shimmer;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))
      ..repeat(reverse: true);
    _shimmer = CurvedAnimation(parent: _c, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final base = dark ? AppColors.surfaceDark : const Color(0xFFE2E8F0);
    final shine = dark ? const Color(0xFF20322C) : Colors.white;

    return AnimatedBuilder(
      animation: _shimmer,
      builder: (_, __) => Container(
        margin: const EdgeInsets.only(bottom: 16),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(22),
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
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Shimmer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: base.withValues(alpha: 0.3),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(21)),
              ),
              child: Row(
                children: [
                  _circle(8, base, shine),
                  const SizedBox(width: 8),
                  _box(44, 20, 6, base, shine),
                  const SizedBox(width: 10),
                  _box(90, 16, 6, base, shine),
                  const Spacer(),
                  _box(64, 20, 12, base, shine),
                ],
              ),
            ),
            // Body Shimmer
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Route Block
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: base.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: dark ? AppColors.borderDark : AppColors.borderLight),
                    ),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            _circle(16, base, shine),
                            const SizedBox(width: 12),
                            Expanded(child: _box(double.infinity, 14, 6, base, shine)),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            _circle(16, base, shine),
                            const SizedBox(width: 12),
                            Expanded(child: _box(double.infinity, 14, 6, base, shine)),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  // Chips Block
                  Row(
                    children: [
                      _box(90, 26, 8, base, shine),
                      const Spacer(),
                      _box(60, 26, 8, base, shine),
                      const SizedBox(width: 8),
                      _box(80, 26, 8, base, shine),
                    ],
                  ),
                ],
              ),
            ),
            // Actions Shimmer
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Row(
                children: [
                  Expanded(child: _box(double.infinity, 44, 12, base, shine)),
                  const SizedBox(width: 10),
                  _box(48, 44, 12, base, shine),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _lerp(Color a, Color b) => Color.lerp(a, b, _shimmer.value)!;

  Widget _box(double w, double h, double r, Color base, Color shine) => Container(
    width: w == double.infinity ? null : w,
    height: h,
    decoration: BoxDecoration(color: _lerp(base, shine), borderRadius: BorderRadius.circular(r)),
  );

  Widget _circle(double size, Color base, Color shine) => Container(
    width: size, height: size,
    decoration: BoxDecoration(color: _lerp(base, shine), shape: BoxShape.circle),
  );
}
