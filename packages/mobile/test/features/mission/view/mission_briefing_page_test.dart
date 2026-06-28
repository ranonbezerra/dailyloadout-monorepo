import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:app/features/mission/view/mission_briefing_page.dart';
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

final _samplePreview = BriefingPreview(
  libraryEntry: _sampleLibraryEntry,
  briefingText: 'Welcome back to Hallownest!',
);

final _samplePreviewNoBriefing = BriefingPreview(
  libraryEntry: _sampleLibraryEntry,
);

final _sampleMission = Mission(
  publicId: 'mission-1',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
  briefingText: 'Continue your journey through the caverns.',
  startedAt: DateTime(2024, 6, 15, 10),
  createdAt: DateTime(2024, 6, 15, 10),
  updatedAt: DateTime(2024, 6, 15, 10),
);

final _sampleMissionNoBriefing = Mission(
  publicId: 'mission-2',
  libraryEntry: _sampleLibraryEntry,
  missionType: 'regular',
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

  Widget buildPreviewSubject() {
    return BlocProvider<MissionBloc>.value(
      value: missionBloc,
      child: const MaterialApp(
        home: MissionBriefingPage(libraryEntryPublicId: 'entry-1'),
      ),
    );
  }

  Widget buildViewSubject() {
    return BlocProvider<MissionBloc>.value(
      value: missionBloc,
      child: const MaterialApp(
        home: MissionBriefingPage(missionPublicId: 'mission-1'),
      ),
    );
  }

  group('MissionBriefingPage', () {
    testWidgets('shows AppBar with Mission Briefing title', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildPreviewSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Mission Briefing'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows CircularProgressIndicator when MissionLoading', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionLoading());

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('preview mode shows the mode-choice screen on init '
        '(does not fetch yet)', (tester) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('How should we prepare your briefing?'), findsOneWidget);
      expect(find.text('Quick briefing'), findsOneWidget);
      expect(find.text('Deep briefing (web)'), findsOneWidget);
    });

    testWidgets('view mode dispatches LoadActiveMission on init', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildViewSubject());

      verify(() => missionBloc.add(const LoadActiveMission())).called(1);
    });

    testWidgets('preview mode shows game title and briefing text '
        'when BriefingPreviewLoaded', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('Welcome back to Hallownest!'), findsOneWidget);
    });

    testWidgets('preview mode shows platform label', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('PC'), findsOneWidget);
    });

    testWidgets('preview briefing shows Got it and Update, no Cancel', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(
        find.widgetWithText(FilledButton, "Got it, let's go"),
        findsOneWidget,
      );
      expect(
        find.widgetWithText(TextButton, 'Update this briefing'),
        findsOneWidget,
      );
      expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsNothing);
    });

    testWidgets('preview briefing merges the fixers behind Update '
        '(no direct fix buttons)', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('I played without registering'), findsNothing);
      expect(find.text("That's not right"), findsNothing);
    });

    testWidgets('view mode shows briefing from ActiveMissionLoaded', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildViewSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(
        find.text('Continue your journey through the caverns.'),
        findsOneWidget,
      );
    });

    testWidgets('view mode shows Got it button (not Got it let us go)', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildViewSubject());

      expect(find.widgetWithText(FilledButton, 'Got it'), findsOneWidget);
      expect(find.text("Got it, let's go"), findsNothing);
    });

    testWidgets('view mode does NOT show I played without registering', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

      await tester.pumpWidget(buildViewSubject());

      expect(find.text('I played without registering'), findsNothing);
    });

    testWidgets('shows italic no briefing text when briefingText is null '
        '(preview mode)', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreviewNoBriefing));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.textContaining('No briefing available'), findsOneWidget);
    });

    testWidgets('shows italic no briefing text when briefingText is null '
        '(view mode)', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(ActiveMissionLoaded(mission: _sampleMissionNoBriefing));

      await tester.pumpWidget(buildViewSubject());

      expect(find.textContaining('No briefing available'), findsOneWidget);
    });

    testWidgets('Update → Correct my position opens the correction step', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this briefing'));
      await tester.pumpAndSettle();
      await tester.tap(
        find.widgetWithText(OutlinedButton, 'Correct my current position'),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(
        find.widgetWithText(FilledButton, 'Update & regenerate'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Tell us where you actually are'),
        findsOneWidget,
      );
    });

    testWidgets('Update → Log a session opens the retroactive step', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this briefing'));
      await tester.pumpAndSettle();
      await tester.tap(
        find.widgetWithText(OutlinedButton, "Log a session I didn't register"),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsOneWidget);
      expect(
        find.widgetWithText(FilledButton, 'Record session'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Tell us what happened in that unregistered'),
        findsOneWidget,
      );
    });

    testWidgets('Back from the correction step returns to the briefing', (
      tester,
    ) async {
      when(
        () => missionBloc.state,
      ).thenReturn(BriefingPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this briefing'));
      await tester.pumpAndSettle();
      await tester.tap(
        find.widgetWithText(OutlinedButton, 'Correct my current position'),
      );
      await tester.pumpAndSettle();

      // Back: correct → update, then update → briefing.
      await tester.tap(find.widgetWithText(TextButton, 'Back'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(TextButton, 'Back'));
      await tester.pumpAndSettle();

      expect(find.text('Welcome back to Hallownest!'), findsOneWidget);
      expect(find.text('Update & regenerate'), findsNothing);
    });

    testWidgets('shows SnackBar on MissionError via listener', (tester) async {
      whenListen(
        missionBloc,
        Stream<MissionState>.fromIterable([
          const MissionError(message: 'Something went wrong'),
        ]),
        initialState: BriefingPreviewLoaded(preview: _samplePreview),
      );

      await tester.pumpWidget(buildPreviewSubject());
      await tester.pumpAndSettle();

      // The error text appears in both the SnackBar (listener)
      // and the body (builder), so verify the SnackBar itself.
      expect(find.byType(SnackBar), findsOneWidget);
      expect(
        find.descendant(
          of: find.byType(SnackBar),
          matching: find.text('Something went wrong'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows error message and Go Back button when '
        'MissionError in builder', (tester) async {
      when(
        () => missionBloc.state,
      ).thenReturn(const MissionError(message: 'Failed to load briefing'));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('Failed to load briefing'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Go Back'), findsOneWidget);
    });

    testWidgets('view mode MissionInitial renders nothing (shrink)', (
      tester,
    ) async {
      when(() => missionBloc.state).thenReturn(const MissionInitial());

      await tester.pumpWidget(buildViewSubject());

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('Hollow Knight'), findsNothing);
      expect(find.text('Quick briefing'), findsNothing);
    });

    // ---------------------------------------------------------------
    // Deep briefing (mode choice + progress + cancel)
    // ---------------------------------------------------------------
    group('deep briefing', () {
      testWidgets('view mode does NOT show the mode-choice cards', (
        tester,
      ) async {
        when(
          () => missionBloc.state,
        ).thenReturn(ActiveMissionLoaded(mission: _sampleMission));

        await tester.pumpWidget(buildViewSubject());

        expect(find.text('Quick briefing'), findsNothing);
        expect(find.text('Deep briefing (web)'), findsNothing);
      });

      testWidgets('choosing Quick dispatches a quick PreviewBriefing', (
        tester,
      ) async {
        when(() => missionBloc.state).thenReturn(const MissionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Quick briefing'));
        await tester.pump();

        verify(
          () => missionBloc.add(
            const PreviewBriefing(
              libraryEntryPublicId: 'entry-1',
              // mode defaults to 'quick'
            ),
          ),
        ).called(1);
      });

      testWidgets('choosing Just play starts the mission with no briefing', (
        tester,
      ) async {
        when(() => missionBloc.state).thenReturn(const MissionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Just play'));
        await tester.pump();

        verify(
          () => missionBloc.add(
            const StartMission(
              libraryEntryPublicId: 'entry-1',
              skipBriefing: true,
            ),
          ),
        ).called(1);
      });

      testWidgets('choosing Deep dispatches a deep PreviewBriefing', (
        tester,
      ) async {
        when(() => missionBloc.state).thenReturn(const MissionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Deep briefing (web)'));
        await tester.pump();

        verify(
          () => missionBloc.add(
            const PreviewBriefing(
              libraryEntryPublicId: 'entry-1',
              mode: 'deep',
            ),
          ),
        ).called(1);
      });

      testWidgets('DeepBriefingLoading shows progress and a Cancel button', (
        tester,
      ) async {
        when(() => missionBloc.state).thenReturn(const DeepBriefingLoading());

        await tester.pumpWidget(buildPreviewSubject());

        expect(
          find.text('Researching the web for your briefing'),
          findsOneWidget,
        );
        expect(find.byType(CircularProgressIndicator), findsOneWidget);
        expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsOneWidget);
      });

      testWidgets('Cancel during deep dispatches CancelDeepBriefing', (
        tester,
      ) async {
        when(() => missionBloc.state).thenReturn(const DeepBriefingLoading());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
        await tester.pump();

        verify(
          () => missionBloc.add(
            const CancelDeepBriefing(libraryEntryPublicId: 'entry-1'),
          ),
        ).called(1);
      });
    });
  });
}
