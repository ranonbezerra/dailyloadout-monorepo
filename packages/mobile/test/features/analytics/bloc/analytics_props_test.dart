import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

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
  genres: [GenreStat(genre: 'RPG', totalMinutes: 600, missionCount: 10)],
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

void main() {
  group('AnalyticsEvent', () {
    test('LoadAnalytics supports value equality', () {
      expect(const LoadAnalytics(), const LoadAnalytics());
      expect(const LoadAnalytics().props, isEmpty);
    });

    test('LoadTimeline supports value equality', () {
      expect(const LoadTimeline(), const LoadTimeline());
      expect(const LoadTimeline().props, isEmpty);
    });

    test('LoadMoreTimeline supports value equality', () {
      expect(const LoadMoreTimeline(), const LoadMoreTimeline());
      expect(const LoadMoreTimeline().props, isEmpty);
    });
  });

  group('AnalyticsState', () {
    test('AnalyticsInitial supports value equality', () {
      expect(const AnalyticsInitial(), const AnalyticsInitial());
      expect(const AnalyticsInitial().props, isEmpty);
    });

    test('AnalyticsLoading supports value equality', () {
      expect(const AnalyticsLoading(), const AnalyticsLoading());
      expect(const AnalyticsLoading().props, isEmpty);
    });

    test('AnalyticsLoaded supports value equality, props and copyWith', () {
      final a = AnalyticsLoaded(
        overview: _overview,
        heatmap: _heatmap,
        genreStats: _genreStats,
        platformStats: _platformStats,
        timelineItems: [_timelineEntry],
        timelineTotal: 2,
      );
      final b = AnalyticsLoaded(
        overview: _overview,
        heatmap: _heatmap,
        genreStats: _genreStats,
        platformStats: _platformStats,
        timelineItems: [_timelineEntry],
        timelineTotal: 2,
      );
      expect(a, b);
      expect(a.hasMoreTimeline, true);
      expect(a.isLoadingMoreTimeline, false);
      expect(a.props, [
        _overview,
        _heatmap,
        _genreStats,
        _platformStats,
        [_timelineEntry],
        2,
        false,
        null,
      ]);

      final updated = a.copyWith(isLoadingMoreTimeline: true, timelineTotal: 1);
      expect(updated.isLoadingMoreTimeline, true);
      expect(updated.timelineTotal, 1);
      expect(updated.hasMoreTimeline, false);
      expect(updated.overview, _overview);

      final errored = a.copyWith(loadMoreTimelineError: 'oops');
      expect(errored.loadMoreTimelineError, 'oops');
      expect(errored.props.last, 'oops');
    });

    test('AnalyticsLoaded uses default timeline values', () {
      final a = AnalyticsLoaded(
        overview: _overview,
        heatmap: _heatmap,
        genreStats: _genreStats,
        platformStats: _platformStats,
      );
      expect(a.timelineItems, isEmpty);
      expect(a.timelineTotal, 0);
      expect(a.isLoadingMoreTimeline, false);
      expect(a.hasMoreTimeline, false);
    });

    test('AnalyticsError supports value equality and props', () {
      const a = AnalyticsError(message: 'boom');
      const b = AnalyticsError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
    });
  });
}
