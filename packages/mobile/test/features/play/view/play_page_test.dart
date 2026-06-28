import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:app/features/play/view/play_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockMissionBloc extends MockBloc<MissionEvent, MissionState>
    implements MissionBloc {}

final _now = DateTime.utc(2025, 6);

const _platform = Platform(
  id: 1,
  slug: 'ps5',
  label: 'PlayStation 5',
  family: 'playstation',
);

final _game = Game(
  publicId: 'game-1',
  slug: 'hollow-knight',
  title: 'Hollow Knight',
  metadataSource: 'igdb',
  createdAt: _now,
);

final _entry = LibraryEntry(
  publicId: 'entry-1',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _mission = Mission(
  publicId: 'mission-1',
  libraryEntry: _entry,
  missionType: 'regular',
  briefingText: 'Continue exploring Hallownest.',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
);

final _missionNoBriefing = Mission(
  publicId: 'mission-2',
  libraryEntry: _entry,
  missionType: 'regular',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  late MockMissionBloc missionBloc;

  setUp(() {
    missionBloc = MockMissionBloc();
  });

  tearDown(() {
    missionBloc.close();
  });

  /// Wrapper with a GoRouter so `context.go()` resolves in tests, and
  /// stub destinations for each door / mission action.
  Widget buildSubject({bool conciergeEnabled = false}) {
    final router = GoRouter(
      initialLocation: '/play',
      routes: [
        GoRoute(
          path: '/play',
          builder: (_, __) => PlayPage(conciergeEnabled: conciergeEnabled),
        ),
        GoRoute(
          path: '/play/loadout',
          builder: (_, __) => const Scaffold(body: Text('Loadout stub')),
        ),
        GoRoute(
          path: '/play/missions',
          builder: (_, __) => const Scaffold(body: Text('Missions stub')),
        ),
        GoRoute(
          path: '/play/concierge',
          builder: (_, __) => const Scaffold(body: Text('Concierge stub')),
        ),
        GoRoute(
          path: '/library',
          builder: (_, __) => const Scaffold(body: Text('Library stub')),
        ),
        GoRoute(
          path: '/missions/:id/briefing',
          builder: (_, __) => const Scaffold(body: Text('Briefing stub')),
        ),
        GoRoute(
          path: '/missions/:id/debrief',
          builder: (_, __) => const Scaffold(body: Text('Debrief stub')),
        ),
      ],
    );

    return BlocProvider<MissionBloc>.value(
      value: missionBloc,
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('PlayPage', () {
    testWidgets('dispatches LoadActiveMission on init', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => missionBloc.add(const LoadActiveMission())).called(1);
    });

    testWidgets('shows AppBar with Play title', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(of: find.byType(AppBar), matching: find.text('Play')),
        findsOneWidget,
      );
    });

    testWidgets('shows no-active-mission card when ActiveMissionLoaded '
        'with null mission', (tester) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('No mission running'), findsOneWidget);
      expect(
        find.text('Pick something below and start playing.'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.rocket_launch_outlined), findsOneWidget);
    });

    testWidgets('shows no-active-mission card for MissionInitial', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('No mission running'), findsOneWidget);
    });

    testWidgets('shows loading placeholder when MissionLoading', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('No mission running'), findsNothing);
    });

    testWidgets('shows error card and locks start doors on MissionError', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(const MissionError(message: 'Network down'));

      await tester.pumpWidget(buildSubject());

      // Genuine error is surfaced (not silently treated as "no mission").
      expect(find.text("Couldn't load your mission"), findsOneWidget);
      expect(find.text('Network down'), findsOneWidget);
      expect(find.text('No mission running'), findsNothing);

      // Start doors are locked because the active mission is unknown.
      expect(
        find.text('Could not check your active mission'),
        findsNWidgets(2),
      );
      expect(find.byIcon(Icons.lock_outline), findsNWidgets(2));

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Loadout stub'), findsNothing);
    });

    testWidgets('tapping Retry on the error card re-dispatches '
        'LoadActiveMission', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(const MissionError(message: 'Network down'));

      await tester.pumpWidget(buildSubject());
      clearInteractions(missionBloc);

      await tester.tap(find.text('Retry'));
      await tester.pump();

      verify(() => missionBloc.add(const LoadActiveMission())).called(1);
    });

    testWidgets('shows active mission card with title, platform and briefing', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _mission));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Active mission'), findsOneWidget);
      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('PlayStation 5'), findsOneWidget);
      expect(find.text('Continue exploring Hallownest.'), findsOneWidget);
    });

    testWidgets(
      'active mission card shows Briefing and End / Debrief buttons',
      (tester) async {
        when(
          () => missionBloc.state,
        ).thenReturn(ActiveMissionLoaded(mission: _mission));

        await tester.pumpWidget(buildSubject());

        // Resume was removed — it had no real destination.
        expect(find.text('Resume'), findsNothing);
        expect(find.text('Briefing'), findsOneWidget);
        expect(
          find.widgetWithText(OutlinedButton, 'End / Debrief'),
          findsOneWidget,
        );
      },
    );

    testWidgets('active mission card hides briefing when none present', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _missionNoBriefing));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Active mission'), findsOneWidget);
      expect(find.text('Continue exploring Hallownest.'), findsNothing);
    });

    testWidgets('tapping Briefing navigates to the mission briefing', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _mission));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text('Briefing'));
      await tester.pumpAndSettle();

      expect(find.text('Briefing stub'), findsOneWidget);
    });

    testWidgets('tapping End / Debrief navigates to the mission debrief', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _mission));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.widgetWithText(OutlinedButton, 'End / Debrief'));
      await tester.pumpAndSettle();

      expect(find.text('Debrief stub'), findsOneWidget);
    });

    testWidgets('start doors are disabled while a mission is active', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _mission));

      await tester.pumpWidget(buildSubject());

      // Hint replaces the subtitle on both start doors.
      expect(find.text('Finish your active mission first'), findsNWidgets(2));
      expect(find.byIcon(Icons.lock_outline), findsNWidgets(2));

      // Tapping the disabled door does not navigate.
      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Loadout stub'), findsNothing);
    });

    testWidgets('Ask door stays enabled while a mission is active', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _mission));

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      await tester.tap(find.text('Ask'));
      await tester.pumpAndSettle();

      expect(find.text('Concierge stub'), findsOneWidget);
    });

    testWidgets('start doors are enabled when there is no active mission', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Finish your active mission first'), findsNothing);
      expect(find.byIcon(Icons.lock_outline), findsNothing);

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Loadout stub'), findsOneWidget);
    });

    testWidgets("shows What's next section with the two default doors", (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text("What's next?"), findsOneWidget);
      expect(find.text("What's the move?"), findsOneWidget);
      expect(find.text("I'll choose"), findsOneWidget);
    });

    testWidgets('does NOT show concierge door when conciergeEnabled is false', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ask'), findsNothing);
      expect(find.byIcon(Icons.auto_awesome), findsNothing);
    });

    testWidgets('shows concierge door when conciergeEnabled is true', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      expect(find.text('Ask'), findsOneWidget);
      expect(find.text('Chat about what to play.'), findsOneWidget);
      expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
    });

    testWidgets("tapping What's the move? navigates to /play/loadout", (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();

      expect(find.text('Loadout stub'), findsOneWidget);
    });

    testWidgets("tapping I'll choose navigates to /library", (tester) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text("I'll choose"));
      await tester.pumpAndSettle();

      expect(find.text('Library stub'), findsOneWidget);
    });

    testWidgets('tapping Ask navigates to /play/concierge', (tester) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      await tester.tap(find.text('Ask'));
      await tester.pumpAndSettle();

      expect(find.text('Concierge stub'), findsOneWidget);
    });

    testWidgets('pull to refresh re-dispatches LoadActiveMission', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());
      // Init dispatch counts as one.
      clearInteractions(missionBloc);

      await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
      await tester.pumpAndSettle();

      verify(() => missionBloc.add(const LoadActiveMission())).called(1);
    });
  });
}
