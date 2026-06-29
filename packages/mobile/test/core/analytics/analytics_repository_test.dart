import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:app/core/api/api_client.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

Response<T> _response<T>(String path, T data) => Response<T>(
  requestOptions: RequestOptions(path: path),
  data: data,
);

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late AnalyticsRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = AnalyticsRepository(apiClient: apiClient);
  });

  group('getOverview', () {
    test('parses StatsOverview', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/stats/overview', <String, dynamic>{
          'total_games': 12,
          'status_counts': <String, dynamic>{'playing': 3, 'backlog': 9},
          'play_sessions_last_30d': 7,
          'avg_play_session_duration_minutes': 85.5,
          'user_created_at': '2025-01-01T00:00:00Z',
        }),
      );

      final overview = await repository.getOverview();

      expect(overview, isA<StatsOverview>());
      expect(overview.totalGames, 12);
      expect(overview.statusCounts['playing'], 3);
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/stats/overview'),
      ).called(1);
    });

    test('rethrows DioException', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/stats/overview'),
        ),
      );

      expect(repository.getOverview, throwsA(isA<DioException>()));
    });
  });

  group('getPlayHeatmap', () {
    test('passes date range and parses PlayHeatmap', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/stats/play-heatmap', <String, dynamic>{
          'days': <Map<String, dynamic>>[
            <String, dynamic>{
              'date': '2025-06-01',
              'count': 2,
              'total_minutes': 90,
            },
          ],
        }),
      );

      final heatmap = await repository.getPlayHeatmap(
        from: '2025-06-01',
        to: '2025-06-30',
      );

      expect(heatmap, isA<PlayHeatmap>());
      expect(heatmap.days, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/stats/play-heatmap',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['from'], '2025-06-01');
      expect(query['to'], '2025-06-30');
    });

    test('omits null date range params', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/stats/play-heatmap', <String, dynamic>{
          'days': <Map<String, dynamic>>[],
        }),
      );

      await repository.getPlayHeatmap();

      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query.containsKey('from'), isFalse);
      expect(query.containsKey('to'), isFalse);
    });
  });

  group('getGenreStats', () {
    test('parses GenreStats', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/stats/genres', <String, dynamic>{
          'genres': <Map<String, dynamic>>[
            <String, dynamic>{
              'genre': 'RPG',
              'total_minutes': 120,
              'play_session_count': 4,
            },
          ],
        }),
      );

      final stats = await repository.getGenreStats();

      expect(stats, isA<GenreStats>());
      expect(stats.genres.first.genre, 'RPG');
      verify(() => dio.get<Map<String, dynamic>>('/v1/stats/genres')).called(1);
    });
  });

  group('getPlatformStats', () {
    test('parses PlatformStats', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/stats/platforms', <String, dynamic>{
          'platforms': <Map<String, dynamic>>[
            <String, dynamic>{
              'platform_slug': 'ps5',
              'platform_label': 'PS5',
              'game_count': 5,
              'play_session_count': 8,
              'total_minutes': 300,
            },
          ],
        }),
      );

      final stats = await repository.getPlatformStats();

      expect(stats, isA<PlatformStats>());
      expect(stats.platforms.first.platformSlug, 'ps5');
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/stats/platforms'),
      ).called(1);
    });
  });

  group('getTimeline', () {
    test('passes pagination and parses TimelineResponse', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/stats/timeline', <String, dynamic>{
          'items': <Map<String, dynamic>>[
            <String, dynamic>{
              'public_id': 'm-1',
              'game_title': 'Elden Ring',
              'platform_label': 'PS5',
              'play_session_type': 'story',
              'started_at': '2025-06-01T18:00:00Z',
            },
          ],
          'total': 1,
        }),
      );

      final timeline = await repository.getTimeline(limit: 10, offset: 20);

      expect(timeline, isA<TimelineResponse>());
      expect(timeline.items, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/stats/timeline',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['limit'], 10);
      expect(query['offset'], 20);
    });
  });
}
