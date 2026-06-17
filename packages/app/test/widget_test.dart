import 'package:app/app/app.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

void main() {
  late MockAuthRepository mockAuthRepository;
  late AuthBloc authBloc;

  setUp(() {
    mockAuthRepository = MockAuthRepository();

    // Stub the hasTokens call that AppStarted will trigger.
    when(() => mockAuthRepository.hasTokens())
        .thenAnswer((_) async => false);

    authBloc = AuthBloc(authRepository: mockAuthRepository);
  });

  tearDown(() {
    authBloc.close();
  });

  testWidgets('App widget mounts and renders MaterialApp',
      (tester) async {
    await tester.pumpWidget(App(authBloc: authBloc));

    // The App widget should be mounted successfully.
    expect(find.byType(App), findsOneWidget);
    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('App shows splash with loading indicator on startup',
      (tester) async {
    await tester.pumpWidget(App(authBloc: authBloc));

    // The splash screen should show a progress indicator.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  test('AuthBloc emits Unauthenticated when no tokens stored', () async {
    authBloc.add(const AppStarted());

    await expectLater(
      authBloc.stream,
      emitsInOrder(<Matcher>[
        isA<AuthLoading>(),
        isA<Unauthenticated>(),
      ]),
    );
  });
}
