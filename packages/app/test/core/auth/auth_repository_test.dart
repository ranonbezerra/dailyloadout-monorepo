import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_models.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

class MockAuthTokenStore extends Mock implements AuthTokenStore {}

Map<String, dynamic> _tokensJson() => <String, dynamic>{
  'access_token': 'access-abc',
  'refresh_token': 'refresh-def',
};

Map<String, dynamic> _userJson() => <String, dynamic>{
  'public_id': 'user-001',
  'email': 'test@example.com',
  'display_name': 'TestUser',
  'avatar_url': null,
  'email_verified': true,
  'locale': 'en-US',
  'timezone': 'UTC',
  'created_at': '2025-01-15T10:30:00Z',
};

Response<T> _response<T>(String path, T data) => Response<T>(
  requestOptions: RequestOptions(path: path),
  data: data,
);

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late MockAuthTokenStore tokenStore;
  late AuthRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    tokenStore = MockAuthTokenStore();
    when(() => apiClient.dio).thenReturn(dio);
    repository = AuthRepository(apiClient: apiClient, tokenStore: tokenStore);
  });

  group('register', () {
    test('posts credentials and parses AuthTokens', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/auth/register', _tokensJson()));

      final tokens = await repository.register(
        email: 'test@example.com',
        password: 'pw',
        displayName: 'TestUser',
      );

      expect(tokens, isA<AuthTokens>());
      expect(tokens.accessToken, 'access-abc');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/auth/register');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['email'], 'test@example.com');
      expect(body['password'], 'pw');
      expect(body['display_name'], 'TestUser');
    });

    test('rethrows DioException', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/v1/auth/register')),
      );

      expect(
        () => repository.register(email: 'e', password: 'p', displayName: 'd'),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('login', () {
    test('posts credentials and parses AuthTokens', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/auth/login', _tokensJson()));

      final tokens = await repository.login(
        email: 'test@example.com',
        password: 'pw',
      );

      expect(tokens.refreshToken, 'refresh-def');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/auth/login');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['email'], 'test@example.com');
      expect(body['password'], 'pw');
    });
  });

  group('refreshToken', () {
    test('posts refresh token and parses AuthTokens', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/auth/refresh', _tokensJson()));

      final tokens = await repository.refreshToken(refreshToken: 'old-token');

      expect(tokens.accessToken, 'access-abc');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/auth/refresh');
      expect((captured[1] as Map)['refresh_token'], 'old-token');
    });
  });

  group('logout', () {
    test('posts refresh token to logout', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/auth/logout', <String, dynamic>{}),
      );

      await repository.logout(refreshToken: 'rt');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/auth/logout');
      expect((captured[1] as Map)['refresh_token'], 'rt');
    });
  });

  group('getMe', () {
    test('gets profile and parses User', () async {
      when(
        () => dio.get<Map<String, dynamic>>(any()),
      ).thenAnswer((_) async => _response('/v1/auth/me', _userJson()));

      final user = await repository.getMe();

      expect(user, isA<User>());
      expect(user.email, 'test@example.com');
      verify(() => dio.get<Map<String, dynamic>>('/v1/auth/me')).called(1);
    });
  });

  group('token store delegation', () {
    test('saveTokens forwards to store', () async {
      when(
        () => tokenStore.saveTokens(
          accessToken: any(named: 'accessToken'),
          refreshToken: any(named: 'refreshToken'),
        ),
      ).thenAnswer((_) async {});

      await repository.saveTokens(
        const AuthTokens(accessToken: 'a', refreshToken: 'r'),
      );

      verify(
        () => tokenStore.saveTokens(accessToken: 'a', refreshToken: 'r'),
      ).called(1);
    });

    test('clearTokens forwards to store', () async {
      when(() => tokenStore.clearTokens()).thenAnswer((_) async {});

      await repository.clearTokens();

      verify(() => tokenStore.clearTokens()).called(1);
    });

    test('getStoredRefreshToken forwards to store', () async {
      when(
        () => tokenStore.getRefreshToken(),
      ).thenAnswer((_) async => 'stored-rt');

      final token = await repository.getStoredRefreshToken();

      expect(token, 'stored-rt');
      verify(() => tokenStore.getRefreshToken()).called(1);
    });

    test('hasTokens forwards to store', () async {
      when(() => tokenStore.hasTokens()).thenAnswer((_) async => true);

      final result = await repository.hasTokens();

      expect(result, isTrue);
      verify(() => tokenStore.hasTokens()).called(1);
    });
  });
}
