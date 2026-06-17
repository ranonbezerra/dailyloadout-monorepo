import 'dart:async';

import 'package:app/core/auth/auth_token_store.dart';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

/// Callback invoked when token refresh fails and the user must
/// re-authenticate.
typedef OnForceLogout = void Function();

/// Singleton-style Dio HTTP client with auth interceptor.
///
/// Automatically attaches Bearer tokens and attempts silent refresh
/// on 401 responses.
class ApiClient {
  ApiClient({
    required AuthTokenStore tokenStore,
    OnForceLogout? onForceLogout,
    String baseUrl = 'http://localhost:8100',
    Dio? dio,
  })  : _tokenStore = tokenStore,
        _onForceLogout = onForceLogout {
    _dio = dio ??
        Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 10),
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        );

    _dio.interceptors.add(_AuthInterceptor(
      dio: _dio,
      tokenStore: _tokenStore,
      onForceLogout: _onForceLogout,
      logger: _logger,
    ));
  }

  final AuthTokenStore _tokenStore;
  final OnForceLogout? _onForceLogout;
  final Logger _logger = Logger(printer: PrettyPrinter(methodCount: 0));
  late final Dio _dio;

  /// Exposes the configured [Dio] instance for direct use.
  Dio get dio => _dio;
}

class _AuthInterceptor extends Interceptor {
  _AuthInterceptor({
    required Dio dio,
    required AuthTokenStore tokenStore,
    required this.onForceLogout,
    required this.logger,
  })  : _dio = dio,
        _tokenStore = tokenStore;

  final Dio _dio;
  final AuthTokenStore _tokenStore;
  final OnForceLogout? onForceLogout;
  final Logger logger;

  bool _isRefreshing = false;
  final List<_RetryEntry> _pendingRetries = [];

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final accessToken = _tokenStore.getAccessToken();
    if (accessToken != null) {
      options.headers['Authorization'] = 'Bearer $accessToken';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final response = err.response;
    final requestOptions = err.requestOptions;

    // Only handle 401 responses, and skip the refresh endpoint itself
    // to avoid infinite loops.
    if (response?.statusCode != 401 ||
        requestOptions.path.contains('/auth/refresh')) {
      return handler.next(err);
    }

    if (_isRefreshing) {
      // Another request is already refreshing — queue this one.
      final completer = Completer<Response<dynamic>>();
      _pendingRetries.add(_RetryEntry(
        options: requestOptions,
        completer: completer,
      ));
      try {
        final result = await completer.future;
        return handler.resolve(result);
      } on DioException catch (e) {
        return handler.next(e);
      }
    }

    _isRefreshing = true;

    try {
      final refreshToken = await _tokenStore.getRefreshToken();
      if (refreshToken == null) {
        _failAllPending(err);
        _forceLogout();
        return handler.next(err);
      }

      // Attempt to refresh the token pair.
      final refreshResponse = await _dio.post<Map<String, dynamic>>(
        '/v1/auth/refresh',
        data: {'refresh_token': refreshToken},
      );

      final data = refreshResponse.data!;
      final newAccessToken = data['access_token'] as String;
      final newRefreshToken = data['refresh_token'] as String;

      await _tokenStore.saveTokens(
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
      );

      // Retry the original request with the new token.
      requestOptions.headers['Authorization'] = 'Bearer $newAccessToken';
      final retryResponse = await _dio.fetch<dynamic>(requestOptions);

      // Resolve any queued requests.
      _resolveAllPending(newAccessToken);

      return handler.resolve(retryResponse);
    } on DioException catch (e) {
      logger.w('Token refresh failed: ${e.message}');
      _failAllPending(e);
      await _tokenStore.clearTokens();
      _forceLogout();
      return handler.next(e);
    } finally {
      _isRefreshing = false;
    }
  }

  void _forceLogout() {
    onForceLogout?.call();
  }

  void _resolveAllPending(String newAccessToken) {
    for (final entry in _pendingRetries) {
      entry.options.headers['Authorization'] = 'Bearer $newAccessToken';
      _dio.fetch<dynamic>(entry.options).then(
            entry.completer.complete,
            onError: entry.completer.completeError,
          );
    }
    _pendingRetries.clear();
  }

  void _failAllPending(DioException error) {
    for (final entry in _pendingRetries) {
      entry.completer.completeError(error);
    }
    _pendingRetries.clear();
  }
}

class _RetryEntry {
  _RetryEntry({required this.options, required this.completer});

  final RequestOptions options;
  final Completer<Response<dynamic>> completer;
}
