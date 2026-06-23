import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:app/features/mission/view/mission_debrief_page.dart';
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

final _sampleMission = Mission(
  publicId: 'mission-1',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  briefingText: 'Explore the caverns below.',
  startedAt: DateTime(2024, 6, 15, 10),
  createdAt: DateTime(2024, 6, 15, 10),
  updatedAt: DateTime(2024, 6, 15, 10),
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
      child: const MaterialApp(
        home: MissionDebriefPage(missionPublicId: 'mission-1'),
      ),
    );
  }

  group('MissionDebriefPage', () {
    testWidgets('shows AppBar with Mission Debrief title', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Mission Debrief'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('dispatches LoadActiveMission on init', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => missionBloc.add(const LoadActiveMission())).called(1);
    });

    testWidgets('shows CircularProgressIndicator when MissionLoading', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows game title when ActiveMissionLoaded', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
    });

    testWidgets('shows What happened this session prompt', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(find.text('What happened this session?'), findsOneWidget);
    });

    testWidgets('shows descriptive subtitle text', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(
        find.textContaining('Describe what you did, where you are'),
        findsOneWidget,
      );
    });

    testWidgets('shows TextFormField for debrief input', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(find.byType(TextFormField), findsOneWidget);
    });

    testWidgets('shows Submit debrief and Skip debrief buttons', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(
        find.widgetWithText(FilledButton, 'Submit debrief'),
        findsOneWidget,
      );
      expect(find.widgetWithText(TextButton, 'Skip debrief'), findsOneWidget);
    });

    testWidgets('validation shows error when input is empty', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      // Tap Submit without entering text.
      await tester.tap(find.widgetWithText(FilledButton, 'Submit debrief'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter at least 3 characters'), findsOneWidget);
    });

    testWidgets('validation shows error when input is less than 3 chars', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      await tester.enterText(find.byType(TextFormField), 'ab');

      await tester.tap(find.widgetWithText(FilledButton, 'Submit debrief'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter at least 3 characters'), findsOneWidget);
    });

    testWidgets('dispatches SubmitDebrief when valid text is submitted', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.byType(TextFormField),
        'Beat the Soul Master boss',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Submit debrief'));
      await tester.pumpAndSettle();

      verify(
        () => missionBloc.add(
          const SubmitDebrief(
            publicId: 'mission-1',
            debriefText: 'Beat the Soul Master boss',
          ),
        ),
      ).called(1);
    });

    testWidgets('dispatches EndMission when Skip debrief is tapped', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Skip debrief'));
      await tester.pumpAndSettle();

      verify(
        () => missionBloc.add(const EndMission(publicId: 'mission-1')),
      ).called(1);
    });

    testWidgets('shows SnackBar on MissionError via listener', (tester) async {
      whenListen(
        missionBloc,
        Stream<MissionState>.fromIterable([
          const MissionError(message: 'Failed to submit debrief'),
        ]),
        initialState: ActiveMissionLoaded(mission: _sampleMission),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Failed to submit debrief'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('does not show game title when no active mission', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const ActiveMissionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Hollow Knight'), findsNothing);
      // But still shows the debrief form.
      expect(find.text('What happened this session?'), findsOneWidget);
    });

    testWidgets('shows hint text in TextFormField', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildSubject());

      expect(find.textContaining('Beat the first boss'), findsOneWidget);
    });
  });
}
