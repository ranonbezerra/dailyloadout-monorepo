import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/features/play/view/play_page.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockPlaySessionBloc extends MockBloc<PlaySessionEvent, PlaySessionState>
    implements PlaySessionBloc {}

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

final _playSession = PlaySession(
  publicId: 'playSession-1',
  libraryEntry: _entry,
  playSessionType: 'regular',
  recapText: 'Continue exploring Hallownest.',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
);

final _playSessionNoRecap = PlaySession(
  publicId: 'playSession-2',
  libraryEntry: _entry,
  playSessionType: 'regular',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  late MockPlaySessionBloc playSessionBloc;

  setUp(() {
    playSessionBloc = MockPlaySessionBloc();
  });

  tearDown(() {
    playSessionBloc.close();
  });

  /// Wrapper with a GoRouter so `context.go()` resolves in tests, and
  /// stub destinations for each door / playSession action.
  Widget buildSubject({bool conciergeEnabled = false}) {
    final router = GoRouter(
      initialLocation: '/play',
      routes: [
        GoRoute(
          path: '/play',
          builder: (_, __) => PlayPage(conciergeEnabled: conciergeEnabled),
        ),
        GoRoute(
          path: '/play/pick',
          builder: (_, __) => const Scaffold(body: Text('Pick stub')),
        ),
        GoRoute(
          path: '/play/play-sessions',
          builder: (_, __) => const Scaffold(body: Text('PlaySessions stub')),
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
          path: '/play-sessions/:id/recap',
          builder: (_, __) => const Scaffold(body: Text('Recap stub')),
        ),
        GoRoute(
          path: '/play-sessions/:id/wrap-up',
          builder: (_, __) => const Scaffold(body: Text('WrapUp stub')),
        ),
      ],
    );

    return BlocProvider<PlaySessionBloc>.value(
      value: playSessionBloc,
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('PlayPage', () {
    testWidgets('dispatches LoadActivePlaySession on init', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      verify(
        () => playSessionBloc.add(const LoadActivePlaySession()),
      ).called(1);
    });

    testWidgets('shows AppBar with Play title', (tester) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(of: find.byType(AppBar), matching: find.text('Play')),
        findsOneWidget,
      );
    });

    testWidgets('shows no-active-playSession card when ActivePlaySessionLoaded '
        'with null playSession', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('No session running'), findsOneWidget);
      expect(
        find.text('Pick something below and start playing.'),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.rocket_launch_outlined), findsOneWidget);
    });

    testWidgets('shows no-active-playSession card for PlaySessionInitial', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('No session running'), findsOneWidget);
    });

    testWidgets('shows loading placeholder when PlaySessionLoading', (
      tester,
    ) async {
      when(() => playSessionBloc.state).thenReturn(const PlaySessionLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('No session running'), findsNothing);
    });

    testWidgets('shows error card and locks start doors on PlaySessionError', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const PlaySessionError(message: 'Network down'));

      await tester.pumpWidget(buildSubject());

      // Genuine error is surfaced (not silently treated as "no playSession").
      expect(find.text("Couldn't load your session"), findsOneWidget);
      expect(find.text('Network down'), findsOneWidget);
      expect(find.text('No session running'), findsNothing);

      // Start doors are locked because the active playSession is unknown.
      expect(
        find.text('Could not check your active session'),
        findsNWidgets(2),
      );
      expect(find.byIcon(Icons.lock_outline), findsNWidgets(2));

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Pick stub'), findsNothing);
    });

    testWidgets('tapping Retry on the error card re-dispatches '
        'LoadActivePlaySession', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const PlaySessionError(message: 'Network down'));

      await tester.pumpWidget(buildSubject());
      clearInteractions(playSessionBloc);

      await tester.tap(find.text('Retry'));
      await tester.pump();

      verify(
        () => playSessionBloc.add(const LoadActivePlaySession()),
      ).called(1);
    });

    testWidgets(
      'shows active playSession card with title, platform and recap',
      (tester) async {
        when(
          () => playSessionBloc.state,
        ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

        await tester.pumpWidget(buildSubject());

        expect(find.text('Active session'), findsOneWidget);
        expect(find.text('Hollow Knight'), findsOneWidget);
        expect(find.text('PlayStation 5'), findsOneWidget);
        expect(find.text('Continue exploring Hallownest.'), findsOneWidget);
      },
    );

    testWidgets('active playSession card shows Recap and Wrap up buttons', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

      await tester.pumpWidget(buildSubject());

      // Resume was removed — it had no real destination.
      expect(find.text('Resume'), findsNothing);
      expect(find.text('Recap'), findsOneWidget);
      expect(find.widgetWithText(OutlinedButton, 'Wrap up'), findsOneWidget);
    });

    testWidgets('active playSession card hides recap when none present', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSessionNoRecap));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Active session'), findsOneWidget);
      expect(find.text('Continue exploring Hallownest.'), findsNothing);
    });

    testWidgets('tapping Recap navigates to the playSession recap', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text('Recap'));
      await tester.pumpAndSettle();

      expect(find.text('Recap stub'), findsOneWidget);
    });

    testWidgets('tapping Wrap up navigates to the playSession wrapUp', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.widgetWithText(OutlinedButton, 'Wrap up'));
      await tester.pumpAndSettle();

      expect(find.text('WrapUp stub'), findsOneWidget);
    });

    testWidgets('start doors are disabled while a playSession is active', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

      await tester.pumpWidget(buildSubject());

      // Hint replaces the subtitle on both start doors.
      expect(find.text('Finish your active session first'), findsNWidgets(2));
      expect(find.byIcon(Icons.lock_outline), findsNWidgets(2));

      // Tapping the disabled door does not navigate.
      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Pick stub'), findsNothing);
    });

    testWidgets('Ask door stays enabled while a playSession is active', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(ActivePlaySessionLoaded(playSession: _playSession));

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      await tester.tap(find.text('Ask'));
      await tester.pumpAndSettle();

      expect(find.text('Concierge stub'), findsOneWidget);
    });

    testWidgets('start doors are enabled when there is no active playSession', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Finish your active session first'), findsNothing);
      expect(find.byIcon(Icons.lock_outline), findsNothing);

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();
      expect(find.text('Pick stub'), findsOneWidget);
    });

    testWidgets("shows What's next section with the two default doors", (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text("What's next?"), findsOneWidget);
      expect(find.text("What's the move?"), findsOneWidget);
      expect(find.text("I'll choose"), findsOneWidget);
    });

    testWidgets('does NOT show concierge door when conciergeEnabled is false', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Ask'), findsNothing);
      expect(find.byIcon(Icons.auto_awesome), findsNothing);
    });

    testWidgets('shows concierge door when conciergeEnabled is true', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      expect(find.text('Ask'), findsOneWidget);
      expect(find.text('Chat about what to play.'), findsOneWidget);
      expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
    });

    testWidgets("tapping What's the move? navigates to /play/pick", (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text("What's the move?"));
      await tester.pumpAndSettle();

      expect(find.text('Pick stub'), findsOneWidget);
    });

    testWidgets("tapping I'll choose navigates to /library", (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());

      await tester.tap(find.text("I'll choose"));
      await tester.pumpAndSettle();

      expect(find.text('Library stub'), findsOneWidget);
    });

    testWidgets('tapping Ask navigates to /play/concierge', (tester) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject(conciergeEnabled: true));

      await tester.tap(find.text('Ask'));
      await tester.pumpAndSettle();

      expect(find.text('Concierge stub'), findsOneWidget);
    });

    testWidgets('pull to refresh re-dispatches LoadActivePlaySession', (
      tester,
    ) async {
      when(
        () => playSessionBloc.state,
      ).thenReturn(const ActivePlaySessionLoaded());

      await tester.pumpWidget(buildSubject());
      // Init dispatch counts as one.
      clearInteractions(playSessionBloc);

      await tester.fling(find.byType(ListView), const Offset(0, 400), 1000);
      await tester.pumpAndSettle();

      verify(
        () => playSessionBloc.add(const LoadActivePlaySession()),
      ).called(1);
    });
  });
}
