import 'package:app/core/auth/auth_token_store.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late MockFlutterSecureStorage mockStorage;
  late AuthTokenStore store;

  setUp(() {
    mockStorage = MockFlutterSecureStorage();
    store = AuthTokenStore(secureStorage: mockStorage);
  });

  group('AuthTokenStore', () {
    group('saveTokens', () {
      test(
        'stores access token in memory and refresh token in secure storage',
        () async {
          when(
            () => mockStorage.write(
              key: any(named: 'key'),
              value: any(named: 'value'),
            ),
          ).thenAnswer((_) async {});

          await store.saveTokens(
            accessToken: 'access-123',
            refreshToken: 'refresh-456',
          );

          // Access token should be retrievable from memory.
          expect(store.getAccessToken(), equals('access-123'));

          // Refresh token should have been written to secure storage.
          verify(
            () => mockStorage.write(key: 'refresh_token', value: 'refresh-456'),
          ).called(1);
        },
      );
    });

    group('getAccessToken', () {
      test('returns null initially before any save', () {
        expect(store.getAccessToken(), isNull);
      });

      test('returns value after saveTokens', () async {
        when(
          () => mockStorage.write(
            key: any(named: 'key'),
            value: any(named: 'value'),
          ),
        ).thenAnswer((_) async {});

        await store.saveTokens(
          accessToken: 'my-access',
          refreshToken: 'my-refresh',
        );

        expect(store.getAccessToken(), equals('my-access'));
      });
    });

    group('getRefreshToken', () {
      test('delegates to secure storage read', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => 'stored-refresh-token');

        final result = await store.getRefreshToken();

        expect(result, equals('stored-refresh-token'));
        verify(() => mockStorage.read(key: 'refresh_token')).called(1);
      });

      test('returns null when secure storage has no value', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => null);

        final result = await store.getRefreshToken();

        expect(result, isNull);
      });
    });

    group('hasTokens', () {
      test('returns false when no refresh token stored', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => null);

        final result = await store.hasTokens();

        expect(result, isFalse);
      });

      test('returns false when refresh token is empty string', () async {
        when(
          () => mockStorage.read(key: any(named: 'key')),
        ).thenAnswer((_) async => '');

        final result = await store.hasTokens();

        expect(result, isFalse);
      });

      test(
        'returns true when refresh token is present and non-empty',
        () async {
          when(
            () => mockStorage.read(key: any(named: 'key')),
          ).thenAnswer((_) async => 'valid-token');

          final result = await store.hasTokens();

          expect(result, isTrue);
        },
      );
    });

    group('clearTokens', () {
      test(
        'clears access token to null and deletes refresh from storage',
        () async {
          // First save tokens so there is something to clear.
          when(
            () => mockStorage.write(
              key: any(named: 'key'),
              value: any(named: 'value'),
            ),
          ).thenAnswer((_) async {});
          when(
            () => mockStorage.delete(key: any(named: 'key')),
          ).thenAnswer((_) async {});

          await store.saveTokens(
            accessToken: 'to-clear',
            refreshToken: 'to-clear-refresh',
          );

          // Verify token was stored.
          expect(store.getAccessToken(), equals('to-clear'));

          // Clear tokens.
          await store.clearTokens();

          // Access token should be null.
          expect(store.getAccessToken(), isNull);

          // Secure storage delete should have been called.
          verify(() => mockStorage.delete(key: 'refresh_token')).called(1);
        },
      );

      test(
        'clearTokens works even when no tokens were previously saved',
        () async {
          when(
            () => mockStorage.delete(key: any(named: 'key')),
          ).thenAnswer((_) async {});

          await store.clearTokens();

          expect(store.getAccessToken(), isNull);
          verify(() => mockStorage.delete(key: 'refresh_token')).called(1);
        },
      );
    });
  });
}
