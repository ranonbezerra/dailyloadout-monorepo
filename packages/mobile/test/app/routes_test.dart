import 'package:app/app/routes.dart';
import 'package:app/core/auth/auth_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/login_page.dart';
import 'package:app/features/auth/view/splash_page.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library/view/library_list_page.dart';
import 'package:app/features/play/view/play_page.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:app/features/play_session/view/play_sessions_list_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockAuthBloc extends MockBloc<AuthEvent, AuthState> implements AuthBloc {}

class MockLibraryBloc extends MockBloc<LibraryEvent, LibraryState>
    implements LibraryBloc {}

class MockPlaySessionBloc extends MockBloc<PlaySessionEvent, PlaySessionState>
    implements PlaySessionBloc {}

void main() {
  late MockAuthBloc authBloc;
  late MockLibraryBloc libraryBloc;
  late MockPlaySessionBloc playSessionBloc;
  late MockLibraryRepository mockLibraryRepository;

  setUp(() {
    authBloc = MockAuthBloc();
    libraryBloc = MockLibraryBloc();
    playSessionBloc = MockPlaySessionBloc();
    mockLibraryRepository = MockLibraryRepository();
  });

  tearDown(() {
    authBloc.close();
    libraryBloc.close();
    playSessionBloc.close();
  });

  /// Creates a [MaterialApp.router] that provides the necessary BLoCs and
  /// uses the router produced by [createRouter].
  Widget buildRoutedApp(GoRouter router) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthBloc>.value(value: authBloc),
        BlocProvider<LibraryBloc>.value(value: libraryBloc),
        BlocProvider<PlaySessionBloc>.value(value: playSessionBloc),
      ],
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('createRouter', () {
    test('returns a GoRouter instance', () {
      when(() => authBloc.state).thenReturn(const AuthInitial());
      when(
        () => authBloc.stream,
      ).thenAnswer((_) => const Stream<AuthState>.empty());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      expect(router, isA<GoRouter>());
      router.dispose();
    });
  });

  group('redirect logic', () {
    testWidgets('AuthInitial stays on /splash', (tester) async {
      when(() => authBloc.state).thenReturn(const AuthInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pump();

      expect(find.byType(SplashPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('AuthLoading stays on /splash', (tester) async {
      when(() => authBloc.state).thenReturn(const AuthLoading());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pump();

      expect(find.byType(SplashPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Unauthenticated + not on auth page redirects to /login', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(const Unauthenticated());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Started on /splash but unauthenticated => redirected to /login.
      expect(find.byType(LoginPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Unauthenticated + on /login stays on /login', (tester) async {
      when(() => authBloc.state).thenReturn(const Unauthenticated());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Unauthenticated lands on /login.
      expect(find.byType(LoginPage), findsOneWidget);

      // Navigate to /login explicitly (should stay).
      router.go('/login');
      await tester.pumpAndSettle();

      expect(find.byType(LoginPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Authenticated + on /login redirects to /play', (tester) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Navigate to /login; authenticated user should be redirected
      // to /play.
      router.go('/login');
      await tester.pumpAndSettle();

      expect(find.byType(PlayPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Authenticated + on /splash redirects to /play', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Initial location is /splash, but authenticated => /play.
      expect(find.byType(PlayPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Authenticated + on /library stays on /library', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => libraryBloc.state).thenReturn(const LibraryInitial());
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Should have navigated to the Play hub by default.
      expect(find.byType(PlayPage), findsOneWidget);

      // Go to /library explicitly.
      router.go('/library');
      await tester.pumpAndSettle();

      expect(find.byType(LibraryListPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Route /history renders the playSession history', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      router.go('/history');
      await tester.pumpAndSettle();

      expect(find.byType(PlaySessionsListPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Legacy /play/play-sessions redirects to /history', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      router.go('/play/play-sessions');
      await tester.pumpAndSettle();

      expect(find.byType(PlaySessionsListPage), findsOneWidget);

      router.dispose();
    });

    testWidgets('Route / redirects to /play', (tester) async {
      when(() => authBloc.state).thenReturn(
        Authenticated(
          user: User(
            publicId: 'u1',
            email: 'a@b.com',
            displayName: 'Test',
            emailVerified: true,
            locale: 'en',
            timezone: 'UTC',
            createdAt: DateTime(2024),
          ),
        ),
      );
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      final router = createRouter(
        authBloc,
        libraryRepository: mockLibraryRepository,
      );

      await tester.pumpWidget(buildRoutedApp(router));
      await tester.pumpAndSettle();

      // Navigate to '/'.
      router.go('/');
      await tester.pumpAndSettle();

      // The '/' route has a redirect to '/play'.
      expect(find.byType(PlayPage), findsOneWidget);

      router.dispose();
    });
  });
}
