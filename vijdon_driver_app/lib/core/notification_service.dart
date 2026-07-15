import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Buyurtma kelganda ovoz va bildirishnoma chiqarish servisi
class NotificationService {
  static final FlutterLocalNotificationsPlugin _notif =
      FlutterLocalNotificationsPlugin();
  static final AudioPlayer _player = AudioPlayer();

  static bool _initialized = false;

  // ── Init ──────────────────────────────────────────────────────────────────

  static Future<void> init() async {
    if (_initialized) return;

    // Android init
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    // iOS init
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _notif.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (_) {},
    );

    // Android notification channel
    final vibrationPattern = Int64List.fromList([0, 300, 200, 300]);

    final channel = AndroidNotificationChannel(
      'new_orders_channel',
      'Yangi buyurtmalar',
      description: 'Yangi buyurtma kelganda bildirishnoma',
      importance: Importance.max,
      playSound: false, // ovozni audioplayers orqali chiqaramiz
      enableVibration: true,
      vibrationPattern: vibrationPattern,
    );

    final androidPlugin = _notif.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(channel);
    await androidPlugin?.requestNotificationsPermission();

    _initialized = true;
  }

  // ── Show notification + play sound ────────────────────────────────────────

  /// [count] - yangi buyurtmalar soni
  static Future<void> notifyNewOrder(int count) async {
    await _playOrderSound();
    await _showNotification(count);
  }

  static Future<void> _playOrderSound() async {
    try {
      await _player.stop();
      await _player.play(AssetSource('sounds/new_order.wav'));
    } catch (_) {
      // Ovoz chiqmasa ham ilovani to'xtatmaymiz
    }
  }

  static Future<void> _showNotification(int count) async {
    final String title = count == 1
        ? '🚖 Yangi buyurtma keldi!'
        : '🚖 $count ta yangi buyurtma!';
    const String body = "Buyurtmani ko'rish uchun bosing";

    final vibrationPattern = Int64List.fromList([0, 300, 200, 300]);

    final androidDetails = AndroidNotificationDetails(
      'new_orders_channel',
      'Yangi buyurtmalar',
      channelDescription: 'Yangi buyurtma kelganda bildirishnoma',
      importance: Importance.max,
      priority: Priority.high,
      ticker: 'Yangi buyurtma',
      fullScreenIntent: true,
      playSound: false,
      enableVibration: true,
      vibrationPattern: vibrationPattern,
      icon: '@mipmap/ic_launcher',
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _notif.show(
      id: 1001,
      title,
      body,
      details,
    );
  }

  static Future<void> dispose() async {
    await _player.dispose();
  }
}
