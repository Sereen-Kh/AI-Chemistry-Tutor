import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class AppLogInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions o, RequestInterceptorHandler h) {
    if (kDebugMode) debugPrint('→ ${o.method} ${o.uri}');
    h.next(o);
  }

  @override
  void onResponse(Response r, ResponseInterceptorHandler h) {
    if (kDebugMode) debugPrint('← ${r.statusCode} ${r.requestOptions.uri}');
    h.next(r);
  }

  @override
  void onError(DioException e, ErrorInterceptorHandler h) {
    if (kDebugMode) debugPrint('✕ ${e.type}: ${e.message}');
    h.next(e);
  }
}
