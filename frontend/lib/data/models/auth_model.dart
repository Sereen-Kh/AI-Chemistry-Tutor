// ── Request models ────────────────────────────────────────────────────────────

class RegisterRequest {
  final String fullName;
  final String email;
  final String password;
  final String gender;

  const RegisterRequest({
    required this.fullName,
    required this.email,
    required this.password,
    required this.gender,
  });

  Map<String, dynamic> toJson() => {
        'full_name': fullName,
        'email': email,
        'password': password,
        'gender': gender,
      };
}

class LoginRequest {
  final String email;
  final String password;

  const LoginRequest({required this.email, required this.password});

  Map<String, dynamic> toJson() => {'email': email, 'password': password};
}

class ChangePasswordRequest {
  final String oldPassword;
  final String newPassword;

  const ChangePasswordRequest({
    required this.oldPassword,
    required this.newPassword,
  });

  Map<String, dynamic> toJson() => {
        'old_password': oldPassword,
        'new_password': newPassword,
      };
}

class UpdateProfileRequest {
  final String fullName;
  final String gender;

  const UpdateProfileRequest({required this.fullName, required this.gender});

  Map<String, dynamic> toJson() => {'full_name': fullName, 'gender': gender};
}

class ForgotPasswordRequest {
  final String email;

  const ForgotPasswordRequest({required this.email});

  Map<String, dynamic> toJson() => {'email': email};
}

class ResetPasswordRequest {
  final String token;
  final String newPassword;

  const ResetPasswordRequest({required this.token, required this.newPassword});

  Map<String, dynamic> toJson() => {
        'token': token,
        'new_password': newPassword,
      };
}

// ── Response models ───────────────────────────────────────────────────────────

class AuthResponse {
  final String accessToken;
  final String tokenType;
  final UserAuth? user; // null when server omits the user object (e.g. login)

  const AuthResponse({
    required this.accessToken,
    required this.tokenType,
    this.user,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> j) {
    final raw = j['user'];
    return AuthResponse(
      accessToken: j['access_token'] as String? ?? '',
      tokenType: j['token_type'] as String? ?? 'bearer',
      user: raw is Map<String, dynamic> ? UserAuth.fromJson(raw) : null,
    );
  }
}

class UserAuth {
  final String id;
  final String fullName;
  final String email;
  final String gender;

  const UserAuth({
    required this.id,
    required this.fullName,
    required this.email,
    required this.gender,
  });

  factory UserAuth.fromJson(Map<String, dynamic> j) => UserAuth(
        id: j['id']?.toString() ?? '',
        fullName: j['full_name'] as String? ?? '',
        email: j['email'] as String? ?? '',
        gender: j['gender'] as String? ?? '',
      );

  UserAuth copyWith({String? fullName}) => UserAuth(
        id: id,
        fullName: fullName ?? this.fullName,
        email: email,
        gender: gender,
      );
}

// Generic response for endpoints that return only a message field
class MessageResponse {
  final String message;

  const MessageResponse({required this.message});

  factory MessageResponse.fromJson(Map<String, dynamic> j) =>
      MessageResponse(message: j['message'] as String? ?? '');
}
