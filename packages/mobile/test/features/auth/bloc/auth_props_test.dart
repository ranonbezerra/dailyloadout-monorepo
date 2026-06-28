import 'package:app/core/auth/auth_models.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

final _user = User(
  publicId: 'user-001',
  email: 'test@example.com',
  displayName: 'TestUser',
  emailVerified: true,
  locale: 'en-US',
  timezone: 'America/New_York',
  createdAt: DateTime.utc(2025, 1, 15),
);

void main() {
  group('AuthEvent', () {
    test('AppStarted supports value equality', () {
      expect(const AppStarted(), const AppStarted());
      expect(const AppStarted().props, isEmpty);
    });

    test('LoginRequested supports value equality and props', () {
      const a = LoginRequested(email: 'a@b.com', password: 'pw');
      const b = LoginRequested(email: 'a@b.com', password: 'pw');
      expect(a, b);
      expect(a.props, ['a@b.com', 'pw']);
      expect(a, isNot(const LoginRequested(email: 'x@b.com', password: 'pw')));
    });

    test('RegisterRequested supports value equality and props', () {
      const a = RegisterRequested(
        email: 'a@b.com',
        password: 'pw',
        displayName: 'Neo',
      );
      const b = RegisterRequested(
        email: 'a@b.com',
        password: 'pw',
        displayName: 'Neo',
      );
      expect(a, b);
      expect(a.props, ['a@b.com', 'pw', 'Neo']);
    });

    test('LogoutRequested supports value equality', () {
      expect(const LogoutRequested(), const LogoutRequested());
      expect(const LogoutRequested().props, isEmpty);
    });
  });

  group('AuthState', () {
    test('AuthInitial supports value equality', () {
      expect(const AuthInitial(), const AuthInitial());
      expect(const AuthInitial().props, isEmpty);
    });

    test('AuthLoading supports value equality', () {
      expect(const AuthLoading(), const AuthLoading());
      expect(const AuthLoading().props, isEmpty);
    });

    test('Authenticated supports value equality and props', () {
      final a = Authenticated(user: _user);
      final b = Authenticated(user: _user);
      expect(a, b);
      expect(a.props, [_user]);
    });

    test('Unauthenticated supports value equality', () {
      expect(const Unauthenticated(), const Unauthenticated());
      expect(const Unauthenticated().props, isEmpty);
    });

    test('AuthError supports value equality and props', () {
      const a = AuthError(message: 'boom');
      const b = AuthError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
      expect(a, isNot(const AuthError(message: 'other')));
    });
  });
}
