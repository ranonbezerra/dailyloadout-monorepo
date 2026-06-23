import 'package:app/core/analytics/analytics_models.dart';
import 'package:flutter_test/flutter_test.dart';

// -----------------------------------------------------------------
// JSON fixture builders
// -----------------------------------------------------------------

Map<String, dynamic> _statsOverviewJson({
  int totalGames = 42,
  Map<String, dynamic>? statusCounts,
  int missionsLast30d = 15,
  double? avgMissionDurationMinutes = 90.5,
  String userCreatedAt = '2024-01-15T00:00:00Z',
}) => <String, dynamic>{
  'total_games': totalGames,
  'status_counts':
      statusCounts ??
      <String, dynamic>{
        'playing': 5,
        'backlog': 20,
        'completed': 10,
        'dropped': 3,
        'paused': 4,
      },
  'missions_last_30d': missionsLast30d,
  'avg_mission_duration_minutes': avgMissionDurationMinutes,
  'user_created_at': userCreatedAt,
};

Map<String, dynamic> _heatmapDayJson({
  String date = '2025-06-01',
  int count = 3,
  int totalMinutes = 120,
}) => <String, dynamic>{
  'date': date,
  'count': count,
  'total_minutes': totalMinutes,
};

Map<String, dynamic> _playHeatmapJson({List<Map<String, dynamic>>? days}) =>
    <String, dynamic>{'days': days ?? <Map<String, dynamic>>[]};

Map<String, dynamic> _genreStatJson({
  String genre = 'RPG',
  int totalMinutes = 600,
  int missionCount = 10,
}) => <String, dynamic>{
  'genre': genre,
  'total_minutes': totalMinutes,
  'mission_count': missionCount,
};

Map<String, dynamic> _genreStatsJson({List<Map<String, dynamic>>? genres}) =>
    <String, dynamic>{'genres': genres ?? <Map<String, dynamic>>[]};

Map<String, dynamic> _platformStatJson({
  String platformSlug = 'ps5',
  String platformLabel = 'PlayStation 5',
  int gameCount = 12,
  int missionCount = 8,
  int totalMinutes = 480,
}) => <String, dynamic>{
  'platform_slug': platformSlug,
  'platform_label': platformLabel,
  'game_count': gameCount,
  'mission_count': missionCount,
  'total_minutes': totalMinutes,
};

Map<String, dynamic> _platformStatsJson({
  List<Map<String, dynamic>>? platforms,
}) => <String, dynamic>{'platforms': platforms ?? <Map<String, dynamic>>[]};

Map<String, dynamic> _timelineEntryJson({
  String publicId = 'timeline-001',
  String gameTitle = 'Elden Ring',
  String platformLabel = 'PlayStation 5',
  String missionType = 'regular',
  String? briefingText = 'Time to explore!',
  String? debriefText = 'Great session.',
  String? endedVia = 'debrief',
  String startedAt = '2025-06-10T14:00:00Z',
  String? endedAt = '2025-06-10T16:30:00Z',
  int? durationMinutes = 150,
}) => <String, dynamic>{
  'public_id': publicId,
  'game_title': gameTitle,
  'platform_label': platformLabel,
  'mission_type': missionType,
  'briefing_text': briefingText,
  'debrief_text': debriefText,
  'ended_via': endedVia,
  'started_at': startedAt,
  'ended_at': endedAt,
  'duration_minutes': durationMinutes,
};

Map<String, dynamic> _timelineResponseJson({
  List<Map<String, dynamic>>? items,
  int total = 0,
}) => <String, dynamic>{
  'items': items ?? <Map<String, dynamic>>[],
  'total': total,
};

// -----------------------------------------------------------------
// Tests
// -----------------------------------------------------------------

