import 'package:app/core/auth/auth_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/login_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockAuthBloc extends MockBloc<AuthEvent, AuthState> implements AuthBloc {}

void main() {
  late MockAuthBloc authBloc;

  setUp(() {
    authBloc = MockAuthBloc();
    when(() => authBloc.state).thenReturn(const Unauthenticated());
  });

  tearDown(() {
    authBloc.close();
  });

  Widget buildSubject() {
    return BlocProvider<AuthBloc>.value(
      value: authBloc,
      child: const MaterialApp(home: LoginPage()),
    );
  }

  group('LoginPage', () {
    testWidgets('renders Slate title text', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.text('Slate'), findsOneWidget);
    });

    testWidgets('renders Sign in to your account subtitle', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.text('Sign in to your account'), findsOneWidget);
    });

    testWidgets('has Email and Password TextFormFields', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(TextFormField, 'Email'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);
    });

    testWidgets('has Login FilledButton', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(FilledButton, 'Login'), findsOneWidget);
    });

    testWidgets("has Don't have an account? Register TextButton", (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      expect(
        find.widgetWithText(TextButton, "Don't have an account? Register"),
        findsOneWidget,
      );
    });

    testWidgets('email validation - empty shows Please enter your email', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      // Tap Login without entering anything.
      await tester.tap(find.widgetWithText(FilledButton, 'Login'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter your email'), findsOneWidget);
    });

    testWidgets(
      'password validation - empty shows Please enter your password',
      (tester) async {
        await tester.pumpWidget(buildSubject());

        // Enter a valid email but leave password empty.
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Email'),
          'test@example.com',
        );

        await tester.tap(find.widgetWithText(FilledButton, 'Login'));
        await tester.pumpAndSettle();

        expect(find.text('Please enter your password'), findsOneWidget);
      },
    );

    testWidgets(
      'submit dispatches LoginRequested event with email and password',
      (tester) async {
        await tester.pumpWidget(buildSubject());

        await tester.enterText(
          find.widgetWithText(TextFormField, 'Email'),
          'test@example.com',
        );
        await tester.enterText(
          find.widgetWithText(TextFormField, 'Password'),
          'password123',
        );

        await tester.tap(find.widgetWithText(FilledButton, 'Login'));
        await tester.pumpAndSettle();

        verify(
          () => authBloc.add(
            const LoginRequested(
              email: 'test@example.com',
              password: 'password123', // pragma: allowlist secret
            ),
          ),
        ).called(1);
      },
    );

    testWidgets('shows CircularProgressIndicator when AuthLoading state', (
      tester,
    ) async {
      when(() => authBloc.state).thenReturn(const AuthLoading());

      await tester.pumpWidget(buildSubject());

      // The FilledButton should contain a CircularProgressIndicator.
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // The Login text should not be visible.
      expect(find.text('Login'), findsNothing);
    });

    testWidgets('shows SnackBar on AuthError state', (tester) async {
      // Start with Unauthenticated, then emit AuthError.
      whenListen(
        authBloc,
        Stream<AuthState>.fromIterable([
          const AuthError(message: 'Invalid credentials'),
        ]),
        initialState: const Unauthenticated(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Invalid credentials'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });
  });
}
