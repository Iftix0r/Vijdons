import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final FlutterLocalNotificationsPlugin _notif =
      FlutterLocalNotificationsPlugin();
  static final AudioPlayer _player = AudioPlayer();
  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;

    const androidSettings =
        AndroidInitializationSettings('@drawable/ic_notification');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    await _notif.initialize(
      settings: const InitializationSettings(
        android: androidSettings,
        iOS: iosSettings,
      ),
      onDidReceiveNotificationResponse: (_) {},
    );

    final vibrationPattern = Int64List.fromList([0, 300, 200, 300]);
    final channel = AndroidNotificationChannel(
      'new_orders_channel',
      'Yangi buyurtmalar',
      description: 'Yangi buyurtma kelganda bildirishnoma',
      importance: Importance.max,
      playSound: false,
      enableVibration: true,
      vibrationPattern: vibrationPattern,
    );

    final androidPlugin = _notif.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    await androidPlugin?.createNotificationChannel(channel);
    await androidPlugin?.requestNotificationsPermission();

    _initialized = true;
  }

  static Future<void> notifyNewOrder(int count) async {
    await _playOrderSound();
    await _showNotification(count);
  }

  static Future<void> _playOrderSound() async {
    try {
      await _player.stop();
      await _player.setReleaseMode(ReleaseMode.loop);
      await _player.play(AssetSource('sounds/new_order.wav'));
    } catch (_) {}
  }

  static Future<void> stopOrderSound() async {
    try {
      await _player.stop();
    } catch (_) {}
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
      icon: '@drawable/ic_notification',
      color: const Color(0xFFFFD600),
      largeIcon: const DrawableResourceAndroidBitmap('@mipmap/ic_launcher'),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    await _notif.show(
      id: 1001,
      title: title,
      body: body,
      notificationDetails: NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      ),
    );
  }

  static Future<void> dispose() async {
    await _player.dispose();
  }
}
