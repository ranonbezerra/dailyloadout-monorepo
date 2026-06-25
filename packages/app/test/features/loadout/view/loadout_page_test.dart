import 'package:app/core/library/library_models.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:app/features/loadout/view/loadout_page.dart';
import 'package:app/features/loadout/view/loadout_result_card.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockLoadoutBloc extends MockBloc<LoadoutEvent, LoadoutState>
    implements LoadoutBloc {}

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'Sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'hollow-knight',
  title: 'Hollow Knight',
  metadataSource: 'igdb',
  createdAt: _now,
  genres: const ['Metroidvania', 'Action'],
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _loadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  createdAt: _now,
  updatedAt: _now,
);

final _loadout2 = Loadout(
  publicId: 'loadout-002',
  libraryEntry: LibraryEntry(
    publicId: 'lib-002',
    game: Game(
      publicId: 'game-002',
      slug: 'elden-ring',
      title: 'Elden Ring',
      metadataSource: 'igdb',
      createdAt: _now,
    ),
    platform: const Platform(id: 2, slug: 'pc', label: 'PC', family: 'PC'),
    status: 'backlog',
    createdAt: _now,
    updatedAt: _now,
  ),
  mood: 'focused',
  availableMinutes: 120,
  mentalEnergy: 'high',
  reasoning: 'Challenge yourself tonight',
  createdAt: _now,
  updatedAt: _now,
);

