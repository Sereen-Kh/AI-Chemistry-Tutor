import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:get/get.dart';

import '../core/constants/api_constants.dart';
import '../core/network/dio_client.dart';
import '../data/models/auth_model.dart';

class AuthService extends GetxService {
  final DioClient _client = Get.find<DioClient>();

  // ── Register ─────────────────────────────────────────────────────────────
  // Server returns: {"message": "User created successfully"}

  Future<AuthResponse?> register(RegisterRequest req) async {
    try {
      final res = await _client.post<Map<String, dynamic>>(
        ApiConstants.register,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return AuthResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('register', e);
    }
    return null;
  }

  // ── Login ─────────────────────────────────────────────────────────────────

  Future<AuthResponse?> login(LoginRequest req) async {
    try {
      final res = await _client.post<Map<String, dynamic>>(
        ApiConstants.login,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return AuthResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('login', e);
      rethrow;
    }
    return null;
  }

  // ── Logout ────────────────────────────────────────────────────────────────

  Future<bool> logout() async {
    try {
      final res = await _client.post(ApiConstants.logout);
      return _ok(res.statusCode);
    } on DioException catch (e) {
      _logDio('logout', e);
    }
    return false;
  }

  // ── Get account ───────────────────────────────────────────────────────────

  Future<UserAuth?> getAccount() async {
    try {
      final res = await _client.get<Map<String, dynamic>>(ApiConstants.account);
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return UserAuth.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('getAccount', e);
    }
    return null;
  }

  // ── Refresh token ─────────────────────────────────────────────────────────

  Future<AuthResponse?> refreshToken() async {
    try {
      final res = await _client.post<Map<String, dynamic>>(ApiConstants.refresh);
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return AuthResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('refreshToken', e);
    }
    return null;
  }

  // ── Delete account ────────────────────────────────────────────────────────

  Future<MessageResponse?> deleteAccount() async {
    try {
      final res = await _client.delete<Map<String, dynamic>>(ApiConstants.account);
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return MessageResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('deleteAccount', e);
      rethrow;
    }
    return null;
  }

  // ── Change password ───────────────────────────────────────────────────────

  Future<MessageResponse?> changePassword(ChangePasswordRequest req) async {
    try {
      final res = await _client.put<Map<String, dynamic>>(
        ApiConstants.changePassword,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return MessageResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('changePassword', e);
      rethrow;
    }
    return null;
  }

  // ── Update profile ────────────────────────────────────────────────────────

  Future<MessageResponse?> updateProfile(UpdateProfileRequest req) async {
    try {
      final res = await _client.patch<Map<String, dynamic>>(
        ApiConstants.updateProfile,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return MessageResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('updateProfile', e);
      rethrow;
    }
    return null;
  }

  // ── Forgot password ───────────────────────────────────────────────────────

  Future<MessageResponse?> forgotPassword(ForgotPasswordRequest req) async {
    try {
      final res = await _client.post<Map<String, dynamic>>(
        ApiConstants.forgotPassword,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return MessageResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('forgotPassword', e);
      rethrow;
    }
    return null;
  }

  // ── Reset password ────────────────────────────────────────────────────────

  Future<MessageResponse?> resetPassword(ResetPasswordRequest req) async {
    try {
      final res = await _client.post<Map<String, dynamic>>(
        ApiConstants.resetPassword,
        data: req.toJson(),
      );
      if (_ok(res.statusCode)) {
        final data = _toMap(res.data);
        if (data != null) return MessageResponse.fromJson(data);
      }
    } on DioException catch (e) {
      _logDio('resetPassword', e);
      rethrow;
    }
    return null;
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  bool _ok(int? code) => code == 200 || code == 201;

  Map<String, dynamic>? _toMap(dynamic raw) {
    if (raw is Map<String, dynamic>) return raw;
    if (raw is String) {
      try { return jsonDecode(raw) as Map<String, dynamic>; } catch (_) {}
    }
    return null;
  }

  /// Logs the error and throws an [Exception] with a human-readable message
  /// extracted from FastAPI's validation response (422) or generic server error.
  Never _logDio(String method, DioException e) {
    final status = e.response?.statusCode;
    final body   = e.response?.data;
    print('*** AuthService.$method [$status]: $body');

    // FastAPI 422 returns {"detail": [...]} or {"detail": "string"}
    String msg = 'Server error ($status)';
    if (body is Map) {
      final detail = body['detail'];
      if (detail is List && detail.isNotEmpty) {
        // Take first validation error: "body → field: message"
        final first = detail.first;
        final field = (first['loc'] as List?)?.skip(1).join(' → ') ?? '';
        final reason = first['msg'] ?? '';
        msg = field.isNotEmpty ? '$field: $reason' : reason.toString();
      } else if (detail is String) {
        msg = detail;
      }
    }
    throw Exception(msg);
  }
}
