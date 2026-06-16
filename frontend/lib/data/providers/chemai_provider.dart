import 'package:dio/dio.dart';

import '../../core/constants/api_constants.dart';
import '../../core/network/dio_client.dart';

class ChemAIProvider {
  final DioClient _client;
  const ChemAIProvider(this._client);

  Future<Map<String, dynamic>> fetchProfile() async {
    final r = await _client.get<Map<String, dynamic>>(ApiConstants.profile);
    return r.data ?? {};
  }

  Future<List<dynamic>> fetchChapters() async {
    final r = await _client.get<Map<String, dynamic>>(ApiConstants.chapters);
    return (r.data?['data'] as List<dynamic>?) ?? [];
  }

  Future<List<dynamic>> fetchMentors() async {
    final r = await _client.get<Map<String, dynamic>>(ApiConstants.mentors);
    return (r.data?['data'] as List<dynamic>?) ?? [];
  }

  Future<void> selectMentor(String mentorId) async {
    await _client.post(
      '${ApiConstants.mentors}/select',
      data: {'mentor_id': mentorId},
    );
  }

  Future<Map<String, dynamic>> askAi(String message,
      {String? sessionId}) async {
    final r = await _client.post<Map<String, dynamic>>(
      ApiConstants.askAi,
      data: {'message': message, if (sessionId != null) 'session_id': sessionId},
    );
    return r.data ?? {};
  }
}
