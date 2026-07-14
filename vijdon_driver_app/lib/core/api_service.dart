import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'constants.dart';

class ApiService {
  static const _tokenKey = 'auth_token';

  // ── Token ──────────────────────────────────────────────────────────────────

  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_tokenKey);
  }

  static Future<void> saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
  }

  static Future<void> clearToken() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  static Uri _uri(String path) => Uri.parse('${AppConstants.baseUrl}$path');

  static Future<Map<String, String>> _headers({bool auth = true}) async {
    final h = {'Content-Type': 'application/json'};
    if (auth) {
      final token = await getToken();
      if (token != null) h['Authorization'] = 'Token $token';
    }
    return h;
  }

  static Map<String, dynamic> _decode(http.Response r) {
    final body = json.decode(utf8.decode(r.bodyBytes));
    if (r.statusCode >= 400) {
      final msg = body is Map
          ? (body['detail'] ?? body.values.first?.toString() ?? 'Xatolik')
          : body.toString();
      throw ApiException(msg.toString(), r.statusCode);
    }
    return body is Map<String, dynamic> ? body : {'data': body};
  }

  // ── Auth ───────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> register(Map<String, dynamic> data) async {
    final r = await http.post(
      _uri(AppConstants.register),
      headers: await _headers(auth: false),
      body: json.encode(data),
    );
    return _decode(r);
  }

  static Future<Map<String, dynamic>> login(String phone, String password) async {
    final r = await http.post(
      _uri(AppConstants.login),
      headers: await _headers(auth: false),
      body: json.encode({'phone_number': phone, 'password': password}),
    );
    final body = _decode(r);
    await saveToken(body['token']);
    return body;
  }

  static Future<void> logout() => clearToken();

  // ── Profile ────────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> getProfile() async {
    final r = await http.get(_uri(AppConstants.profile), headers: await _headers());
    return _decode(r);
  }

  static Future<Map<String, dynamic>> toggleDuty() async {
    final r = await http.post(_uri(AppConstants.duty), headers: await _headers());
    return _decode(r);
  }

  // ── Orders ─────────────────────────────────────────────────────────────────

  static Future<List<dynamic>> getAvailableOrders() async {
    final r = await http.get(_uri(AppConstants.availableOrders), headers: await _headers());
    final body = _decode(r);
    return body['data'] as List? ?? (r.body.startsWith('[') ? json.decode(r.body) : []);
  }

  static Future<List<dynamic>> getMyOrders() async {
    final r = await http.get(_uri(AppConstants.myOrders), headers: await _headers());
    return json.decode(utf8.decode(r.bodyBytes)) as List;
  }

  static Future<Map<String, dynamic>> orderAction(String endpoint) async {
    final r = await http.post(_uri(endpoint), headers: await _headers());
    return _decode(r);
  }
}

class ApiException implements Exception {
  final String message;
  final int statusCode;
  ApiException(this.message, this.statusCode);
  @override
  String toString() => message;
}
