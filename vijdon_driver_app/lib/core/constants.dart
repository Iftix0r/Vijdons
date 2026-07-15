class AppConstants {
  // Change to your server URL
  static const String baseUrl = 'https://vijdontaxi.uz/panel/api';

  // Auth
  static const String register = '/driver/register/';
  static const String login = '/driver/login/';
  static const String profile = '/driver/profile/';
  static const String duty = '/driver/duty/';
  static const String fcm = '/driver/fcm/';
  static const String location = '/driver/location/';

  // Orders
  static const String availableOrders = '/orders/available/';
  static const String myOrders = '/orders/my/';

  // Chat
  static const String chatMessages = '/chat/messages/';
  static const String chatSend = '/chat/send/';
  static const String chatUnread = '/chat/unread/';
  static String onWayOrder(int id) => '/orders/$id/on_way/';
  static String acceptOrder(int id) => '/orders/$id/accept/';
  static String arrivedOrder(int id) => '/orders/$id/arrived/';
  static String completeOrder(int id) => '/orders/$id/complete/';
  static String cancelOrder(int id) => '/orders/$id/cancel/';
}
