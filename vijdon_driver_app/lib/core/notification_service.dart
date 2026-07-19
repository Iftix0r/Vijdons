import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:app_badge_plus/app_badge_plus.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final FlutterLocalNotificationsPlugin _notif =
      FlutterLocalNotificationsPlugin();
  static final AudioPlayer _player = AudioPlayer();
  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;
    try {
      const androidSettings =
          AndroidInitializationSettings('@mipmap/ic_launcher');
      const iosSettings = DarwinInitializationSettings(
        requestAlertPermission: true,
        requestBadgePermission: true,
        requestSoundPermission: true,
      );

      await _notif.initialize(
        const InitializationSettings(
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
    } catch (_) {
      _initialized = true;
    }
  }

  static Future<void> notifyNewOrder(int count) async {
    await _playOrderSound();
    await _showNotification(count);
    await _updateBadge(count);
  }

  static Future<void> clearBadge() async {
    await _updateBadge(0);
  }

  // app_badge_plus faqat Android/iOS'da qo'llab-quvvatlanadi (masalan Linux
  // desktop'da mavjud emas) — shuning uchun avval tekshiramiz.
  static Future<void> _updateBadge(int count) async {
    try {
      if (await AppBadgePlus.isSupported()) {
        await AppBadgePlus.updateBadge(count);
      }
    } catch (_) {}
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
        ? 'Yangi buyurtma'
        : '$count ta yangi buyurtma';
    final String body = count == 1
        ? '\u{1F4CD} Yaqin atrofda buyurtma kutmoqda'
        : '\u{1F4CD} $count ta buyurtma sizni kutmoqda';

    final vibrationPattern = Int64List.fromList([0, 200, 100, 200, 100, 400]);

    final androidDetails = AndroidNotificationDetails(
      'new_orders_channel',
      'Yangi buyurtmalar',
      channelDescription: 'Yangi buyurtma kelganda bildirishnoma',
      importance: Importance.max,
      priority: Priority.high,
      ticker: title,
      fullScreenIntent: true,
      playSound: false,
      enableVibration: true,
      vibrationPattern: vibrationPattern,
      icon: '@mipmap/ic_launcher',
      color: const Color(0xFFFFD600),
      largeIcon: const DrawableResourceAndroidBitmap('@mipmap/ic_launcher'),
      styleInformation: BigTextStyleInformation(
        body,
        htmlFormatBigText: false,
        contentTitle: title,
        summaryText: 'Vijdon Driver',
      ),
      category: AndroidNotificationCategory.call,
      visibility: NotificationVisibility.public,
      ongoing: false,
      autoCancel: true,
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
      interruptionLevel: InterruptionLevel.timeSensitive,
      threadIdentifier: 'new_orders',
    );

    await _notif.show(
      1001,
      title,
      body,
      NotificationDetails(
        android: androidDetails,
        iOS: iosDetails,
      ),
    );
  }

  static Future<void> dispose() async {
    await _player.dispose();
  }
}