final _acceptedLoadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'accepted',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedLoadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'rejected',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedLoadout2 = Loadout(
  publicId: 'loadout-002',
  libraryEntry: _loadout2.libraryEntry,
  mood: 'focused',
  availableMinutes: 120,
  mentalEnergy: 'high',
  reasoning: 'Challenge yourself tonight',
  action: 'rejected',
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  setUpAll(() {
    registerFallbackValue(
      const CreateLoadout(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      ),
    );
    registerFallbackValue(const AcceptLoadout(publicId: 'x'));
    registerFallbackValue(const RejectLoadout(publicId: 'x'));
    registerFallbackValue(
      const GenerateLoadoutBriefing(publicId: 'x', libraryEntryPublicId: 'y'),
    );
  });

  late MockLoadoutBloc mockLoadoutBloc;

  setUp(() {
    mockLoadoutBloc = MockLoadoutBloc();
  });

  tearDown(() {
    mockLoadoutBloc.close();
  });

  /// Simple wrapper: MaterialApp with the LoadoutPage
  /// as home, no GoRouter needed.
  Widget buildSubject() {
    return BlocProvider<LoadoutBloc>.value(
      value: mockLoadoutBloc,
      child: const MaterialApp(home: LoadoutPage()),
    );
  }

  /// Wrapper using GoRouter so that `context.go()`
  /// works in tests that trigger navigation.
  Widget buildRoutedSubject() {
    final router = GoRouter(
      initialLocation: '/loadout',
      routes: [
        GoRoute(path: '/loadout', builder: (_, __) => const LoadoutPage()),
        GoRoute(
          path: '/play',
          builder: (_, __) => const Scaffold(body: Text('Play stub')),
        ),
      ],
    );

    return BlocProvider<LoadoutBloc>.value(
      value: mockLoadoutBloc,
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('LoadoutPage', () {
    testWidgets('shows AppBar with Daily Loadout title', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Daily Loadout'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows mood choice chips '
        'when LoadoutInitial', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Mood'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Chill'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Focused'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Energetic'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Adventurous'), findsOneWidget);
    });

    testWidgets('shows time Slider when LoadoutInitial', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Available time'), findsOneWidget);
      expect(find.byType(Slider), findsOneWidget);
      // Default time is 60 min = "1h"
      expect(find.text('1h'), findsAtLeast(1));
    });

    testWidgets('shows mental energy choice chips '
        'when LoadoutInitial', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Mental energy'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Low'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Medium'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'High'), findsOneWidget);
    });

    testWidgets('shows context TextFormField', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Context (optional)'), findsOneWidget);
    });

    testWidgets('shows "Show multiple suggestions" switch', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(SwitchListTile), findsOneWidget);
      expect(find.text('Show multiple suggestions (up to 3)'), findsOneWidget);
    });

    testWidgets('shows "Roll the dice" button '
        'when LoadoutInitial', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Roll the dice'), findsOneWidget);
      expect(find.byIcon(Icons.casino), findsOneWidget);
    });

    testWidgets('shows loading view with spinner '
        'when LoadoutLoading', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Scanning your library...'), findsOneWidget);
    });

    testWidgets('hides questionnaire when LoadoutLoading', (tester) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutLoading());

      await tester.pumpWidget(buildSubject());

      // Questionnaire is replaced by loading view.
      expect(find.text('Roll the dice'), findsNothing);
      expect(find.text('Scanning your library...'), findsOneWidget);
    });

    testWidgets('shows error text via builder '
        'on LoadoutError from stream', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          const LoadoutError(message: 'Something went wrong'),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Something went wrong'), findsOneWidget);
    });

    testWidgets('shows error text when LoadoutError '
        'in builder', (tester) async {
      when(
        () => mockLoadoutBloc.state,
      ).thenReturn(const LoadoutError(message: 'Failed to generate loadout'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Failed to generate loadout'), findsOneWidget);
    });

    testWidgets('shows result cards when '
        'LoadoutResultsLoaded', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout, _loadout2]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(LoadoutResultCard), findsNWidgets(2));
      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('Elden Ring'), findsOneWidget);
      expect(find.text('Your picks'), findsOneWidget);
    });

    testWidgets('shows questionnaire again when all '
        'results are actioned', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout, _loadout2]),
          LoadoutRejected(loadout: _rejectedLoadout),
          LoadoutRejected(loadout: _rejectedLoadout2),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // All actioned => questionnaire is shown
      expect(find.text('Mood'), findsOneWidget);
      expect(find.text('Roll the dice'), findsOneWidget);
      expect(find.byType(LoadoutResultCard), findsNothing);
    });

    testWidgets('shows "Roll again" button '
        'in results view', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Roll again'), findsOneWidget);
    });

    testWidgets('"Roll again" clears results '
        'and shows questionnaire', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Roll again'));
      await tester.pump();

      expect(find.text('Mood'), findsOneWidget);
      expect(find.byType(LoadoutResultCard), findsNothing);
    });

    testWidgets('shows SnackBar with "Mission started!" '
        'on LoadoutAccepted via listener', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
          LoadoutAccepted(loadout: _acceptedLoadout),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      // First pump processes the stream events.
      await tester.pump();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(
        find.descendant(
          of: find.byType(SnackBar),
          matching: find.text('Mission started!'),
        ),
        findsOneWidget,
      );

      // Advance past the 800ms navigation delay
      // so the timer fires and completes cleanly.
      await tester.pump(const Duration(seconds: 1));
      // Let the route transition settle.
      await tester.pumpAndSettle();
    });

    testWidgets('"Roll the dice" dispatches CreateLoadout with defaults', (
      tester,
    ) async {
      when(() => mockLoadoutBloc.state).thenReturn(const LoadoutInitial());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text('Roll the dice'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(
          const CreateLoadout(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
      ).called(1);
    });

    testWidgets('Accept on a result card dispatches AcceptLoadout', (
      tester,
    ) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pump();

      await tester.tap(find.text('Just play'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(const AcceptLoadout(publicId: 'loadout-001')),
      ).called(1);
    });

    testWidgets('Reject on a result card dispatches RejectLoadout', (
      tester,
    ) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Reject'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(const RejectLoadout(publicId: 'loadout-001')),
      ).called(1);
    });

    testWidgets('Quick briefing dispatches GenerateLoadoutBriefing (quick)', (
      tester,
    ) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Quick briefing'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(
          // mode defaults to 'quick'
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
      ).called(1);
    });

    testWidgets('Deep briefing dispatches GenerateLoadoutBriefing (deep)', (
      tester,
    ) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Deep briefing'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
            mode: 'deep',
          ),
        ),
      ).called(1);
    });

    testWidgets('renders briefing and "Start with briefing" '
        'after LoadoutBriefingReady', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
          const LoadoutBriefingReady(
            publicId: 'loadout-001',
            briefingText: 'Push toward the next checkpoint.',
          ),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Push toward the next checkpoint.'), findsOneWidget);
      expect(find.text('Start with briefing'), findsOneWidget);
    });

    testWidgets('"Start with briefing" dispatches AcceptLoadout '
        'with the briefing text', (tester) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
          const LoadoutBriefingReady(
            publicId: 'loadout-001',
            briefingText: 'Push toward the next checkpoint.',
          ),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pump();

      await tester.tap(find.text('Start with briefing'));
      await tester.pump();

      verify(
        () => mockLoadoutBloc.add(
          const AcceptLoadout(
            publicId: 'loadout-001',
            briefingText: 'Push toward the next checkpoint.',
          ),
        ),
      ).called(1);
    });

    testWidgets('navigates to /play after a mission is accepted', (
      tester,
    ) async {
      whenListen(
        mockLoadoutBloc,
        Stream<LoadoutState>.fromIterable([
          LoadoutResultsLoaded(results: [_loadout]),
          LoadoutAccepted(loadout: _acceptedLoadout),
        ]),
        initialState: const LoadoutInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pump();

      // Advance past the 800ms navigation delay.
      await tester.pump(const Duration(seconds: 1));
      await tester.pumpAndSettle();

      expect(find.text('Play stub'), findsOneWidget);
    });
  });
}
