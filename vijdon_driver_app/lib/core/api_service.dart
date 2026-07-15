import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'constants.dart';

class ApiService {
  static const _tokenKey = 'auth_token';
  static const _timeout  = Duration(seconds: 15);

  // ── Token ──────────────────────────────────────────────────────────────────

  static Future<String?> getToken() async {
    final p = await SharedPreferences.getInstance();
    return p.getString(_tokenKey);
  }

  static Future<void> saveToken(String token) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_tokenKey, token);
  }

  static Future<void> clearToken() async {
    final p = await SharedPreferences.getInstance();
    await p.remove(_tokenKey);
  }

  // ── Internals ──────────────────────────────────────────────────────────────

  static Uri _uri(String path) => Uri.parse('${AppConstants.baseUrl}$path');

  static Future<Map<String, String>> _headers({bool auth = true}) async {
    final h = <String, String>{'Content-Type': 'application/json'};
    if (auth) {
      final token = await getToken();
      if (token != null) h['Authorization'] = 'Token $token';
    }
    return h;
  }

  static dynamic _decode(http.Response r) {
    dynamic body;
    try { body = json.decode(utf8.decode(r.bodyBytes)); } catch (_) { body = r.body; }

    if (r.statusCode == 401) {
      clearToken();
      throw const ApiException('Sessiya tugadi. Qayta kiring.', 401);
    }
    if (r.statusCode >= 400) {
      String msg = 'Xatolik yuz berdi';
      if (body is Map) {
        msg = body['detail']?.toString() ??
              body.values.firstWhere((v) => v != null, orElse: () => 'Xatolik').toString();
      }
      throw ApiException(msg, r.statusCode);
    }
    return body;
  }

  static Future<http.Response> _get(String path) async {
    try {
      return await http.get(_uri(path), headers: await _headers()).timeout(_timeout);
    } on SocketException {
      throw const ApiException("Internet aloqasi yo'q.", 0);
    } on TimeoutException {
      throw const ApiException('Server javob bermadi.', 0);
    }
  }

  static Future<http.Response> _post(String path,
      {Map<String, dynamic>? body, bool auth = true}) async {
    try {
      return await http
          .post(_uri(path),
              headers: await _headers(auth: auth),
              body: body != null ? json.encode(body) : null)
          .timeout(_timeout);
    } on SocketException {
      throw const ApiException("Internet aloqasi yo'q.", 0);
    } on TimeoutException {
      throw const ApiException('Server javob bermadi.', 0);
    }
  }

  // ── Auth ───────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> register(Map<String, dynamic> data) async {
    final r = await _post(AppConstants.register, body: data, auth: false);
    return _decode(r) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> login(String phone, String password) async {
    final r = await _post(AppConstants.login,
        body: {'phone_number': phone, 'password': password}, auth: false);
    final body = _decode(r) as Map<String, dynamic>;
    await saveToken(body['token'] as String);
    return body;
  }

  static Future<void> logout() => clearToken();

  // ── Profile ────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> getProfile() async {
    final r = await _get(AppConstants.profile);
    return _decode(r) as Map<String, dynamic>;
  }

  static Future<Map<String, dynamic>> toggleDuty() async {
    final r = await _post(AppConstants.duty);
    return _decode(r) as Map<String, dynamic>;
  }

  static Future<void> updateFcmToken(String token) async {
    await _post(AppConstants.fcm, body: {'fcm_token': token});
  }

  static Future<void> updateLocation(double lat, double lng) async {
    await _post(AppConstants.location, body: {'latitude': lat, 'longitude': lng});
  }

  // ── Orders ─────────────────────────────────────────────────────────────────

  static Future<List<dynamic>> getAvailableOrders() async {
    final r = await _get(AppConstants.availableOrders);
    final raw = _decode(r);
    if (raw is List) return raw;
    return (raw as Map<String, dynamic>)['data'] as List? ?? [];
  }

  static Future<List<dynamic>> getMyOrders() async {
    final r = await _get(AppConstants.myOrders);
    final raw = _decode(r);
    if (raw is List) return raw;
    return (raw as Map<String, dynamic>)['data'] as List? ?? [];
  }

  static Future<Map<String, dynamic>> orderAction(String endpoint) async {
    final r = await _post(endpoint);
    return _decode(r) as Map<String, dynamic>;
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;
  const ApiException(this.message, this.statusCode);
  @override
  String toString() => message;

  bool get isUnauthorized => statusCode == 401;
  bool get isNetworkError => statusCode == 0;
}
