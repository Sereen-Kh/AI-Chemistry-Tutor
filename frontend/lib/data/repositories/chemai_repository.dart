import 'package:dio/dio.dart';

import '../../core/utils/failures.dart';
import '../models/chapter_model.dart';
import '../models/mentor_model.dart';
import '../models/user_model.dart';
import '../providers/chemai_provider.dart';

typedef Result<T> = ({T? data, Failure? failure});

class ChemAIRepository {
  final ChemAIProvider _provider;
  const ChemAIRepository(this._provider);

  Future<Result<UserModel>> fetchProfile() async {
    try {
      final raw = await _provider.fetchProfile();
      return (data: UserModel.fromJson(raw), failure: null);
    } on DioException catch (e) {
      return (data: null, failure: _map(e));
    } catch (_) {
      return (data: null, failure: const ParseFailure());
    }
  }

  Future<Result<List<ChapterModel>>> fetchChapters() async {
    try {
      final raw = await _provider.fetchChapters();
      return (
        data: raw
            .map((e) => ChapterModel.fromJson(e as Map<String, dynamic>))
            .toList(),
        failure: null,
      );
    } on DioException catch (e) {
      return (data: null, failure: _map(e));
    } catch (_) {
      return (data: null, failure: const ParseFailure());
    }
  }

  Future<Result<List<MentorModel>>> fetchMentors() async {
    try {
      final raw = await _provider.fetchMentors();
      return (
        data: raw
            .map((e) => MentorModel.fromJson(e as Map<String, dynamic>))
            .toList(),
        failure: null,
      );
    } on DioException catch (e) {
      return (data: null, failure: _map(e));
    } catch (_) {
      return (data: null, failure: const ParseFailure());
    }
  }

  Future<Result<void>> selectMentor(String mentorId) async {
    try {
      await _provider.selectMentor(mentorId);
      return (data: null, failure: null);
    } on DioException catch (e) {
      return (data: null, failure: _map(e));
    }
  }

  Failure _map(DioException e) => switch (e.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout =>
          const TimeoutFailure(),
        DioExceptionType.connectionError => const NetworkFailure(),
        DioExceptionType.badResponse    => ServerFailure(
            e.response?.statusMessage ?? 'Server error',
            statusCode: e.response?.statusCode,
          ),
        _ => const UnknownFailure(),
      };
}
