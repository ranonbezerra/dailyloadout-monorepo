import 'package:app/core/auth/auth_models.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

void main() {
  late MockAuthRepository mockAuthRepository;

  const testTokens = AuthTokens(
    accessToken: 'access-abc',
    refreshToken: 'refresh-xyz',
  );

  final testUser = User(
    publicId: 'user-001',
    email: 'test@example.com',
    displayName: 'TestUser',
    emailVerified: true,
    locale: 'en-US',
    timezone: 'America/New_York',
    createdAt: DateTime.utc(2025, 1, 15),
  );

  setUp(() {
    mockAuthRepository = MockAuthRepository();

    // Register fallback values for commonly used types.
    registerFallbackValue(testTokens);
  });

  AuthBloc buildBloc() => AuthBloc(authRepository: mockAuthRepository);

  group('AuthBloc', () {
    test('initial state is AuthInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const AuthInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // AppStarted
    // ---------------------------------------------------------------
    group('AppStarted', () {
      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Unauthenticated] when no tokens are stored',
        setUp: () {
          when(
            () => mockAuthRepository.hasTokens(),
          ).thenAnswer((_) async => false);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AppStarted()),
        expect: () => const [AuthLoading(), Unauthenticated()],
        verify: (_) {
          verify(() => mockAuthRepository.hasTokens()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Authenticated] when tokens exist, '
        'refresh succeeds, and getMe succeeds',
        setUp: () {
          when(
            () => mockAuthRepository.hasTokens(),
          ).thenAnswer((_) async => true);
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => 'stored-refresh');
          when(
            () =>
                mockAuthRepository.refreshToken(refreshToken: 'stored-refresh'),
          ).thenAnswer((_) async => testTokens);
          when(
            () => mockAuthRepository.saveTokens(any()),
          ).thenAnswer((_) async {});
          when(
            () => mockAuthRepository.getMe(),
          ).thenAnswer((_) async => testUser);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AppStarted()),
        expect: () => [const AuthLoading(), Authenticated(user: testUser)],
        verify: (_) {
          verify(() => mockAuthRepository.saveTokens(testTokens)).called(1);
          verify(() => mockAuthRepository.getMe()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Unauthenticated] when '
        'getStoredRefreshToken returns null',
        setUp: () {
          when(
            () => mockAuthRepository.hasTokens(),
          ).thenAnswer((_) async => true);
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => null);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AppStarted()),
        expect: () => const [AuthLoading(), Unauthenticated()],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Unauthenticated] and calls clearTokens '
        'when refreshToken throws',
        setUp: () {
          when(
            () => mockAuthRepository.hasTokens(),
          ).thenAnswer((_) async => true);
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => 'stored-refresh');
          when(
            () =>
                mockAuthRepository.refreshToken(refreshToken: 'stored-refresh'),
          ).thenThrow(Exception('refresh failed'));
          when(() => mockAuthRepository.clearTokens()).thenAnswer((_) async {});
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AppStarted()),
        expect: () => const [AuthLoading(), Unauthenticated()],
        verify: (_) {
          verify(() => mockAuthRepository.clearTokens()).called(1);
        },
      );
    });

    // ---------------------------------------------------------------
    // LoginRequested
    // ---------------------------------------------------------------
    group('LoginRequested', () {
      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Authenticated] on successful login',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: 'user@example.com',
              password: 'secret', // pragma: allowlist secret
            ),
          ).thenAnswer((_) async => testTokens);
          when(
            () => mockAuthRepository.saveTokens(any()),
          ).thenAnswer((_) async {});
          when(
            () => mockAuthRepository.getMe(),
          ).thenAnswer((_) async => testUser);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const LoginRequested(
            email: 'user@example.com',
            password: 'secret', // pragma: allowlist secret
          ),
        ),
        expect: () => [const AuthLoading(), Authenticated(user: testUser)],
        verify: (_) {
          verify(() => mockAuthRepository.saveTokens(testTokens)).called(1);
          verify(() => mockAuthRepository.getMe()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with detail message '
        'when DioException has response detail',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 401,
                data: <String, dynamic>{'detail': 'Invalid credentials'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const LoginRequested(
            email: 'bad@e.com',
            password: 'wrong', // pragma: allowlist secret
          ),
        ),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Invalid credentials'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with e.message '
        'when DioException has no detail',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'Connection refused',
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Connection refused'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with fallback message '
        'when DioException has null message and no detail',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with e.toString() '
        'on generic Exception',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(Exception('Something broke'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Exception: Something broke'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // RegisterRequested
    // ---------------------------------------------------------------
    group('RegisterRequested', () {
      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, Authenticated] on successful registration',
        setUp: () {
          when(
            () => mockAuthRepository.register(
              email: 'new@example.com',
              password: 'pass123', // pragma: allowlist secret
              displayName: 'NewUser',
            ),
          ).thenAnswer((_) async => testTokens);
          when(
            () => mockAuthRepository.saveTokens(any()),
          ).thenAnswer((_) async {});
          when(
            () => mockAuthRepository.getMe(),
          ).thenAnswer((_) async => testUser);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RegisterRequested(
            email: 'new@example.com',
            password: 'pass123', // pragma: allowlist secret
            displayName: 'NewUser',
          ),
        ),
        expect: () => [const AuthLoading(), Authenticated(user: testUser)],
        verify: (_) {
          verify(() => mockAuthRepository.saveTokens(testTokens)).called(1);
          verify(() => mockAuthRepository.getMe()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with detail '
        'when DioException has response detail',
        setUp: () {
          when(
            () => mockAuthRepository.register(
              email: any(named: 'email'),
              password: any(named: 'password'),
              displayName: any(named: 'displayName'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 409,
                data: <String, dynamic>{'detail': 'Email already registered'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RegisterRequested(
            email: 'dup@e.com',
            password: 'p',
            displayName: 'D',
          ),
        ),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Email already registered'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [AuthLoading, AuthError] with e.toString() '
        'on generic Exception',
        setUp: () {
          when(
            () => mockAuthRepository.register(
              email: any(named: 'email'),
              password: any(named: 'password'),
              displayName: any(named: 'displayName'),
            ),
          ).thenThrow(Exception('Network issue'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RegisterRequested(
            email: 'a@b.com',
            password: 'p',
            displayName: 'D',
          ),
        ),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Exception: Network issue'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LogoutRequested
    // ---------------------------------------------------------------
    group('LogoutRequested', () {
      blocTest<AuthBloc, AuthState>(
        'calls logout API and clearTokens, emits [Unauthenticated] '
        'when refresh token exists',
        setUp: () {
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => 'stored-refresh');
          when(
            () => mockAuthRepository.logout(refreshToken: 'stored-refresh'),
          ).thenAnswer((_) async {});
          when(() => mockAuthRepository.clearTokens()).thenAnswer((_) async {});
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LogoutRequested()),
        expect: () => const [Unauthenticated()],
        verify: (_) {
          verify(
            () => mockAuthRepository.logout(refreshToken: 'stored-refresh'),
          ).called(1);
          verify(() => mockAuthRepository.clearTokens()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'just clears tokens and emits [Unauthenticated] '
        'when no stored token',
        setUp: () {
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => null);
          when(() => mockAuthRepository.clearTokens()).thenAnswer((_) async {});
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LogoutRequested()),
        expect: () => const [Unauthenticated()],
        verify: (_) {
          verifyNever(
            () => mockAuthRepository.logout(
              refreshToken: any(named: 'refreshToken'),
            ),
          );
          verify(() => mockAuthRepository.clearTokens()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'still clears tokens and emits [Unauthenticated] '
        'when logout API throws',
        setUp: () {
          when(
            () => mockAuthRepository.getStoredRefreshToken(),
          ).thenAnswer((_) async => 'stored-refresh');
          when(
            () => mockAuthRepository.logout(refreshToken: 'stored-refresh'),
          ).thenThrow(Exception('server down'));
          when(() => mockAuthRepository.clearTokens()).thenAnswer((_) async {});
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LogoutRequested()),
        expect: () => const [Unauthenticated()],
        verify: (_) {
          verify(() => mockAuthRepository.clearTokens()).called(1);
        },
      );
    });

    // ---------------------------------------------------------------
    // RefreshUserRequested
    // ---------------------------------------------------------------
    group('RefreshUserRequested', () {
      final verifiedUser = User(
        publicId: 'user-001',
        email: 'test@example.com',
        displayName: 'TestUser',
        emailVerified: true,
        locale: 'en-US',
        timezone: 'America/New_York',
        createdAt: DateTime.utc(2025, 1, 15),
      );

      blocTest<AuthBloc, AuthState>(
        're-fetches the profile and emits Authenticated without AuthLoading',
        setUp: () {
          when(
            () => mockAuthRepository.getMe(),
          ).thenAnswer((_) async => verifiedUser);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RefreshUserRequested()),
        expect: () => [Authenticated(user: verifiedUser)],
        verify: (_) {
          verify(() => mockAuthRepository.getMe()).called(1);
        },
      );

      blocTest<AuthBloc, AuthState>(
        'emits nothing when getMe throws (session is preserved)',
        setUp: () {
          when(
            () => mockAuthRepository.getMe(),
          ).thenThrow(Exception('offline'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RefreshUserRequested()),
        expect: () => const <AuthState>[],
      );
    });

    // ---------------------------------------------------------------
    // ResendVerificationRequested
    // ---------------------------------------------------------------
    group('ResendVerificationRequested', () {
      final unverifiedUser = User(
        publicId: 'user-001',
        email: 'test@example.com',
        displayName: 'TestUser',
        emailVerified: false,
        locale: 'en-US',
        timezone: 'America/New_York',
        createdAt: DateTime.utc(2025, 1, 15),
      );

      blocTest<AuthBloc, AuthState>(
        'emits [VerificationEmailSent, Authenticated] on success',
        setUp: () {
          when(
            () => mockAuthRepository.resendVerification(),
          ).thenAnswer((_) async => 'Email sent.');
        },
        build: buildBloc,
        seed: () => Authenticated(user: unverifiedUser),
        act: (bloc) => bloc.add(const ResendVerificationRequested()),
        expect: () => [
          VerificationEmailSent(user: unverifiedUser, message: 'Email sent.'),
          Authenticated(user: unverifiedUser),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'uses a fallback message when the API returns an empty message',
        setUp: () {
          when(
            () => mockAuthRepository.resendVerification(),
          ).thenAnswer((_) async => '');
        },
        build: buildBloc,
        seed: () => Authenticated(user: unverifiedUser),
        act: (bloc) => bloc.add(const ResendVerificationRequested()),
        expect: () => [
          VerificationEmailSent(
            user: unverifiedUser,
            message: 'Verification email sent. Check your inbox.',
          ),
          Authenticated(user: unverifiedUser),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'emits [VerificationEmailFailed, Authenticated] on DioException',
        setUp: () {
          when(() => mockAuthRepository.resendVerification()).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 429,
                data: <String, dynamic>{'detail': 'Too many requests'},
              ),
            ),
          );
        },
        build: buildBloc,
        seed: () => Authenticated(user: unverifiedUser),
        act: (bloc) => bloc.add(const ResendVerificationRequested()),
        expect: () => [
          VerificationEmailFailed(
            user: unverifiedUser,
            message: 'Too many requests',
          ),
          Authenticated(user: unverifiedUser),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'does nothing when not in an authenticated state',
        build: buildBloc,
        act: (bloc) => bloc.add(const ResendVerificationRequested()),
        expect: () => const <AuthState>[],
        verify: (_) {
          verifyNever(() => mockAuthRepository.resendVerification());
        },
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage via DioException paths
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException error paths)', () {
      blocTest<AuthBloc, AuthState>(
        'returns detail string when response data is Map with detail',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{'detail': 'Validation failed'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'Validation failed'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'falls back to e.message when response data has no detail key',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'timeout',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'error': 'internal'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [AuthLoading(), AuthError(message: 'timeout')],
      );

      blocTest<AuthBloc, AuthState>(
        'falls back to e.message when response data is not a Map',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'bad response',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: 'plain string body',
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [AuthLoading(), AuthError(message: 'bad response')],
      );

      blocTest<AuthBloc, AuthState>(
        'falls back to e.message when detail is not a String',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'non-string detail fallback',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{
                  'detail': <String, dynamic>{'field': 'email'},
                },
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'non-string detail fallback'),
        ],
      );

      blocTest<AuthBloc, AuthState>(
        'returns fallback when response is null and message is null',
        setUp: () {
          when(
            () => mockAuthRepository.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const LoginRequested(email: 'a@b.com', password: 'p')),
        expect: () => const [
          AuthLoading(),
          AuthError(message: 'An unexpected error occurred.'),
        ],
      );
    });
  });
}
