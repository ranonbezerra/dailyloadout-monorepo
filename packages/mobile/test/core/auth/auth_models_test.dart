import 'package:app/core/auth/auth_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AuthTokens', () {
    test('fromJson parses valid JSON correctly', () {
      final json = <String, dynamic>{
        'access_token': 'abc123',
        'refresh_token': 'def456',
      };

      final tokens = AuthTokens.fromJson(json);

      expect(tokens.accessToken, equals('abc123'));
      expect(tokens.refreshToken, equals('def456'));
    });

    test('Equatable: equal instances are equal', () {
      const a = AuthTokens(accessToken: 'abc', refreshToken: 'def');
      const b = AuthTokens(accessToken: 'abc', refreshToken: 'def');

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      const a = AuthTokens(accessToken: 'abc', refreshToken: 'def');
      const b = AuthTokens(accessToken: 'xyz', refreshToken: 'def');

      expect(a, isNot(equals(b)));
    });

    test('Equatable: different refresh tokens are not equal', () {
      const a = AuthTokens(accessToken: 'abc', refreshToken: 'def');
      const b = AuthTokens(accessToken: 'abc', refreshToken: 'ghi');

      expect(a, isNot(equals(b)));
    });

    test('props contains accessToken and refreshToken', () {
      const tokens = AuthTokens(accessToken: 'a', refreshToken: 'b');

      expect(tokens.props, equals(['a', 'b']));
    });
  });

  group('User', () {
    test('fromJson parses full JSON with all fields including avatarUrl', () {
      final json = <String, dynamic>{
        'public_id': 'user-001',
        'email': 'test@example.com',
        'display_name': 'TestUser',
        'avatar_url': 'https://example.com/avatar.png',
        'email_verified': true,
        'locale': 'en-US',
        'timezone': 'America/New_York',
        'created_at': '2025-01-15T10:30:00Z',
      };

      final user = User.fromJson(json);

      expect(user.publicId, equals('user-001'));
      expect(user.email, equals('test@example.com'));
      expect(user.displayName, equals('TestUser'));
      expect(user.avatarUrl, equals('https://example.com/avatar.png'));
      expect(user.emailVerified, isTrue);
      expect(user.locale, equals('en-US'));
      expect(user.timezone, equals('America/New_York'));
      expect(user.createdAt, equals(DateTime.utc(2025, 1, 15, 10, 30)));
    });

    test('fromJson parses JSON with null avatarUrl', () {
      final json = <String, dynamic>{
        'public_id': 'user-002',
        'email': 'no-avatar@example.com',
        'display_name': 'NoAvatar',
        'avatar_url': null,
        'email_verified': false,
        'locale': 'pt-BR',
        'timezone': 'America/Sao_Paulo',
        'created_at': '2025-06-01T00:00:00Z',
      };

      final user = User.fromJson(json);

      expect(user.avatarUrl, isNull);
      expect(user.emailVerified, isFalse);
    });

    test('fromJson parses JSON with missing avatarUrl key', () {
      final json = <String, dynamic>{
        'public_id': 'user-003',
        'email': 'missing@example.com',
        'display_name': 'MissingAvatar',
        'email_verified': true,
        'locale': 'en-GB',
        'timezone': 'Europe/London',
        'created_at': '2025-03-10T12:00:00Z',
      };

      final user = User.fromJson(json);

      expect(user.avatarUrl, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final createdAt = DateTime.utc(2025);
      final a = User(
        publicId: 'u1',
        email: 'a@b.com',
        displayName: 'A',
        emailVerified: true,
        locale: 'en',
        timezone: 'UTC',
        createdAt: createdAt,
        avatarUrl: 'https://img.com/a.png',
      );
      final b = User(
        publicId: 'u1',
        email: 'a@b.com',
        displayName: 'A',
        emailVerified: true,
        locale: 'en',
        timezone: 'UTC',
        createdAt: createdAt,
        avatarUrl: 'https://img.com/a.png',
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final createdAt = DateTime.utc(2025);
      final a = User(
        publicId: 'u1',
        email: 'a@b.com',
        displayName: 'A',
        emailVerified: true,
        locale: 'en',
        timezone: 'UTC',
        createdAt: createdAt,
      );
      final b = User(
        publicId: 'u2',
        email: 'a@b.com',
        displayName: 'A',
        emailVerified: true,
        locale: 'en',
        timezone: 'UTC',
        createdAt: createdAt,
      );

      expect(a, isNot(equals(b)));
    });

    test('props contains all fields in correct order', () {
      final createdAt = DateTime.utc(2025);
      final user = User(
        publicId: 'u1',
        email: 'e@e.com',
        displayName: 'D',
        emailVerified: true,
        locale: 'en',
        timezone: 'UTC',
        createdAt: createdAt,
        avatarUrl: 'url',
      );

      expect(
        user.props,
        equals(['u1', 'e@e.com', 'D', 'url', true, 'en', 'UTC', createdAt]),
      );
    });
  });
}
