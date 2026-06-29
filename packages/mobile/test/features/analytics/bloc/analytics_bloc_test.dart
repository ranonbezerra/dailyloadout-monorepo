import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockAnalyticsRepository extends Mock implements AnalyticsRepository {}

// -----------------------------------------------------------------
// Test fixtures
// -----------------------------------------------------------------

final _overview = StatsOverview(
  totalGames: 42,
  statusCounts: const {'playing': 5, 'backlog': 20, 'completed': 10},
  playSessionsLast30d: 15,
  avgPlaySessionDurationMinutes: 90.5,
  userCreatedAt: DateTime.utc(2024),
);

const _heatmap = PlayHeatmap(
  days: [HeatmapDay(date: '2025-06-01', count: 3, totalMinutes: 120)],
);

const _genreStats = GenreStats(
  genres: [GenreStat(genre: 'RPG', totalMinutes: 600, playSessionCount: 10)],
);

const _platformStats = PlatformStats(
  platforms: [
    PlatformStat(
      platformSlug: 'ps5',
      platformLabel: 'PlayStation 5',
      gameCount: 12,
      playSessionCount: 8,
      totalMinutes: 480,
    ),
  ],
);

final _timelineEntry = TimelineEntry(
  publicId: 'tl-001',
  gameTitle: 'Elden Ring',
  platformLabel: 'PlayStation 5',
  playSessionType: 'regular',
  startedAt: DateTime.utc(2025, 6, 10, 14),
  endedAt: DateTime.utc(2025, 6, 10, 16, 30),
  durationMinutes: 150,
);

final _timelineEntry2 = TimelineEntry(
  publicId: 'tl-002',
  gameTitle: 'Hollow Knight',
  platformLabel: 'PC',
  playSessionType: 'regular',
  startedAt: DateTime.utc(2025, 6, 11, 10),
  endedAt: DateTime.utc(2025, 6, 11, 12),
  durationMinutes: 120,
);

final _timelineResponse = TimelineResponse(items: [_timelineEntry], total: 2);

final _timelineResponsePage2 = TimelineResponse(
  items: [_timelineEntry2],
  total: 2,
);

// -----------------------------------------------------------------
// Tests
// -----------------------------------------------------------------

