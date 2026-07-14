import 'package:flutter/material.dart';

class SkeletonCard extends StatefulWidget {
  const SkeletonCard({super.key});
  @override
  State<SkeletonCard> createState() => _SkeletonCardState();
}

class _SkeletonCardState extends State<SkeletonCard> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.4, end: 1.0).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _anim,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Colors.grey.withValues(alpha: 0.1)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [_box(60, 22, 8), const SizedBox(width: 10), _box(120, 22, 8), const Spacer(), _box(70, 22, 20)]),
            const SizedBox(height: 16),
            _box(double.infinity, 14, 6),
            const SizedBox(height: 8),
            _box(double.infinity, 14, 6),
            const SizedBox(height: 14),
            _box(140, 12, 6),
            const SizedBox(height: 14),
            Row(children: [Expanded(child: _box(double.infinity, 38, 10)), const SizedBox(width: 8), Expanded(child: _box(double.infinity, 38, 10))]),
          ],
        ),
      ),
    );
  }

  Widget _box(double w, double h, double r) => Container(
    width: w == double.infinity ? null : w,
    height: h,
    decoration: BoxDecoration(
      color: Colors.grey.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(r),
    ),
  );
}
