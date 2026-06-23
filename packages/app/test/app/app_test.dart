import 'package:app/app/app.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockCaptureRepository extends Mock implements CaptureRepository {}

void main() {
  late MockAuthRepository mockAuthRepository;
  late MockLibraryRepository mockLibraryRepository;
  late MockCaptureRepository mockCaptureRepository;
  late AuthBloc authBloc;
  late LibraryBloc libraryBloc;
  late CaptureBloc captureBloc;

  setUp(() {
    mockAuthRepository = MockAuthRepository();
    mockLibraryRepository = MockLibraryRepository();
    mockCaptureRepository = MockCaptureRepository();

    // Stub the hasTokens call that AppStarted will trigger.
    when(() => mockAuthRepository.hasTokens()).thenAnswer((_) async => false);

    authBloc = AuthBloc(authRepository: mockAuthRepository);
    libraryBloc = LibraryBloc(libraryRepository: mockLibraryRepository);
    captureBloc = CaptureBloc(captureRepository: mockCaptureRepository);
  });

  tearDown(() {
    authBloc.close();
    libraryBloc.close();
    captureBloc.close();
  });

  Widget buildSubject() {
    return App(
      authBloc: authBloc,
      libraryBloc: libraryBloc,
      captureBloc: captureBloc,
      libraryRepository: mockLibraryRepository,
    );
  }

  group('App', () {
    testWidgets('mounts and renders MaterialApp', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(find.byType(App), findsOneWidget);
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('uses dark theme', (tester) async {
      await tester.pumpWidget(buildSubject());

      final materialApp = tester.widget<MaterialApp>(find.byType(MaterialApp));
      expect(materialApp.themeMode, ThemeMode.dark);
    });

    testWidgets(
      'shows splash with CircularProgressIndicator on initial state',
      (tester) async {
        await tester.pumpWidget(buildSubject());

        // On initial pump, the auth bloc has not resolved yet,
        // so the app should remain on the splash screen.
        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      },
    );

    testWidgets('provides all 3 BLoCs via MultiBlocProvider', (tester) async {
      await tester.pumpWidget(buildSubject());

      // Verify blocs are accessible from the widget tree. We grab the
      // element of a widget that sits below MultiBlocProvider.
      final BuildContext context = tester.element(find.byType(MaterialApp));

      // These will throw if the blocs are not provided.
      expect(context.read<AuthBloc>(), isA<AuthBloc>());
      expect(context.read<LibraryBloc>(), isA<LibraryBloc>());
      expect(context.read<CaptureBloc>(), isA<CaptureBloc>());
    });
  });
}
