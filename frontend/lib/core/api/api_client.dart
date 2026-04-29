import 'dart:convert';
import 'package:http/http.dart' as http;

/// Central HTTP client for all backend communication.
/// Base URL reads from a const — replace with env loading once flutter_dotenv is wired up.
class ApiClient {
  // TODO: Move to .env once flutter_dotenv is configured
  static const String _baseUrl = 'http://localhost:8000/api/v1';

  Future<void> register({
    required String name,
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name, 'email': email, 'password': password}),
    );
    if (response.statusCode != 201) {
      throw Exception('${response.statusCode}:${response.body}');
    }
  }

  Future<String> login({
    required String email,
    required String password,
  }) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['access_token'] as String;
    }
    throw Exception('${response.statusCode}:${response.body}');
  }
}

