import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:app/features/mission/view/missions_list_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockMissionBloc extends MockBloc<MissionEvent, MissionState>
    implements MissionBloc {}

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

final _activeMission = MissionListItem(
  publicId: 'mission-1',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  startedAt: DateTime(2024, 6, 15, 10),
);

final _debriefedMission = MissionListItem(
  publicId: 'mission-2',
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
  missionType: 'regular',
  startedAt: DateTime(2024, 6, 10, 14),
  endedAt: DateTime(2024, 6, 10, 16, 30),
  endedVia: 'debrief',
);

final _pausedMission = MissionListItem(
  publicId: 'mission-3',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  startedAt: DateTime(2024, 6, 12, 9),
  endedAt: DateTime(2024, 6, 12, 9, 45),
  endedVia: 'paused_app',
);

final _autoClosedMission = MissionListItem(
  publicId: 'mission-4',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  startedAt: DateTime(2024, 6, 11, 20),
  endedAt: DateTime(2024, 6, 12, 2),
  endedVia: 'auto_clamp',
);

final _retroactiveMission = MissionListItem(
  publicId: 'mission-5',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'retroactive',
  startedAt: DateTime(2024, 6, 8, 18),
  endedAt: DateTime(2024, 6, 8, 20, 15),
  endedVia: 'retroactive',
);

final _endedMission = MissionListItem(
  publicId: 'mission-6',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  startedAt: DateTime(2024, 6, 5, 12),
  endedAt: DateTime(2024, 6, 5, 13),
  endedVia: 'unknown_reason',
);

void main() {
  late MockMissionBloc missionBloc;

  setUp(() {
    missionBloc = MockMissionBloc();
  });

  tearDown(() {
    missionBloc.close();
  });

  Widget buildSubject() {
    return BlocProvider<MissionBloc>.value(
      value: missionBloc,
      child: const MaterialApp(home: MissionsListPage()),
    );
  }

  group('MissionsListPage', () {
    testWidgets('dispatches LoadMissions on init', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => missionBloc.add(const LoadMissions())).called(1);
    });

    testWidgets('shows CircularProgressIndicator when MissionLoading', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows empty state when MissionListLoaded with empty list', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(const MissionListLoaded(missions: [], total: 0));

      await tester.pumpWidget(buildSubject());

      expect(find.text('No missions yet.'), findsOneWidget);
      expect(find.text('Start one from the Play tab.'), findsOneWidget);
      expect(find.byIcon(Icons.rocket_launch_outlined), findsOneWidget);
    });

    testWidgets('shows error message and Retry button when MissionError', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(const MissionError(message: 'Network error'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Network error'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
    });

    testWidgets('shows mission cards when MissionListLoaded with items', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(
        MissionListLoaded(
          missions: [_activeMission, _debriefedMission],
          total: 2,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('Elden Ring'), findsOneWidget);
    });

    testWidgets('active mission card is read-only (no action buttons)', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_activeMission], total: 1));

      await tester.pumpWidget(buildSubject());

      // History is read-only — active-mission actions live on the Play page.
      expect(find.text('View Briefing'), findsNothing);
      expect(find.text('End Mission'), findsNothing);
      expect(find.byType(OutlinedButton), findsNothing);
      expect(find.byType(FilledButton), findsNothing);
    });

    testWidgets('ended mission card does NOT show action buttons', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_debriefedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('View Briefing'), findsNothing);
      expect(find.text('End Mission'), findsNothing);
    });

    testWidgets('shows Active status badge for active mission', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_activeMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Active'), findsOneWidget);
    });

    testWidgets('shows Debriefed status badge for debriefed mission', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_debriefedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Debriefed'), findsOneWidget);
    });

    testWidgets('shows Paused status badge for paused mission', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_pausedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Paused'), findsOneWidget);
    });

    testWidgets('shows Auto-closed status badge for auto_clamp mission', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_autoClosedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Auto-closed'), findsOneWidget);
    });

    testWidgets('shows Retroactive status badge for retroactive mission', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(
        MissionListLoaded(missions: [_retroactiveMission], total: 1),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Retroactive'), findsOneWidget);
    });

    testWidgets('shows Ended status badge for unknown endedVia', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_endedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ended'), findsOneWidget);
    });

    testWidgets('shows Ongoing for active mission duration', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_activeMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ongoing'), findsOneWidget);
    });

    testWidgets('shows formatted duration for ended mission', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_debriefedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      // 2h 30m (from 14:00 to 16:30)
      expect(find.text('2h 30m'), findsOneWidget);
    });

    testWidgets('shows platform label on mission card', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_debriefedMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('PlayStation 5'), findsOneWidget);
    });

    testWidgets('shows formatted start date on mission card', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(MissionListLoaded(missions: [_activeMission], total: 1));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Jun 15, 2024'), findsOneWidget);
    });

    testWidgets('shows SizedBox.shrink for MissionInitial', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      // Should not show loading, error, or empty state.
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('No missions yet.'), findsNothing);
      expect(find.text('Retry'), findsNothing);
    });

    testWidgets('shows AppBar with Mission History title', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Mission History'),
        ),
        findsOneWidget,
      );
    });
  });
}