void main() {
  late MockAnalyticsRepository mockAnalyticsRepository;

  setUp(() {
    mockAnalyticsRepository = MockAnalyticsRepository();
  });

  AnalyticsBloc buildBloc() =>
      AnalyticsBloc(analyticsRepository: mockAnalyticsRepository);

  group('AnalyticsBloc', () {
    test('initial state is AnalyticsInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const AnalyticsInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // LoadAnalytics
    // ---------------------------------------------------------------
    group('LoadAnalytics', () {
      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits [AnalyticsLoading, AnalyticsLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getOverview(),
          ).thenAnswer((_) async => _overview);
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => [
          const AnalyticsLoading(),
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
          ),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits [AnalyticsLoading, AnalyticsError] '
        'on DioException',
        setUp: () {
          when(() => mockAnalyticsRepository.getOverview()).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Server error'},
              ),
            ),
          );
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'Server error'),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits [AnalyticsLoading, AnalyticsError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getOverview(),
          ).thenThrow(Exception('unexpected'));
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'Exception: unexpected'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadTimeline
    // ---------------------------------------------------------------
    group('LoadTimeline', () {
      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits updated state with timeline data '
        'when state is AnalyticsLoaded',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _timelineResponse);
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
        act: (bloc) => bloc.add(const LoadTimeline()),
        expect: () => [
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
          ),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits AnalyticsLoading when state '
        'is not AnalyticsLoaded',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _timelineResponse);
        },
        build: buildBloc,
        seed: () => const AnalyticsInitial(),
        act: (bloc) => bloc.add(const LoadTimeline()),
        expect: () => const [AnalyticsLoading()],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits [AnalyticsError] on DioException '
        'when state is AnalyticsLoaded',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Timeline error'},
              ),
            ),
          );
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
        act: (bloc) => bloc.add(const LoadTimeline()),
        expect: () => const [AnalyticsError(message: 'Timeline error')],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'emits [AnalyticsError] on generic Exception',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('timeline failed'));
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
        ),
        act: (bloc) => bloc.add(const LoadTimeline()),
        expect: () => const [
          AnalyticsError(message: 'Exception: timeline failed'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadMoreTimeline
    // ---------------------------------------------------------------
    group('LoadMoreTimeline', () {
      blocTest<AnalyticsBloc, AnalyticsState>(
        'appends items and clears isLoadingMoreTimeline '
        'on success',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: 1,
            ),
          ).thenAnswer((_) async => _timelineResponsePage2);
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 2,
        ),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => [
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
            isLoadingMoreTimeline: true,
          ),
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry, _timelineEntry2],
            timelineTotal: 2,
          ),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'does nothing when state is not AnalyticsLoaded',
        build: buildBloc,
        seed: () => const AnalyticsInitial(),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => <AnalyticsState>[],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'does nothing when hasMoreTimeline is false',
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry, _timelineEntry2],
          timelineTotal: 2,
        ),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => <AnalyticsState>[],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'does nothing when already loading more',
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 2,
          isLoadingMoreTimeline: true,
        ),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => <AnalyticsState>[],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'keeps the dashboard and surfaces loadMoreTimelineError '
        'on DioException (no full-screen AnalyticsError)',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Page error'},
              ),
            ),
          );
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 2,
        ),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => [
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
            isLoadingMoreTimeline: true,
          ),
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
            loadMoreTimelineError: 'Page error',
          ),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'keeps the dashboard and surfaces loadMoreTimelineError '
        'on generic Exception',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getTimeline(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('network down'));
        },
        build: buildBloc,
        seed: () => AnalyticsLoaded(
          overview: _overview,
          heatmap: _heatmap,
          genreStats: _genreStats,
          platformStats: _platformStats,
          timelineItems: [_timelineEntry],
          timelineTotal: 2,
        ),
        act: (bloc) => bloc.add(const LoadMoreTimeline()),
        expect: () => [
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
            isLoadingMoreTimeline: true,
          ),
          AnalyticsLoaded(
            overview: _overview,
            heatmap: _heatmap,
            genreStats: _genreStats,
            platformStats: _platformStats,
            timelineItems: [_timelineEntry],
            timelineTotal: 2,
            loadMoreTimelineError: 'Exception: network down',
          ),
        ],
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException paths)', () {
      blocTest<AnalyticsBloc, AnalyticsState>(
        'returns fallback when response is null '
        'and message is null',
        setUp: () {
          when(
            () => mockAnalyticsRepository.getOverview(),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'returns e.message when response data '
        'has no detail key',
        setUp: () {
          when(() => mockAnalyticsRepository.getOverview()).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'timeout exceeded',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 504,
                data: <String, dynamic>{'error': 'gateway timeout'},
              ),
            ),
          );
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'timeout exceeded'),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'returns e.message when response data '
        'is not a Map',
        setUp: () {
          when(() => mockAnalyticsRepository.getOverview()).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'bad response',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: 'plain text error',
              ),
            ),
          );
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'bad response'),
        ],
      );

      blocTest<AnalyticsBloc, AnalyticsState>(
        'falls through when detail is not a String',
        setUp: () {
          when(() => mockAnalyticsRepository.getOverview()).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'fallback msg',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{'detail': 42},
              ),
            ),
          );
          when(
            () => mockAnalyticsRepository.getPlayHeatmap(),
          ).thenAnswer((_) async => _heatmap);
          when(
            () => mockAnalyticsRepository.getGenreStats(),
          ).thenAnswer((_) async => _genreStats);
          when(
            () => mockAnalyticsRepository.getPlatformStats(),
          ).thenAnswer((_) async => _platformStats);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadAnalytics()),
        expect: () => const [
          AnalyticsLoading(),
          AnalyticsError(message: 'fallback msg'),
        ],
      );
    });
  });
}
