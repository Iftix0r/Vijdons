class AppConstants {
  static const String baseUrl = 'https://vijdontaxi.uz/panel/api';

  // ── Auth ──────────────────────────────────────────────────────────────────
  static const String register = '/driver/register/';
  static const String login    = '/driver/login/';
  static const String profile  = '/driver/profile/';
  static const String duty     = '/driver/duty/';
  static const String fcm      = '/driver/fcm/';
  static const String location = '/driver/location/';

  // ── Geocode ───────────────────────────────────────────────────────────────
  static const String geocodeReverse = '/geocode/reverse/';
  static const String mapsConfig     = '/maps/config/';

  // ── Orders ────────────────────────────────────────────────────────────────
  static const String availableOrders = '/orders/available/';
  static const String myOrders        = '/orders/my/';

  static String acceptOrder(int id)   => '/orders/$id/accept/';
  static String rejectOrder(int id)   => '/orders/$id/reject/';
  static String onWayOrder(int id)    => '/orders/$id/on_way/';
  static String arrivedOrder(int id)  => '/orders/$id/arrived/';
  static String completeOrder(int id) => '/orders/$id/complete/';
  static String cancelOrder(int id)   => '/orders/$id/cancel/';

  // ── Tariff ────────────────────────────────────────────────────────────────
  static const String tariff = '/tariff/';

  // ── Destination mode ──────────────────────────────────────────────────────
  static const String destinationSet = '/driver/destination/';
  static const String destinationGet = '/driver/destination/get/';

  // ── Chat ──────────────────────────────────────────────────────────────────
  static const String chatMessages = '/chat/messages/';
  static const String chatSend     = '/chat/send/';
  static const String chatUnread   = '/chat/unread/';

  // ── Misc ──────────────────────────────────────────────────────────────────
  static const String activeDrivers = '/drivers/locations/';
}
