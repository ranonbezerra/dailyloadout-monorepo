import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthTokenStore extends Mock implements AuthTokenStore {}

class MockHttpClientAdapter extends Mock implements HttpClientAdapter {}

ResponseBody _jsonBody(Map<String, dynamic> data, int status) {
  return ResponseBody.fromString(
    jsonEncode(data),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

void main() {
  late MockAuthTokenStore tokenStore;
  late MockHttpClientAdapter adapter;
  late ApiClient apiClient;

  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
    registerFallbackValue(Uint8List(0));
  });

  setUp(() {
    tokenStore = MockAuthTokenStore();
    adapter = MockHttpClientAdapter();
  });

  /// Builds an [ApiClient] with a real Dio whose transport layer is mocked.
  ApiClient buildClient({OnForceLogout? onForceLogout}) {
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8100'))
      ..httpClientAdapter = adapter;
    return ApiClient(
      tokenStore: tokenStore,
      dio: dio,
      onForceLogout: onForceLogout,
    );
  }

  test('exposes the configured Dio instance', () {
    apiClient = buildClient();
    expect(apiClient.dio, isA<Dio>());
  });

  test('uses a default Dio when none is provided', () {
    final client = ApiClient(tokenStore: tokenStore);
    expect(client.dio.options.baseUrl, 'http://localhost:8100');
    expect(client.dio.interceptors.whereType<Interceptor>(), isNotEmpty);
  });

  group('auth interceptor — request', () {
    test('adds Authorization header when an access token exists', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('access-123');
      RequestOptions? sent;
      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        sent = invocation.positionalArguments[0] as RequestOptions;
        return Future.value(_jsonBody(<String, dynamic>{'ok': true}, 200));
      });

      apiClient = buildClient();
      await apiClient.dio.get<dynamic>('/v1/ping');

      expect(sent!.headers['Authorization'], 'Bearer access-123');
    });

    test('omits Authorization header when no access token', () async {
      when(() => tokenStore.getAccessToken()).thenReturn(null);
      RequestOptions? sent;
      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        sent = invocation.positionalArguments[0] as RequestOptions;
        return Future.value(_jsonBody(<String, dynamic>{'ok': true}, 200));
      });

      apiClient = buildClient();
      await apiClient.dio.get<dynamic>('/v1/ping');

      expect(sent!.headers.containsKey('Authorization'), isFalse);
    });
  });

  group('auth interceptor — 401 refresh + retry', () {
    test('refreshes token and retries the original request', () async {
      var currentAccess = 'old-access';
      when(() => tokenStore.getAccessToken()).thenAnswer((_) => currentAccess);
      when(
        () => tokenStore.getRefreshToken(),
      ).thenAnswer((_) async => 'refresh-1');
      when(
        () => tokenStore.saveTokens(
          accessToken: any(named: 'accessToken'),
          refreshToken: any(named: 'refreshToken'),
        ),
      ).thenAnswer((invocation) async {
        currentAccess = invocation.namedArguments[#accessToken] as String;
      });

      final authorizations = <String?>[];
      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        final options = invocation.positionalArguments[0] as RequestOptions;
        // The refresh endpoint succeeds with a new token pair.
        if (options.path.contains('/auth/refresh')) {
          return Future.value(
            _jsonBody(<String, dynamic>{
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
            }, 200),
          );
        }
        authorizations.add(options.headers['Authorization'] as String?);
        // First protected call 401s, retry (with new token) succeeds.
        if (authorizations.length == 1) {
          return Future.value(
            _jsonBody(<String, dynamic>{'detail': 'unauthorized'}, 401),
          );
        }
        return Future.value(_jsonBody(<String, dynamic>{'ok': true}, 200));
      });

      apiClient = buildClient();
      final response = await apiClient.dio.get<dynamic>('/v1/protected');

      expect(response.statusCode, 200);
      expect(authorizations.first, 'Bearer old-access');
      expect(authorizations.last, 'Bearer new-access');
      verify(
        () => tokenStore.saveTokens(
          accessToken: 'new-access',
          refreshToken: 'new-refresh',
        ),
      ).called(1);
    });

    test('forces logout and surfaces error when no refresh token', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('old-access');
      when(() => tokenStore.getRefreshToken()).thenAnswer((_) async => null);
      var loggedOut = false;

      when(() => adapter.fetch(any(), any(), any())).thenAnswer(
        (_) async => _jsonBody(<String, dynamic>{'detail': 'nope'}, 401),
      );

      apiClient = buildClient(onForceLogout: () => loggedOut = true);

      await expectLater(
        apiClient.dio.get<dynamic>('/v1/protected'),
        throwsA(isA<DioException>()),
      );
      expect(loggedOut, isTrue);
    });

    test('clears tokens and logs out when refresh fails', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('old-access');
      when(
        () => tokenStore.getRefreshToken(),
      ).thenAnswer((_) async => 'refresh-1');
      when(() => tokenStore.clearTokens()).thenAnswer((_) async {});
      var loggedOut = false;

      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        final options = invocation.positionalArguments[0] as RequestOptions;
        if (options.path.contains('/auth/refresh')) {
          // Refresh itself fails with 401.
          return Future.value(
            _jsonBody(<String, dynamic>{'detail': 'expired'}, 401),
          );
        }
        return Future.value(
          _jsonBody(<String, dynamic>{'detail': 'unauthorized'}, 401),
        );
      });

      apiClient = buildClient(onForceLogout: () => loggedOut = true);

      await expectLater(
        apiClient.dio.get<dynamic>('/v1/protected'),
        throwsA(isA<DioException>()),
      );
      verify(() => tokenStore.clearTokens()).called(1);
      expect(loggedOut, isTrue);
    });

    test('does not refresh on 401 from the refresh endpoint itself', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('old-access');
      when(
        () => tokenStore.getRefreshToken(),
      ).thenAnswer((_) async => 'refresh-1');

      var refreshCalls = 0;
      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        final options = invocation.positionalArguments[0] as RequestOptions;
        if (options.path.contains('/auth/refresh')) refreshCalls++;
        return Future.value(
          _jsonBody(<String, dynamic>{'detail': 'expired'}, 401),
        );
      });

      apiClient = buildClient();

      await expectLater(
        apiClient.dio.post<dynamic>(
          '/v1/auth/refresh',
          data: <String, dynamic>{'refresh_token': 'refresh-1'},
        ),
        throwsA(isA<DioException>()),
      );
      // Called exactly once: the original request, never a nested refresh.
      expect(refreshCalls, 1);
    });

    test('passes through non-401 errors untouched', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('access');
      when(() => adapter.fetch(any(), any(), any())).thenAnswer(
        (_) async => _jsonBody(<String, dynamic>{'detail': 'boom'}, 500),
      );

      apiClient = buildClient();

      await expectLater(
        apiClient.dio.get<dynamic>('/v1/protected'),
        throwsA(
          isA<DioException>().having(
            (e) => e.response?.statusCode,
            'statusCode',
            500,
          ),
        ),
      );
      verifyNever(() => tokenStore.getRefreshToken());
    });

    test('queues concurrent 401s and retries them after refresh', () async {
      when(() => tokenStore.getAccessToken()).thenReturn('old-access');
      when(
        () => tokenStore.getRefreshToken(),
      ).thenAnswer((_) async => 'refresh-1');
      when(
        () => tokenStore.saveTokens(
          accessToken: any(named: 'accessToken'),
          refreshToken: any(named: 'refreshToken'),
        ),
      ).thenAnswer((_) async {});

      final seen = <String>{};
      when(() => adapter.fetch(any(), any(), any())).thenAnswer((invocation) {
        final options = invocation.positionalArguments[0] as RequestOptions;
        if (options.path.contains('/auth/refresh')) {
          // Slight delay so both protected calls hit the refreshing branch.
          return Future.delayed(
            const Duration(milliseconds: 20),
            () => _jsonBody(<String, dynamic>{
              'access_token': 'new-access',
              'refresh_token': 'new-refresh',
            }, 200),
          );
        }
        final auth = options.headers['Authorization'] as String?;
        if (auth == 'Bearer old-access' && seen.add(options.path)) {
          return Future.value(
            _jsonBody(<String, dynamic>{'detail': 'unauthorized'}, 401),
          );
        }
        return Future.value(
          _jsonBody(<String, dynamic>{'path': options.path}, 200),
        );
      });

      apiClient = buildClient();

      final results = await Future.wait([
        apiClient.dio.get<dynamic>('/v1/a'),
        apiClient.dio.get<dynamic>('/v1/b'),
      ]);

      expect(results.every((r) => r.statusCode == 200), isTrue);
    });
  });
}
