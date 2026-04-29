import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ai_chemistry_tutor/core/api/api_client.dart';

// State management: Provider — team will decide whether to keep or replace.
// To swap: rewrite only this file and update main.dart registration.
class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();

  String? _token;
  bool _isLoading = false;
  String? _error;

  String? get token => _token;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _token != null;

  /// Call once on app start to restore saved session.
  Future<void> loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
    notifyListeners();
  }

  Future<bool> register(String name, String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _apiClient.register(name: name, email: email, password: password);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = _parseError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final token = await _apiClient.login(email: email, password: password);
      _token = token;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', token);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = _parseError(e);
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    notifyListeners();
  }

  String _parseError(Object e) {
    final msg = e.toString();
    if (msg.contains('400')) return 'Email already registered.';
    if (msg.contains('401')) return 'Invalid email or password.';
    return 'Something went wrong. Please try again.';
  }
}
