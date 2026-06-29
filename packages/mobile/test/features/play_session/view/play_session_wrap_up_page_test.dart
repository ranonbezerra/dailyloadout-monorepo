import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:app/features/play_session/view/play_session_wrap_up_page.dart';
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

final _samplePlaySession = PlaySession(
  publicId: 'playSession-1',
  libraryEntry: _sampleLibraryEntry,
  playSessionType: 'regular',
  recapText: 'Explore the caverns below.',
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

  Widget buildSubject() {
    return BlocProvider<PlaySessionBloc>.value(
      value: playSessionBloc,
      child: const MaterialApp(
        home: PlaySessionWrapUpPage(playSessionPublicId: 'playSession-1'),
      ),
    );
  }

  group('PlaySessionWrapUpPage', () {
    testWidgets('shows AppBar with Wrap up title', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Wrap up'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('dispatches LoadActivePlaySession on init', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      verify(
        () => playSessionBloc.add(const LoadActivePlaySession()),
      ).called(1);
    });

    testWidgets('shows CircularProgressIndicator when PlaySessionLoading', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows game title when ActivePlaySessionLoaded', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Hollow Knight'), findsOneWidget);
    });

    testWidgets('shows What happened this session prompt', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(find.text('What happened this session?'), findsOneWidget);
    });

    testWidgets('shows descriptive subtitle text', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(
        find.textContaining('Describe what you did, where you are'),
        findsOneWidget,
      );
    });

    testWidgets('shows TextFormField for wrapUp input', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(find.byType(TextFormField), findsOneWidget);
    });

    testWidgets('shows Save wrap-up and Skip wrap-up buttons', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(FilledButton, 'Save wrap-up'), findsOneWidget);
      expect(find.widgetWithText(TextButton, 'Skip wrap-up'), findsOneWidget);
    });

    testWidgets('validation shows error when input is empty', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      // Tap Submit without entering text.
      await tester.tap(find.widgetWithText(FilledButton, 'Save wrap-up'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter at least 3 characters'), findsOneWidget);
    });

    testWidgets('validation shows error when input is less than 3 chars', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      await tester.enterText(find.byType(TextFormField), 'ab');

      await tester.tap(find.widgetWithText(FilledButton, 'Save wrap-up'));
      await tester.pumpAndSettle();

      expect(find.text('Please enter at least 3 characters'), findsOneWidget);
    });

    testWidgets('dispatches SubmitWrapUp when valid text is submitted', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.byType(TextFormField),
        'Beat the Soul Master boss',
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Save wrap-up'));
      await tester.pumpAndSettle();

      verify(
        () => playSessionBloc.add(
          const SubmitWrapUp(
            publicId: 'playSession-1',
            wrapUpText: 'Beat the Soul Master boss',
          ),
        ),
      ).called(1);
    });

    testWidgets('dispatches EndPlaySession when Skip wrap-up is tapped', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.widgetWithText(TextButton, 'Skip wrap-up'));
      await tester.pumpAndSettle();

      verify(
        () => playSessionBloc.add(
          const EndPlaySession(publicId: 'playSession-1'),
        ),
      ).called(1);
    });

    testWidgets('shows SnackBar on PlaySessionError via listener', (
      tester,
    ) async {
      whenListen(
        playSessionBloc,
        Stream<PlaySessionState>.fromIterable([
          const PlaySessionError(message: 'Failed to submit wrapUp'),
        ]),
        initialState: ActivePlaySessionLoaded(playSession: _samplePlaySession),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Failed to submit wrapUp'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('does not show game title when no active playSession', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Hollow Knight'), findsNothing);
      // But still shows the wrapUp form.
      expect(find.text('What happened this session?'), findsOneWidget);
    });

    testWidgets('shows hint text in TextFormField', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _samplePlaySession));

      await tester.pumpWidget(buildSubject());

      expect(find.textContaining('Beat the first boss'), findsOneWidget);
    });
  });
}
