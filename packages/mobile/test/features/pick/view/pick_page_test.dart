import 'package:app/core/library/library_models.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:app/features/pick/view/pick_page.dart';
import 'package:app/features/pick/view/pick_result_card.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockPickBloc extends MockBloc<PickEvent, PickState> implements PickBloc {}

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

final _pick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  createdAt: _now,
  updatedAt: _now,
);

final _pick2 = Pick(
  publicId: 'pick-002',
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

final _acceptedPick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'accepted',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedPick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'rejected',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedPick2 = Pick(
  publicId: 'pick-002',
  libraryEntry: _pick2.libraryEntry,
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
      const CreatePick(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      ),
    );
    registerFallbackValue(const AcceptPick(publicId: 'x'));
    registerFallbackValue(const RejectPick(publicId: 'x'));
    registerFallbackValue(
      const GeneratePickRecap(publicId: 'x', libraryEntryPublicId: 'y'),
    );
  });

  late MockPickBloc mockPickBloc;

  setUp(() {
    mockPickBloc = MockPickBloc();
  });

  tearDown(() {
    mockPickBloc.close();
  });

  /// Simple wrapper: MaterialApp with the PickPage
  /// as home, no GoRouter needed.
  Widget buildSubject() {
    return BlocProvider<PickBloc>.value(
      value: mockPickBloc,
      child: const MaterialApp(home: PickPage()),
    );
  }

  /// Wrapper using GoRouter so that `context.go()`
  /// works in tests that trigger navigation.
  Widget buildRoutedSubject() {
    final router = GoRouter(
      initialLocation: '/pick',
      routes: [
        GoRoute(path: '/pick', builder: (_, __) => const PickPage()),
        GoRoute(
          path: '/play',
          builder: (_, __) => const Scaffold(body: Text('Play stub')),
        ),
      ],
    );

    return BlocProvider<PickBloc>.value(
      value: mockPickBloc,
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('PickPage', () {
    testWidgets('shows AppBar with Daily Pick title', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Daily Pick'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows mood choice chips '
        'when PickInitial', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Mood'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Chill'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Focused'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Energetic'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Adventurous'), findsOneWidget);
    });

    testWidgets('shows time Slider when PickInitial', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Available time'), findsOneWidget);
      expect(find.byType(Slider), findsOneWidget);
      // Default time is 60 min = "1h"
      expect(find.text('1h'), findsAtLeast(1));
    });

    testWidgets('shows mental energy choice chips '
        'when PickInitial', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Mental energy'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Low'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'Medium'), findsOneWidget);
      expect(find.widgetWithText(ChoiceChip, 'High'), findsOneWidget);
    });

    testWidgets('shows context TextFormField', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(TextFormField), findsOneWidget);
      expect(find.text('Context (optional)'), findsOneWidget);
    });

    testWidgets('shows "Show multiple suggestions" switch', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(SwitchListTile), findsOneWidget);
      expect(find.text('Show multiple suggestions (up to 3)'), findsOneWidget);
    });

    testWidgets('shows "Roll the dice" button '
        'when PickInitial', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Roll the dice'), findsOneWidget);
      expect(find.byIcon(Icons.casino), findsOneWidget);
    });

    testWidgets('shows loading view with spinner '
        'when PickLoading', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Scanning your library...'), findsOneWidget);
    });

    testWidgets('hides questionnaire when PickLoading', (tester) async {
      when(() => mockPickBloc.state).thenReturn(const PickLoading());

      await tester.pumpWidget(buildSubject());

      // Questionnaire is replaced by loading view.
      expect(find.text('Roll the dice'), findsNothing);
      expect(find.text('Scanning your library...'), findsOneWidget);
    });

    testWidgets('shows error text via builder '
        'on PickError from stream', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          const PickError(message: 'Something went wrong'),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Something went wrong'), findsOneWidget);
    });

    testWidgets('shows error text when PickError '
        'in builder', (tester) async {
      when(
        () => mockPickBloc.state,
      ).thenReturn(const PickError(message: 'Failed to generate pick'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Failed to generate pick'), findsOneWidget);
    });

    testWidgets('shows result cards when '
        'PickResultsLoaded', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick, _pick2]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(PickResultCard), findsNWidgets(2));
      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('Elden Ring'), findsOneWidget);
      expect(find.text('Your picks'), findsOneWidget);
    });

    testWidgets('shows questionnaire again when all '
        'results are actioned', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick, _pick2]),
          PickRejected(pick: _rejectedPick),
          PickRejected(pick: _rejectedPick2),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // All actioned => questionnaire is shown
      expect(find.text('Mood'), findsOneWidget);
      expect(find.text('Roll the dice'), findsOneWidget);
      expect(find.byType(PickResultCard), findsNothing);
    });

    testWidgets('shows "Roll again" button '
        'in results view', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Roll again'), findsOneWidget);
    });

    testWidgets('"Roll again" clears results '
        'and shows questionnaire', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Roll again'));
      await tester.pump();

      expect(find.text('Mood'), findsOneWidget);
      expect(find.byType(PickResultCard), findsNothing);
    });

    testWidgets('shows SnackBar with "Session started!" '
        'on PickAccepted via listener', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
          PickAccepted(pick: _acceptedPick),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      // First pump processes the stream events.
      await tester.pump();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(
        find.descendant(
          of: find.byType(SnackBar),
          matching: find.text('Session started!'),
        ),
        findsOneWidget,
      );

      // Advance past the 800ms navigation delay
      // so the timer fires and completes cleanly.
      await tester.pump(const Duration(seconds: 1));
      // Let the route transition settle.
      await tester.pumpAndSettle();
    });

    testWidgets('"Roll the dice" dispatches CreatePick with defaults', (
      tester,
    ) async {
      when(() => mockPickBloc.state).thenReturn(const PickInitial());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text('Roll the dice'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(
          const CreatePick(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
      ).called(1);
    });

    testWidgets('Accept on a result card dispatches AcceptPick', (
      tester,
    ) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pump();

      await tester.tap(find.text('Just play'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(const AcceptPick(publicId: 'pick-001')),
      ).called(1);
    });

    testWidgets('Reject on a result card dispatches RejectPick', (
      tester,
    ) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Reject'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(const RejectPick(publicId: 'pick-001')),
      ).called(1);
    });

    testWidgets('Quick recap dispatches GeneratePickRecap (quick)', (
      tester,
    ) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Quick recap'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(
          // mode defaults to 'quick'
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
      ).called(1);
    });

    testWidgets('Deep recap dispatches GeneratePickRecap (deep)', (
      tester,
    ) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Deep recap'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
            mode: 'deep',
          ),
        ),
      ).called(1);
    });

    testWidgets('renders recap and "Start with recap" '
        'after PickRecapReady', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
          const PickRecapReady(
            publicId: 'pick-001',
            recapText: 'Push toward the next checkpoint.',
          ),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.text('Push toward the next checkpoint.'), findsOneWidget);
      expect(find.text('Start with recap'), findsOneWidget);
    });

    testWidgets('"Start with recap" dispatches AcceptPick '
        'with the recap text', (tester) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
          const PickRecapReady(
            publicId: 'pick-001',
            recapText: 'Push toward the next checkpoint.',
          ),
        ]),
        initialState: const PickInitial(),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pump();

      await tester.tap(find.text('Start with recap'));
      await tester.pump();

      verify(
        () => mockPickBloc.add(
          const AcceptPick(
            publicId: 'pick-001',
            recapText: 'Push toward the next checkpoint.',
          ),
        ),
      ).called(1);
    });

    testWidgets('navigates to /play after a playSession is accepted', (
      tester,
    ) async {
      whenListen(
        mockPickBloc,
        Stream<PickState>.fromIterable([
          PickResultsLoaded(results: [_pick]),
          PickAccepted(pick: _acceptedPick),
        ]),
        initialState: const PickInitial(),
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
