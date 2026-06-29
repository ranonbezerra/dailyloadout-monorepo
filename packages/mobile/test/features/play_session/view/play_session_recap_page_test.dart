import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:app/features/play_session/view/play_session_recap_page.dart';
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

final _samplePreview = RecapPreview(
  libraryEntry: _sampleLibraryEntry,
  recapText: 'Welcome back to Hallownest!',
);

final _samplePreviewNoRecap = RecapPreview(libraryEntry: _sampleLibraryEntry);

final _samplePlaySession = PlaySession(
  publicId: 'playSession-1',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  recapText: 'Continue your journey through the caverns.',
  startedAt: DateTime(2024, 6, 15, 10),
  createdAt: DateTime(2024, 6, 15, 10),
  updatedAt: DateTime(2024, 6, 15, 10),
);

final _samplePlaySessionNoRecap = PlaySession(
  publicId: 'playSession-2',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  startedAt: DateTime(2024, 6, 15, 10),
  createdAt: DateTime(2024, 6, 15, 10),
  updatedAt: DateTime(2024, 6, 15, 10),
);

void main() {
  late MockPlaySessionBloc playSessionBloc;

  setUp(() {
    playSessionBloc = MockPlaySessionBloc();
  });

  tearDown(() {
    playSessionBloc.close();
  });

  Widget buildPreviewSubject() {
    return BlocProvider<PlaySessionBloc>.value(
      value: playSessionBloc,
      child: const MaterialApp(
        home: PlaySessionRecapPage(libraryEntryPublicId: 'entry-1'),
      ),
    );
  }

  Widget buildViewSubject() {
    return BlocProvider<PlaySessionBloc>.value(
      value: playSessionBloc,
      child: const MaterialApp(
        home: PlaySessionRecapPage(playSessionPublicId: 'playSession-1'),
      ),
    );
  }

  group('PlaySessionRecapPage', () {
    testWidgets('shows AppBar with Recap title', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildPreviewSubject());

      expect(
        find.descendant(of: find.byType(AppBar), matching: find.text('Recap')),
        findsOneWidget,
      );
    });

    testWidgets('shows CircularProgressIndicator when PlaySessionLoading', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionLoading());

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('preview mode shows the mode-choice screen on init '
        '(does not fetch yet)', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('How should we prepare your recap?'), findsOneWidget);
      expect(find.text('Quick recap'), findsOneWidget);
      expect(find.text('Deep recap (web)'), findsOneWidget);
    });

    testWidgets('view mode dispatches LoadActivePlaySession on init', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildViewSubject());

      verify(
        () => playSessionBloc.add(const LoadActivePlaySession()),
      ).called(1);
    });

    testWidgets('preview mode shows game title and recap text '
        'when RecapPreviewLoaded', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
      expect(find.text('Welcome back to Hallownest!'), findsOneWidget);
    });

    testWidgets('preview mode shows platform label', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('PC'), findsOneWidget);
    });

    testWidgets('preview recap shows Got it and Update, no Cancel', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(
        find.widgetWithText(FilledButton, "Got it, let's go"),
        findsOneWidget,
      );
      expect(
        find.widgetWithText(TextButton, 'Update this recap'),
        findsOneWidget,
      );
      expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsNothing);
    });

    testWidgets('preview recap merges the fixers behind Update '
        '(no direct fix buttons)', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('I played without registering'), findsNothing);
      expect(find.text("That's not right"), findsNothing);
    });

    testWidgets('view mode shows recap from ActivePlaySessionLoaded', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

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
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildViewSubject());

      expect(find.widgetWithText(FilledButton, 'Got it'), findsOneWidget);
      expect(find.text("Got it, let's go"), findsNothing);
    });

    testWidgets('view mode does NOT show I played without registering', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildViewSubject());

      expect(find.text('I played without registering'), findsNothing);
    });

    testWidgets('shows italic no recap text when recapText is null '
        '(preview mode)', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreviewNoRecap));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.textContaining('No recap available'), findsOneWidget);
    });

    testWidgets('shows italic no recap text when recapText is null '
        '(view mode)', (tester) async {
      when(() => playSessionBloc.state).thenReturn(
        ActivePlaySessionLoaded(playSession: _samplePlaySessionNoRecap),
      );

      await tester.pumpWidget(buildViewSubject());

      expect(find.textContaining('No recap available'), findsOneWidget);
    });

    testWidgets('Update → Correct my position opens the correction step', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this recap'));
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
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this recap'));
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

    testWidgets('Back from the correction step returns to the recap', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(RecapPreviewLoaded(preview: _samplePreview));

      await tester.pumpWidget(buildPreviewSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Update this recap'));
      await tester.pumpAndSettle();
      await tester.tap(
        find.widgetWithText(OutlinedButton, 'Correct my current position'),
      );
      await tester.pumpAndSettle();

      // Back: correct → update, then update → recap.
      await tester.tap(find.widgetWithText(TextButton, 'Back'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(TextButton, 'Back'));
      await tester.pumpAndSettle();

      expect(find.text('Welcome back to Hallownest!'), findsOneWidget);
      expect(find.text('Update & regenerate'), findsNothing);
    });

    testWidgets('shows SnackBar on PlaySessionError via listener', (
      tester,
    ) async {
      whenListen(
        playSessionBloc,
        Stream<PlaySessionState>.fromIterable([
          const PlaySessionError(message: 'Something went wrong'),
        ]),
        initialState: RecapPreviewLoaded(preview: _samplePreview),
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
        'PlaySessionError in builder', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const PlaySessionError(message: 'Failed to load recap'));

      await tester.pumpWidget(buildPreviewSubject());

      expect(find.text('Failed to load recap'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Go Back'), findsOneWidget);
    });

    testWidgets('view mode PlaySessionInitial renders nothing (shrink)', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildViewSubject());

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('Hollow Knight'), findsNothing);
      expect(find.text('Quick recap'), findsNothing);
    });

    // ---------------------------------------------------------------
    // Deep recap (mode choice + progress + cancel)
    // ---------------------------------------------------------------
    group('deep recap', () {
      testWidgets('view mode does NOT show the mode-choice cards', (
        tester,
      ) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

        await tester.pumpWidget(buildViewSubject());

        expect(find.text('Quick recap'), findsNothing);
        expect(find.text('Deep recap (web)'), findsNothing);
      });

      testWidgets('choosing Quick dispatches a quick PreviewRecap', (
        tester,
      ) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(const PlaySessionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Quick recap'));
        await tester.pump();

        verify(
          () => playSessionBloc.add(
            const PreviewRecap(
              libraryEntryPublicId: 'entry-1',
              // mode defaults to 'quick'
            ),
          ),
        ).called(1);
      });

      testWidgets('choosing Just play starts the playSession with no recap', (
        tester,
      ) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(const PlaySessionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Just play'));
        await tester.pump();

        verify(
          () => playSessionBloc.add(
            const StartPlaySession(
              libraryEntryPublicId: 'entry-1',
              skipRecap: true,
            ),
          ),
        ).called(1);
      });

      testWidgets('choosing Deep dispatches a deep PreviewRecap', (
        tester,
      ) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(const PlaySessionInitial());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.text('Deep recap (web)'));
        await tester.pump();

        verify(
          () => playSessionBloc.add(
            const PreviewRecap(libraryEntryPublicId: 'entry-1', mode: 'deep'),
          ),
        ).called(1);
      });

      testWidgets('DeepRecapLoading shows progress and a Cancel button', (
        tester,
      ) async {
        when(() => playSessionBloc.state).thenReturn(const DeepRecapLoading());

        await tester.pumpWidget(buildPreviewSubject());

        expect(find.text('Researching the web for your recap'), findsOneWidget);
        expect(find.byType(CircularProgressIndicator), findsOneWidget);
        expect(find.widgetWithText(OutlinedButton, 'Cancel'), findsOneWidget);
      });

      testWidgets('Cancel during deep dispatches CancelDeepRecap', (
        tester,
      ) async {
        when(() => playSessionBloc.state).thenReturn(const DeepRecapLoading());

        await tester.pumpWidget(buildPreviewSubject());
        await tester.tap(find.widgetWithText(OutlinedButton, 'Cancel'));
        await tester.pump();

        verify(
          () => playSessionBloc.add(
            const CancelDeepRecap(libraryEntryPublicId: 'entry-1'),
          ),
        ).called(1);
      });
    });
  });
}
