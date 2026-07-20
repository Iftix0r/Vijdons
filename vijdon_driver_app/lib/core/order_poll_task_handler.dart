import 'dart:convert';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:http/http.dart' as http;
import 'notification_service.dart';

// Har doim TOP-LEVEL yoki static bo'lishi SHART — bu funksiya fon xizmati
// uchun ishga tushiriladigan alohida Dart isolate'da chaqiriladi.
@pragma('vm:entry-point')
void startOrderPollTask() {
  FlutterForegroundTask.setTaskHandler(OrderPollTaskHandler());
}

// Haydovchi "ish navbatida" bo'lgan butun vaqt davomida (ilova ochiq yoki
// fonda/yopiq bo'lishidan qat'i nazar) ishlaydi — Android ilova jarayonini
// fondan "o'chirib" qo'yishi (masalan MIUI'da) tufayli yangi buyurtma
// bildirishnomasi faqat ilova qayta ochilgandagina kelib turgan muammoni
// hal qiladi (foreground service Android tomonidan deyarli hech qachon
// o'chirilmaydi, chunki u doimiy bildirishnoma bilan foydalanuvchiga
// ko'rinib turadi).
class OrderPollTaskHandler extends TaskHandler {
  final Set<int> _knownIds = <int>{};

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    // Bu ALOHIDA isolate — asosiy isolate bilan xotira (shu jumladan
    // NotificationService'ning statik holati) umumiy emas, shuning uchun
    // bildirishnoma xizmati shu yerda ham qaytadan ishga tushiriladi.
    await NotificationService.init();
  }

  @override
  void onRepeatEvent(DateTime timestamp) {
    _pollOrders();
  }

  Future<void> _pollOrders() async {
    try {
      final uri = Uri.parse('https://vijdontaxi.uz/driver/orders/json/');
      final resp = await http.get(uri, headers: {
        'X-Requested-With': 'XMLHttpRequest',
      }).timeout(const Duration(seconds: 8));
      if (resp.statusCode != 200) return;
      final data = json.decode(resp.body) as Map<String, dynamic>;
      final ids =
          (data['new_ids'] as List?)?.map((e) => e as int).toSet() ?? {};
      if (ids.isEmpty) {
        _knownIds.clear();
        return;
      }

      final newIds = ids.difference(_knownIds);
      _knownIds
        ..clear()
        ..addAll(ids);

      if (newIds.isNotEmpty) {
        await NotificationService.notifyNewOrder(newIds.length);
        // Ilova ekranda ochiq bo'lsa, uning sahifasini ham yangilash uchun
        // asosiy isolate'ga signal yuboramiz — bu yerdan (fon isolate'idan)
        // WebView'ga to'g'ridan-to'g'ri kira olmaymiz, u asosiy isolate'da
        // yashaydi.
        FlutterForegroundTask.sendDataToMain({'newOrders': newIds.length});
      }
    } catch (_) {}
  }

  @override
  Future<void> onDestroy(DateTime timestamp, bool isTimeout) async {}

  @override
  void onReceiveData(Object data) {}

  @override
  void onNotificationButtonPressed(String id) {}

  @override
  void onNotificationPressed() {
    FlutterForegroundTask.launchApp('/');
  }

  @override
  void onNotificationDismissed() {}
}
