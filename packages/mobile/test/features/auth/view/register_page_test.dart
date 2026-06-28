import 'package:app/core/auth/auth_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/register_page.dart';
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
      child: const MaterialApp(home: RegisterPage()),
    );
  }

  group('RegisterPage', () {
    testWidgets('renders DailyLoadout and Create your account', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.text('DailyLoadout'), findsOneWidget);
      expect(find.text('Create your account'), findsOneWidget);
    });

    testWidgets('has Display Name, Email, Password fields', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(
        find.widgetWithText(TextFormField, 'Display Name'),
        findsOneWidget,
      );
      expect(find.widgetWithText(TextFormField, 'Email'), findsOneWidget);
      expect(find.widgetWithText(TextFormField, 'Password'), findsOneWidget);
    });

    testWidgets(
      'display name validation - empty shows Please enter a display name',
      (tester) async {
        await tester.pumpWidget(buildSubject());

        // Tap Register without entering anything.
        await tester.tap(find.widgetWithText(FilledButton, 'Register'));
        await tester.pumpAndSettle();

        expect(find.text('Please enter a display name'), findsOneWidget);
      },
    );

    testWidgets('email validation - empty shows Please enter your email', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      // Fill display name but leave email empty.
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Display Name'),
        'John',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Register'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter your email'), findsOneWidget);
    });

    testWidgets('password validation - empty shows Please enter a password', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Display Name'),
        'John',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Email'),
        'john@example.com',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Register'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter a password'), findsOneWidget);
    });

    testWidgets('password validation - < 8 chars shows minimum length error', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Display Name'),
        'John',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Email'),
        'john@example.com',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'short',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Register'));
      await tester.pumpAndSettle();

      expect(
        find.text('Password must be at least 8 characters'),
        findsOneWidget,
      );
    });

    testWidgets('submit dispatches RegisterRequested event', (tester) async {
      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Display Name'),
        'John Doe',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Email'),
        'john@example.com',
      );
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Password'),
        'password123',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Register'));
      await tester.pumpAndSettle();

      verify(
        () => authBloc.add(
          const RegisterRequested(
            email: 'john@example.com',
            password: 'password123', // pragma: allowlist secret
            displayName: 'John Doe',
          ),
        ),
      ).called(1);
    });

    testWidgets('shows loading on AuthLoading', (tester) async {
      when(() => authBloc.state).thenReturn(const AuthLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Register'), findsNothing);
    });

    testWidgets('shows SnackBar on AuthError', (tester) async {
      whenListen(
        authBloc,
        Stream<AuthState>.fromIterable([
          const AuthError(message: 'Email already taken'),
        ]),
        initialState: const Unauthenticated(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Email already taken'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });
  });
}