void main() {
  // ── StatsOverview ──────────────────────────────────────

  group('StatsOverview', () {
    group('fromJson', () {
      test('parses full JSON with all fields', () {
        final json = _statsOverviewJson();
        final overview = StatsOverview.fromJson(json);

        expect(overview.totalGames, 42);
        expect(overview.statusCounts, {
          'playing': 5,
          'backlog': 20,
          'completed': 10,
          'dropped': 3,
          'paused': 4,
        });
        expect(overview.missionsLast30d, 15);
        expect(overview.avgMissionDurationMinutes, 90.5);
        expect(overview.userCreatedAt, DateTime.utc(2024, 1, 15));
      });

      test('parses JSON with null avgMissionDurationMinutes', () {
        final json = _statsOverviewJson(avgMissionDurationMinutes: null);
        final overview = StatsOverview.fromJson(json);

        expect(overview.avgMissionDurationMinutes, isNull);
        expect(overview.totalGames, 42);
        expect(overview.missionsLast30d, 15);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(_statsOverviewJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different totalGames '
          'are not equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(_statsOverviewJson(totalGames: 99));

        expect(a, isNot(equals(b)));
      });

      test('instances with different statusCounts '
          'are not equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(
          _statsOverviewJson(statusCounts: <String, dynamic>{'playing': 1}),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different missionsLast30d '
          'are not equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(
          _statsOverviewJson(missionsLast30d: 0),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different '
          'avgMissionDurationMinutes are not equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(
          _statsOverviewJson(avgMissionDurationMinutes: 30),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different userCreatedAt '
          'are not equal', () {
        final a = StatsOverview.fromJson(_statsOverviewJson());
        final b = StatsOverview.fromJson(
          _statsOverviewJson(userCreatedAt: '2023-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final overview = StatsOverview.fromJson(_statsOverviewJson());

        expect(overview.props, hasLength(5));
      });
    });
  });

  // ── HeatmapDay ─────────────────────────────────────────

  group('HeatmapDay', () {
    group('fromJson', () {
      test('parses JSON correctly', () {
        final json = _heatmapDayJson();
        final day = HeatmapDay.fromJson(json);

        expect(day.date, '2025-06-01');
        expect(day.count, 3);
        expect(day.totalMinutes, 120);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = HeatmapDay.fromJson(_heatmapDayJson());
        final b = HeatmapDay.fromJson(_heatmapDayJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different date '
          'are not equal', () {
        final a = HeatmapDay.fromJson(_heatmapDayJson());
        final b = HeatmapDay.fromJson(_heatmapDayJson(date: '2025-06-02'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different count '
          'are not equal', () {
        final a = HeatmapDay.fromJson(_heatmapDayJson());
        final b = HeatmapDay.fromJson(_heatmapDayJson(count: 1));

        expect(a, isNot(equals(b)));
      });

      test('instances with different totalMinutes '
          'are not equal', () {
        final a = HeatmapDay.fromJson(_heatmapDayJson());
        final b = HeatmapDay.fromJson(_heatmapDayJson(totalMinutes: 60));

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final day = HeatmapDay.fromJson(_heatmapDayJson());

        expect(day.props, hasLength(3));
      });
    });
  });

  // ── PlayHeatmap ────────────────────────────────────────

  group('PlayHeatmap', () {
    group('fromJson', () {
      test('parses JSON with empty days', () {
        final json = _playHeatmapJson();
        final heatmap = PlayHeatmap.fromJson(json);

        expect(heatmap.days, isEmpty);
      });

      test('parses JSON with multiple days', () {
        final json = _playHeatmapJson(
          days: [
            _heatmapDayJson(count: 2, totalMinutes: 90),
            _heatmapDayJson(date: '2025-06-02', totalMinutes: 45),
            _heatmapDayJson(date: '2025-06-03', count: 4, totalMinutes: 200),
          ],
        );
        final heatmap = PlayHeatmap.fromJson(json);

        expect(heatmap.days, hasLength(3));
        expect(heatmap.days[0].date, '2025-06-01');
        expect(heatmap.days[1].date, '2025-06-02');
        expect(heatmap.days[2].date, '2025-06-03');
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = _playHeatmapJson(days: [_heatmapDayJson()]);
        final a = PlayHeatmap.fromJson(json);
        final b = PlayHeatmap.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different days '
          'are not equal', () {
        final a = PlayHeatmap.fromJson(_playHeatmapJson());
        final b = PlayHeatmap.fromJson(
          _playHeatmapJson(days: [_heatmapDayJson()]),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final heatmap = PlayHeatmap.fromJson(_playHeatmapJson());

        expect(heatmap.props, hasLength(1));
      });
    });
  });

  // ── GenreStat ──────────────────────────────────────────

  group('GenreStat', () {
    group('fromJson', () {
      test('parses JSON correctly', () {
        final json = _genreStatJson();
        final stat = GenreStat.fromJson(json);

        expect(stat.genre, 'RPG');
        expect(stat.totalMinutes, 600);
        expect(stat.missionCount, 10);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = GenreStat.fromJson(_genreStatJson());
        final b = GenreStat.fromJson(_genreStatJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different genre '
          'are not equal', () {
        final a = GenreStat.fromJson(_genreStatJson());
        final b = GenreStat.fromJson(_genreStatJson(genre: 'FPS'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different totalMinutes '
          'are not equal', () {
        final a = GenreStat.fromJson(_genreStatJson());
        final b = GenreStat.fromJson(_genreStatJson(totalMinutes: 100));

        expect(a, isNot(equals(b)));
      });

      test('instances with different missionCount '
          'are not equal', () {
        final a = GenreStat.fromJson(_genreStatJson());
        final b = GenreStat.fromJson(_genreStatJson(missionCount: 1));

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final stat = GenreStat.fromJson(_genreStatJson());

        expect(stat.props, hasLength(3));
      });
    });
  });

  // ── GenreStats ─────────────────────────────────────────

  group('GenreStats', () {
    group('fromJson', () {
      test('parses JSON with empty list', () {
        final json = _genreStatsJson();
        final stats = GenreStats.fromJson(json);

        expect(stats.genres, isEmpty);
      });

      test('parses JSON with items', () {
        final json = _genreStatsJson(
          genres: [
            _genreStatJson(),
            _genreStatJson(genre: 'Action', totalMinutes: 300, missionCount: 5),
          ],
        );
        final stats = GenreStats.fromJson(json);

        expect(stats.genres, hasLength(2));
        expect(stats.genres[0].genre, 'RPG');
        expect(stats.genres[1].genre, 'Action');
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = _genreStatsJson(genres: [_genreStatJson()]);
        final a = GenreStats.fromJson(json);
        final b = GenreStats.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different genres '
          'are not equal', () {
        final a = GenreStats.fromJson(_genreStatsJson());
        final b = GenreStats.fromJson(
          _genreStatsJson(genres: [_genreStatJson()]),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final stats = GenreStats.fromJson(_genreStatsJson());

        expect(stats.props, hasLength(1));
      });
    });
  });

  // ── PlatformStat ───────────────────────────────────────

  group('PlatformStat', () {
    group('fromJson', () {
      test('parses JSON correctly', () {
        final json = _platformStatJson();
        final stat = PlatformStat.fromJson(json);

        expect(stat.platformSlug, 'ps5');
        expect(stat.platformLabel, 'PlayStation 5');
        expect(stat.gameCount, 12);
        expect(stat.missionCount, 8);
        expect(stat.totalMinutes, 480);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different platformSlug '
          'are not equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson(platformSlug: 'pc'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different platformLabel '
          'are not equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson(platformLabel: 'PC'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different gameCount '
          'are not equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson(gameCount: 1));

        expect(a, isNot(equals(b)));
      });

      test('instances with different missionCount '
          'are not equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson(missionCount: 1));

        expect(a, isNot(equals(b)));
      });

      test('instances with different totalMinutes '
          'are not equal', () {
        final a = PlatformStat.fromJson(_platformStatJson());
        final b = PlatformStat.fromJson(_platformStatJson(totalMinutes: 60));

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final stat = PlatformStat.fromJson(_platformStatJson());

        expect(stat.props, hasLength(5));
      });
    });
  });

  // ── PlatformStats ──────────────────────────────────────

  group('PlatformStats', () {
    group('fromJson', () {
      test('parses JSON with empty list', () {
        final json = _platformStatsJson();
        final stats = PlatformStats.fromJson(json);

        expect(stats.platforms, isEmpty);
      });

      test('parses JSON with items', () {
        final json = _platformStatsJson(
          platforms: [
            _platformStatJson(),
            _platformStatJson(
              platformSlug: 'pc',
              platformLabel: 'PC',
              gameCount: 30,
              missionCount: 20,
              totalMinutes: 1200,
            ),
          ],
        );
        final stats = PlatformStats.fromJson(json);

        expect(stats.platforms, hasLength(2));
        expect(stats.platforms[0].platformSlug, 'ps5');
        expect(stats.platforms[1].platformSlug, 'pc');
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = _platformStatsJson(platforms: [_platformStatJson()]);
        final a = PlatformStats.fromJson(json);
        final b = PlatformStats.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different platforms '
          'are not equal', () {
        final a = PlatformStats.fromJson(_platformStatsJson());
        final b = PlatformStats.fromJson(
          _platformStatsJson(platforms: [_platformStatJson()]),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final stats = PlatformStats.fromJson(_platformStatsJson());

        expect(stats.props, hasLength(1));
      });
    });
  });

  // ── TimelineEntry ──────────────────────────────────────

  group('TimelineEntry', () {
    group('fromJson', () {
      test('parses JSON with all fields', () {
        final json = _timelineEntryJson();
        final entry = TimelineEntry.fromJson(json);

        expect(entry.publicId, 'timeline-001');
        expect(entry.gameTitle, 'Elden Ring');
        expect(entry.platformLabel, 'PlayStation 5');
        expect(entry.missionType, 'regular');
        expect(entry.briefingText, 'Time to explore!');
        expect(entry.debriefText, 'Great session.');
        expect(entry.endedVia, 'debrief');
        expect(entry.startedAt, DateTime.utc(2025, 6, 10, 14));
        expect(entry.endedAt, DateTime.utc(2025, 6, 10, 16, 30));
        expect(entry.durationMinutes, 150);
      });

      test('parses JSON with null optional fields', () {
        final json = _timelineEntryJson(
          briefingText: null,
          debriefText: null,
          endedVia: null,
          endedAt: null,
          durationMinutes: null,
        );
        final entry = TimelineEntry.fromJson(json);

        expect(entry.publicId, 'timeline-001');
        expect(entry.gameTitle, 'Elden Ring');
        expect(entry.platformLabel, 'PlayStation 5');
        expect(entry.missionType, 'regular');
        expect(entry.briefingText, isNull);
        expect(entry.debriefText, isNull);
        expect(entry.endedVia, isNull);
        expect(entry.startedAt, DateTime.utc(2025, 6, 10, 14));
        expect(entry.endedAt, isNull);
        expect(entry.durationMinutes, isNull);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(_timelineEntryJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different publicId '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(_timelineEntryJson(publicId: 'other'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different gameTitle '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(gameTitle: 'Hollow Knight'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different platformLabel '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(platformLabel: 'PC'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different missionType '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(missionType: 'retroactive'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different briefingText '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(briefingText: 'Different'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different debriefText '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(debriefText: 'Different'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different endedVia '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(endedVia: 'auto_clamp'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different startedAt '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(startedAt: '2024-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different endedAt '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(endedAt: '2025-06-10T18:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different durationMinutes '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(durationMinutes: 30),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with vs without optional fields '
          'are not equal', () {
        final a = TimelineEntry.fromJson(_timelineEntryJson());
        final b = TimelineEntry.fromJson(
          _timelineEntryJson(
            briefingText: null,
            debriefText: null,
            endedVia: null,
            endedAt: null,
            durationMinutes: null,
          ),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final entry = TimelineEntry.fromJson(_timelineEntryJson());

        expect(entry.props, hasLength(10));
      });
    });
  });

  // ── TimelineResponse ───────────────────────────────────

  group('TimelineResponse', () {
    group('fromJson', () {
      test('parses JSON with empty items', () {
        final json = _timelineResponseJson();
        final response = TimelineResponse.fromJson(json);

        expect(response.items, isEmpty);
        expect(response.total, 0);
      });

      test('parses JSON with items', () {
        final json = _timelineResponseJson(
          items: [
            _timelineEntryJson(publicId: 'tl-1'),
            _timelineEntryJson(publicId: 'tl-2', gameTitle: 'Hollow Knight'),
          ],
          total: 10,
        );
        final response = TimelineResponse.fromJson(json);

        expect(response.items, hasLength(2));
        expect(response.total, 10);
        expect(response.items[0].publicId, 'tl-1');
        expect(response.items[0].gameTitle, 'Elden Ring');
        expect(response.items[1].publicId, 'tl-2');
        expect(response.items[1].gameTitle, 'Hollow Knight');
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = _timelineResponseJson(
          items: [_timelineEntryJson()],
          total: 1,
        );
        final a = TimelineResponse.fromJson(json);
        final b = TimelineResponse.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different total '
          'are not equal', () {
        final a = TimelineResponse.fromJson(_timelineResponseJson(total: 5));
        final b = TimelineResponse.fromJson(_timelineResponseJson(total: 10));

        expect(a, isNot(equals(b)));
      });

      test('instances with different items '
          'are not equal', () {
        final a = TimelineResponse.fromJson(
          _timelineResponseJson(
            items: [_timelineEntryJson(publicId: 'tl-1')],
            total: 1,
          ),
        );
        final b = TimelineResponse.fromJson(
          _timelineResponseJson(
            items: [_timelineEntryJson(publicId: 'tl-2')],
            total: 1,
          ),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final response = TimelineResponse.fromJson(_timelineResponseJson());

        expect(response.props, hasLength(2));
      });
    });
  });
}
