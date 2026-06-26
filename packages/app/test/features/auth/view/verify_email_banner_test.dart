import 'package:app/core/auth/auth_models.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/verify_email_banner.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthBloc extends MockBloc<AuthEvent, AuthState> implements AuthBloc {}

User _user({required bool emailVerified}) => User(
  publicId: 'user-001',
  email: 'test@example.com',
  displayName: 'TestUser',
  emailVerified: emailVerified,
  locale: 'en-US',
  timezone: 'UTC',
  createdAt: DateTime.utc(2025, 1, 15),
);

void main() {
  late MockAuthBloc authBloc;

  setUp(() {
    authBloc = MockAuthBloc();
  });

  tearDown(() => authBloc.close());

  Widget buildSubject() {
    return BlocProvider<AuthBloc>.value(
      value: authBloc,
      child: const MaterialApp(home: Scaffold(body: VerifyEmailBanner())),
    );
  }

  group('VerifyEmailBanner', () {
    testWidgets('renders the verify prompt when the user is unverified', (
      tester,
    ) async {
      when(
        () => authBloc.state,
      ).thenReturn(Authenticated(user: _user(emailVerified: false)));

      await tester.pumpWidget(buildSubject());

      expect(find.text(VerifyEmailStrings.title), findsOneWidget);
      expect(find.text(VerifyEmailStrings.resend), findsOneWidget);
      expect(find.text(VerifyEmailStrings.refresh), findsOneWidget);
    });

    testWidgets('renders nothing when the user is verified', (tester) async {
      when(
        () => authBloc.state,
      ).thenReturn(Authenticated(user: _user(emailVerified: true)));

      await tester.pumpWidget(buildSubject());

      expect(find.text(VerifyEmailStrings.title), findsNothing);
      expect(find.byType(SizedBox), findsOneWidget);
    });

    testWidgets('renders nothing when unauthenticated', (tester) async {
      when(() => authBloc.state).thenReturn(const Unauthenticated());

      await tester.pumpWidget(buildSubject());

      expect(find.text(VerifyEmailStrings.title), findsNothing);
    });

    testWidgets('dispatches ResendVerificationRequested on Resend tap', (
      tester,
    ) async {
      when(
        () => authBloc.state,
      ).thenReturn(Authenticated(user: _user(emailVerified: false)));

      await tester.pumpWidget(buildSubject());
      await tester.tap(find.text(VerifyEmailStrings.resend));
      await tester.pump();

      verify(() => authBloc.add(const ResendVerificationRequested())).called(1);
    });

    testWidgets('dispatches RefreshUserRequested on Refresh tap', (
      tester,
    ) async {
      when(
        () => authBloc.state,
      ).thenReturn(Authenticated(user: _user(emailVerified: false)));

      await tester.pumpWidget(buildSubject());
      await tester.tap(find.text(VerifyEmailStrings.refresh));
      await tester.pump();

      verify(() => authBloc.add(const RefreshUserRequested())).called(1);
    });

    testWidgets('shows a snackbar when a verification email is sent', (
      tester,
    ) async {
      final unverified = _user(emailVerified: false);
      whenListen(
        authBloc,
        Stream<AuthState>.fromIterable([
          VerificationEmailSent(user: unverified, message: 'Email sent.'),
          Authenticated(user: unverified),
        ]),
        initialState: Authenticated(user: unverified),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Email sent.'), findsOneWidget);
    });

    testWidgets('shows a snackbar when resend fails', (tester) async {
      final unverified = _user(emailVerified: false);
      whenListen(
        authBloc,
        Stream<AuthState>.fromIterable([
          VerificationEmailFailed(user: unverified, message: 'Too many.'),
          Authenticated(user: unverified),
        ]),
        initialState: Authenticated(user: unverified),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Too many.'), findsOneWidget);
    });

    testWidgets('shows a confirmation snackbar once the email is verified', (
      tester,
    ) async {
      whenListen(
        authBloc,
        Stream<AuthState>.fromIterable([
          Authenticated(user: _user(emailVerified: true)),
        ]),
        initialState: Authenticated(user: _user(emailVerified: false)),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text(VerifyEmailStrings.nowVerified), findsOneWidget);
    });
  });
}
