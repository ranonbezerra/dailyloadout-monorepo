import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:app/features/play_session/view/play_sessions_list_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockPlaySessionBloc extends MockBloc<PlaySessionEvent, PlaySessionState>
    implements PlaySessionBloc {}

final _sampleLibraryEntry = LibraryEntry(
  publicId: 'entry-1',
  game: Game(
    publicId: 'game-1',
    slug: 'hollow-knight',
    title: 'Hollow Knight',
    metadataSource: 'igdb',
    createdAt: DateTime(2024),
  ),
  platform: const Platform(id: 1, slug: 'pc', label: 'PC', family: 'pc'),
  status: 'playing',
  createdAt: DateTime(2024),
  updatedAt: DateTime(2024),
);

final _activePlaySession = PlaySessionListItem(
  publicId: 'playSession-1',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 15, 10),
);

final _wrappedUpPlaySession = PlaySessionListItem(
  publicId: 'playSession-2',
  libraryEntry: LibraryEntry(
    publicId: 'entry-2',
    game: Game(
      publicId: 'game-2',
      slug: 'elden-ring',
      title: 'Elden Ring',
      metadataSource: 'igdb',
      createdAt: DateTime(2024),
    ),
    platform: const Platform(
      id: 2,
      slug: 'ps5',
      label: 'PlayStation 5',
      family: 'playstation',
    ),
    status: 'playing',
    createdAt: DateTime(2024),
    updatedAt: DateTime(2024),
  ),
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 10, 14),
  endedAt: DateTime(2024, 6, 10, 16, 30),
  endedVia: 'wrapUp',
);

final _pausedPlaySession = PlaySessionListItem(
  publicId: 'playSession-3',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 12, 9),
  endedAt: DateTime(2024, 6, 12, 9, 45),
  endedVia: 'paused_app',
);

final _autoClosedPlaySession = PlaySessionListItem(
  publicId: 'playSession-4',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 11, 20),
  endedAt: DateTime(2024, 6, 12, 2),
  endedVia: 'auto_clamp',
);

final _retroactivePlaySession = PlaySessionListItem(
  publicId: 'playSession-5',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'retroactive',
  startedAt: DateTime(2024, 6, 8, 18),
  endedAt: DateTime(2024, 6, 8, 20, 15),
  endedVia: 'retroactive',
);

final _endedPlaySession = PlaySessionListItem(
  publicId: 'playSession-6',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 5, 12),
  endedAt: DateTime(2024, 6, 5, 13),
  endedVia: 'unknown_reason',
);

void main() {
  late MockPlaySessionBloc playSessionBloc;

  setUp(() {
    playSessionBloc = MockPlaySessionBloc();
  });

  tearDown(() {
    playSessionBloc.close();
  });

  Widget buildSubject() {
    return BlocProvider<PlaySessionBloc>.value(
      value: playSessionBloc,
      child: const MaterialApp(home: PlaySessionsListPage()),
    );
  }

  group('PlaySessionsListPage', () {
    testWidgets('dispatches LoadPlaySessions on init', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => playSessionBloc.add(const LoadPlaySessions())).called(1);
    });

    testWidgets('shows CircularProgressIndicator when PlaySessionLoading', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets(
      'shows empty state when PlaySessionListLoaded with empty list',
      (tester) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(const PlaySessionListLoaded(playSessions: [], total: 0));

        await tester.pumpWidget(buildSubject());

        expect(find.text('No sessions yet.'), findsOneWidget);
        expect(find.text('Start one from the Play tab.'), findsOneWidget);
        expect(find.byIcon(Icons.rocket_launch_outlined), findsOneWidget);
      },
    );

    testWidgets('shows error message and Retry button when PlaySessionError', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const PlaySessionError(message: 'Network error'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Network error'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
    });

    testWidgets(
      'shows playSession cards when PlaySessionListLoaded with items',
      (tester) async {
        when(() => playSessionBloc.state).thenReturn(
          PlaySessionListLoaded(
            playSessions: [_activePlaySession, _wrappedUpPlaySession],
            total: 2,
          ),
        );

        await tester.pumpWidget(buildSubject());

        expect(find.text('Hollow Knight'), findsOneWidget);
        expect(find.text('Elden Ring'), findsOneWidget);
      },
    );

    testWidgets('active playSession card is read-only (no action buttons)', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_activePlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      // History is read-only — active-session actions live on the Play page.
      expect(find.text('View Recap'), findsNothing);
      expect(find.text('End PlaySession'), findsNothing);
      expect(find.byType(OutlinedButton), findsNothing);
      expect(find.byType(FilledButton), findsNothing);
    });

    testWidgets('ended playSession card does NOT show action buttons', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_wrappedUpPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('View Recap'), findsNothing);
      expect(find.text('End PlaySession'), findsNothing);
    });

    testWidgets('shows Active status badge for active playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_activePlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Active'), findsOneWidget);
    });

    testWidgets('shows Wrapped status badge for wrapped-up playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_wrappedUpPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Wrapped'), findsOneWidget);
    });

    testWidgets('shows Paused status badge for paused playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_pausedPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Paused'), findsOneWidget);
    });

    testWidgets('shows Auto-closed status badge for auto_clamp playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_autoClosedPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Auto-closed'), findsOneWidget);
    });

    testWidgets('shows Retroactive status badge for retroactive playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(
          playSessions: [_retroactivePlaySession],
          total: 1,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Retroactive'), findsOneWidget);
    });

    testWidgets('shows Ended status badge for unknown endedVia', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_endedPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ended'), findsOneWidget);
    });

    testWidgets('shows Ongoing for active playSession duration', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_activePlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ongoing'), findsOneWidget);
    });

    testWidgets('shows formatted duration for ended playSession', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_wrappedUpPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      // 2h 30m (from 14:00 to 16:30)
      expect(find.text('2h 30m'), findsOneWidget);
    });

    testWidgets('shows platform label on playSession card', (tester) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_wrappedUpPlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('PlayStation 5'), findsOneWidget);
    });

    testWidgets('shows formatted start date on playSession card', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(
        PlaySessionListLoaded(playSessions: [_activePlaySession], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Jun 15, 2024'), findsOneWidget);
    });

    testWidgets('shows SizedBox.shrink for PlaySessionInitial', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      // Should not show loading, error, or empty state.
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('No sessions yet.'), findsNothing);
      expect(find.text('Retry'), findsNothing);
    });

    testWidgets('shows AppBar with Session history title', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Session history'),
        ),
        findsOneWidget,
      );
    });
  });
}
