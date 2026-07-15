class AppConstants {
  // Change to your server URL
  static const String baseUrl = 'https://vijdontaxi.uz/panel/api';

  // Auth
  static const String register = '/driver/register/';
  static const String login    = '/driver/login/';
  static const String profile  = '/driver/profile/';
  static const String duty     = '/driver/duty/';
  static const String fcm      = '/driver/fcm/';
  static const String location = '/driver/location/';

  // Orders
  static const String availableOrders = '/orders/available/';
  static const String myOrders        = '/orders/my/';

  static String acceptOrder(int id)   => '/orders/$id/accept/';
  static String onWayOrder(int id)    => '/orders/$id/on_way/';
  static String completeOrder(int id) => '/orders/$id/complete/';
  static String cancelOrder(int id)   => '/orders/$id/cancel/';
}
