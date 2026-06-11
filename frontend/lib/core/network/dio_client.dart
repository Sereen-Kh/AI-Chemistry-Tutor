import 'package:dio/dio.dart';

import '../constants/api_constants.dart';
import 'interceptors/auth_interceptor.dart';
import 'interceptors/log_interceptor.dart';

class DioClient {
  late final Dio dio;

  DioClient() {
    dio = Dio(BaseOptions(
      baseUrl: ApiConstants.baseUrl,
      connectTimeout: ApiConstants.connectTimeout,
      receiveTimeout: ApiConstants.receiveTimeout,
      // contentType drives Dio 5.x body serialisation (Map → jsonEncode).
      // Setting Content-Type only in headers does NOT trigger JSON encoding.
      contentType: 'application/json',
      headers: {
        'Accept': 'application/json',
        // Required for ngrok free tier — bypasses the browser warning interstitial.
        // Safe to keep in production (ignored by real servers).
        'ngrok-skip-browser-warning': 'true',
      },
    ))
      ..interceptors.addAll([
        AuthInterceptor(),
        AppLogInterceptor(),
      ]);
  }

  Future<Response<T>> get<T>(String path,
      {Map<String, dynamic>? params, Options? options}) =>
      dio.get<T>(path, queryParameters: params, options: options);

  Future<Response<T>> post<T>(String path,
      {dynamic data, Options? options}) =>
      dio.post<T>(path, data: data, options: options);

  Future<Response<T>> put<T>(String path,
      {dynamic data, Options? options}) =>
      dio.put<T>(path, data: data, options: options);

  Future<Response<T>> patch<T>(String path,
          {dynamic data, Options? options}) =>
      dio.patch<T>(path, data: data, options: options);

  Future<Response<T>> delete<T>(String path,
          {dynamic data, Options? options}) =>
      dio.delete<T>(path, data: data, options: options);
}
