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
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat(reverse: true);
    _shimmer = CurvedAnimation(parent: _c, curve: Curves.easeInOut);
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final base = dark ? AppColors.surfaceDark : const Color(0xFFF1F5F9);
    final shine = dark ? const Color(0xFF252E42) : Colors.white;
    return AnimatedBuilder(
      animation: _shimmer,
      builder: (_, __) => Container(
        margin: const EdgeInsets.only(bottom: 14),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: dark ? AppColors.cardDark : Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.grey.withValues(alpha: 0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              _box(56, 22, 8, base, shine),
              const SizedBox(width: 10),
              _box(130, 22, 8, base, shine),
              const Spacer(),
              _box(72, 24, 20, base, shine),
            ]),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: base.withValues(alpha: 0.5), borderRadius: BorderRadius.circular(12)),
              child: Column(children: [
                Row(children: [
                  _circle(20, base, shine),
                  const SizedBox(width: 10),
                  Expanded(child: _box(double.infinity, 13, 6, base, shine)),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  _circle(20, base, shine),
                  const SizedBox(width: 10),
                  Expanded(child: _box(double.infinity, 13, 6, base, shine)),
                ]),
              ]),
            ),
            const SizedBox(height: 12),
            _box(160, 12, 6, base, shine),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(child: _box(double.infinity, 42, 12, base, shine)),
              const SizedBox(width: 8),
              _box(44, 42, 12, base, shine),
            ]),
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
