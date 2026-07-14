import 'package:flutter/material.dart';
import '../core/api_service.dart';
import '../core/theme.dart';
import '../models/order_model.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<OrderModel> _orders = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await ApiService.getMyOrders();
      if (mounted) setState(() => _orders = list.map((e) => OrderModel.fromJson(e)).toList());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString()), backgroundColor: AppTheme.danger),
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'completed': return AppTheme.success;
      case 'cancelled': return AppTheme.danger;
      case 'on_way':    return const Color(0xFF8B5CF6);
      case 'accepted':  return AppTheme.info;
      default:          return AppTheme.warning;
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: RefreshIndicator(
        onRefresh: _load,
        color: AppTheme.primary,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
                child: Row(
                  children: [
                    const Text('Buyurtmalar tarixi', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                    const Spacer(),
                    Text('${_orders.length} ta', style: const TextStyle(color: Colors.grey, fontSize: 13)),
                  ],
                ),
              ),
            ),
            if (_loading)
              const SliverFillRemaining(child: Center(child: CircularProgressIndicator(color: AppTheme.primary)))
            else if (_orders.isEmpty)
              SliverFillRemaining(
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.history_rounded, size: 64, color: Colors.grey.shade300),
                      const SizedBox(height: 12),
                      const Text('Tarix bo\'sh', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    ],
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (ctx, i) {
                      final o = _orders[i];
                      return Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        decoration: BoxDecoration(
                          color: Theme.of(context).cardColor,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.grey.withOpacity(.15)),
                        ),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          leading: Container(
                            width: 42, height: 42,
                            decoration: BoxDecoration(
                              color: _statusColor(o.status).withOpacity(.12),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(
                              o.isCompleted ? Icons.check_circle_rounded
                                  : o.isCancelled ? Icons.cancel_rounded
                                  : Icons.route_rounded,
                              color: _statusColor(o.status), size: 22,
                            ),
                          ),
                          title: Text('${o.fromAddress} → ${o.toAddress}',
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                              maxLines: 1, overflow: TextOverflow.ellipsis),
                          subtitle: Text(o.clientPhone, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                          trailing: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: _statusColor(o.status).withOpacity(.12),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(o.statusLabel, style: TextStyle(color: _statusColor(o.status), fontSize: 11, fontWeight: FontWeight.bold)),
                              ),
                              const SizedBox(height: 4),
                              Text('#${o.id}', style: const TextStyle(color: Colors.grey, fontSize: 11)),
                            ],
                          ),
                        ),
                      );
                    },
                    childCount: _orders.length,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
