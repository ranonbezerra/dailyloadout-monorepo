import 'package:app/app/app.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:app/core/config/feature_flags.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/pick/pick_repository.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAuthRepository extends Mock implements AuthRepository {}

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockCaptureRepository extends Mock implements CaptureRepository {}

class MockPlaySessionRepository extends Mock implements PlaySessionRepository {}

class MockPickRepository extends Mock implements PickRepository {}

class MockAnalyticsRepository extends Mock implements AnalyticsRepository {}

class MockConciergeRepository extends Mock implements ConciergeRepository {}

void main() {
  late MockAuthRepository mockAuthRepository;
  late MockLibraryRepository mockLibraryRepository;
  late MockCaptureRepository mockCaptureRepository;
  late MockPlaySessionRepository mockPlaySessionRepository;
  late MockPickRepository mockPickRepository;
  late MockAnalyticsRepository mockAnalyticsRepository;
  late MockConciergeRepository mockConciergeRepository;
  late AuthBloc authBloc;
  late LibraryBloc libraryBloc;
  late CaptureBloc captureBloc;
  late LibraryImportBloc libraryImportBloc;
  late PlaySessionBloc playSessionBloc;
  late PickBloc pickBloc;
  late AnalyticsBloc analyticsBloc;
  late ConciergeBloc conciergeBloc;

  setUp(() {
    mockAuthRepository = MockAuthRepository();
    mockLibraryRepository = MockLibraryRepository();
    mockCaptureRepository = MockCaptureRepository();
    mockPlaySessionRepository = MockPlaySessionRepository();
    mockPickRepository = MockPickRepository();
    mockAnalyticsRepository = MockAnalyticsRepository();
    mockConciergeRepository = MockConciergeRepository();

    // Stub the hasTokens call that AppStarted will trigger.
    when(() => mockAuthRepository.hasTokens()).thenAnswer((_) async => false);

    authBloc = AuthBloc(authRepository: mockAuthRepository);
    libraryBloc = LibraryBloc(libraryRepository: mockLibraryRepository);
    captureBloc = CaptureBloc(captureRepository: mockCaptureRepository);
    libraryImportBloc = LibraryImportBloc(
      captureRepository: mockCaptureRepository,
    );
    playSessionBloc = PlaySessionBloc(
      playSessionRepository: mockPlaySessionRepository,
    );
    pickBloc = PickBloc(
      pickRepository: mockPickRepository,
      playSessionRepository: mockPlaySessionRepository,
    );
    analyticsBloc = AnalyticsBloc(analyticsRepository: mockAnalyticsRepository);
    conciergeBloc = ConciergeBloc(conciergeRepository: mockConciergeRepository);
  });

  tearDown(() {
    authBloc.close();
    libraryBloc.close();
    captureBloc.close();
    libraryImportBloc.close();
    playSessionBloc.close();
    pickBloc.close();
    analyticsBloc.close();
    conciergeBloc.close();
  });

  Widget buildSubject() {
    return App(
      authBloc: authBloc,
      libraryBloc: libraryBloc,
      captureBloc: captureBloc,
      libraryImportBloc: libraryImportBloc,
      playSessionBloc: playSessionBloc,
      pickBloc: pickBloc,
      analyticsBloc: analyticsBloc,
      conciergeBloc: conciergeBloc,
      libraryRepository: mockLibraryRepository,
      featureFlags: const FeatureFlags(),
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
