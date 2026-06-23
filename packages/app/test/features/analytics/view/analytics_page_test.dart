import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/analytics/view/analytics_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAnalyticsBloc extends MockBloc<AnalyticsEvent, AnalyticsState>
    implements AnalyticsBloc {}

// -----------------------------------------------------------------
// Test fixtures
// -----------------------------------------------------------------

final _overview = StatsOverview(
  totalGames: 42,
  statusCounts: const {'playing': 5, 'backlog': 20, 'completed': 10},
  missionsLast30d: 15,
  avgMissionDurationMinutes: 90.5,
  userCreatedAt: DateTime.utc(2024),
);

const _heatmap = PlayHeatmap(
  days: [HeatmapDay(date: '2025-06-01', count: 3, totalMinutes: 120)],
);

const _genreStats = GenreStats(
  genres: [
    GenreStat(genre: 'RPG', totalMinutes: 600, missionCount: 10),
    GenreStat(genre: 'Action', totalMinutes: 300, missionCount: 5),
  ],
);

const _platformStats = PlatformStats(
  platforms: [
    PlatformStat(
      platformSlug: 'ps5',
      platformLabel: 'PlayStation 5',
      gameCount: 12,
      missionCount: 8,
      totalMinutes: 480,
    ),
    PlatformStat(
      platformSlug: 'pc',
      platformLabel: 'PC',
      gameCount: 30,
      missionCount: 20,
      totalMinutes: 1200,
    ),
  ],
);

final _timelineEntry = TimelineEntry(
  publicId: 'tl-001',
  gameTitle: 'Elden Ring',
  platformLabel: 'PlayStation 5',
  missionType: 'regular',
  startedAt: DateTime.utc(2025, 6, 10, 14),
  endedAt: DateTime.utc(2025, 6, 10, 16, 30),
  durationMinutes: 150,
);

final _timelineEntry2 = TimelineEntry(
  publicId: 'tl-002',
  gameTitle: 'Hollow Knight',
  platformLabel: 'PC',
  missionType: 'regular',
  startedAt: DateTime.utc(2025, 6, 11, 10),
  endedAt: DateTime.utc(2025, 6, 11, 12),
  durationMinutes: 120,
);

// -----------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------

void main() {
  late MockAnalyticsBloc analyticsBloc;

  setUp(() {
    analyticsBloc = MockAnalyticsBloc();
  });

  tearDown(() {
    analyticsBloc.close();
  });

  Widget buildSubject() {
    return BlocProvider<AnalyticsBloc>.value(
      value: analyticsBloc,
      child: const MaterialApp(home: AnalyticsPage()),
    );
  }

  group('AnalyticsPage', () {
    testWidgets('dispatches LoadAnalytics and LoadTimeline on init', (
      tester,
    ) async {
      when(() => analyticsBloc.state).thenReturn(const AnalyticsInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => analyticsBloc.add(const LoadAnalytics())).called(1);
      verify(() => analyticsBloc.add(const LoadTimeline())).called(1);
    });

    testWidgets('shows AppBar with Analytics title', (tester) async {
      when(() => analyticsBloc.state).thenReturn(const AnalyticsInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Analytics'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows CircularProgressIndicator when AnalyticsLoading', (
      tester,
    ) async {
      when(() => analyticsBloc.state).thenReturn(const AnalyticsLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows error message and Retry button when AnalyticsError', (
      tester,
    ) async {
      when(
        () => analyticsBloc.state,
      ).thenReturn(const AnalyticsError(message: 'Network error'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Network error'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
    });

    testWidgets('shows KPI cards when AnalyticsLoaded', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 1,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Total Games'), findsOneWidget);
      expect(find.text('42'), findsOneWidget);
      expect(find.text('Sessions (30d)'), findsOneWidget);
      expect(find.text('15'), findsOneWidget);
      expect(find.text('Avg Session'), findsOneWidget);
      // 90.5 rounds to 91 => 1h 31m
      expect(find.text('1h 31m'), findsOneWidget);
    });

    testWidgets('shows status chips in Library Status card', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 1,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Library Status'), findsOneWidget);
      expect(find.text('playing 5'), findsOneWidget);
      expect(find.text('backlog 20'), findsOneWidget);
      expect(find.text('completed 10'), findsOneWidget);
    });

    testWidgets('shows Play Activity section title', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Play Activity'), findsOneWidget);
    });

    testWidgets('shows Time by genre section with genre names', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Time by genre'), findsOneWidget);
      expect(find.text('RPG'), findsOneWidget);
      expect(find.text('Action'), findsOneWidget);
    });

    testWidgets('shows Platforms section with platform labels', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Platforms'), findsOneWidget);
      // PlayStation 5 appears in platform card and in timeline entry chip.
      expect(find.text('PlayStation 5'), findsWidgets);
      expect(find.text('PC'), findsWidgets);
    });

    testWidgets('shows Recent sessions section with game titles', (
      tester,
    ) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry, _timelineEntry2],
          timelineTotal: 2,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Recent sessions'), findsOneWidget);
      expect(find.text('Elden Ring'), findsOneWidget);
      expect(find.text('Hollow Knight'), findsOneWidget);
    });

    testWidgets('shows Load more button when hasMoreTimeline is true', (
      tester,
    ) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 5,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(TextButton, 'Load more'), findsOneWidget);
    });

    testWidgets('does not show Load more button '
        'when hasMoreTimeline is false', (tester) async {
      when(() => analyticsBloc.state).thenReturn(
        AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry, _timelineEntry2],
          timelineTotal: 2,
        ),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(TextButton, 'Load more'), findsNothing);
    });

    testWidgets('shows SizedBox.shrink for AnalyticsInitial', (tester) async {
      when(() => analyticsBloc.state).thenReturn(const AnalyticsInitial());

      await tester.pumpWidget(buildSubject());

      // Should not show loading, error, or loaded state body.
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('Retry'), findsNothing);
      expect(find.text('Total Games'), findsNothing);
    });
  });
}
