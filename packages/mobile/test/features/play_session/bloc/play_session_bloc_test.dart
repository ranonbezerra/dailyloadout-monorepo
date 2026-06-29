import 'package:app/core/library/library_models.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockPlaySessionRepository extends Mock implements PlaySessionRepository {}

// -------------------------------------------------------------------
// Test fixtures
// -------------------------------------------------------------------

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'elden-ring',
  title: 'Elden Ring',
  metadataSource: 'igdb',
  createdAt: _now,
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _playSession = PlaySession(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
  recapText: 'Welcome back!',
);

final _playSessionListItem = PlaySessionListItem(
  publicId: 'playSession-001',
  libraryEntry: _entry,
  playSessionType: 'new_game',
  startedAt: _now,
);

final _listResponse = PlaySessionListResponse(
  items: [_playSessionListItem],
  total: 1,
);

final _preview = RecapPreview(libraryEntry: _entry, recapText: 'Your recap');

// -------------------------------------------------------------------
// Tests
// -------------------------------------------------------------------

void main() {
  late MockPlaySessionRepository mockPlaySessionRepository;

  setUp(() {
    mockPlaySessionRepository = MockPlaySessionRepository();
  });

  PlaySessionBloc buildBloc() =>
      PlaySessionBloc(playSessionRepository: mockPlaySessionRepository);

  group('PlaySessionBloc', () {
    test('initial state is PlaySessionInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const PlaySessionInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // LoadPlaySessions
    // ---------------------------------------------------------------
    group('LoadPlaySessions', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionListLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionListLoaded(playSessions: [_playSessionListItem], total: 1),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'passes limit and offset to repository',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: 10,
              offset: 20,
            ),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions(limit: 10, offset: 20)),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionListLoaded(playSessions: [_playSessionListItem], total: 1),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: 10,
              offset: 20,
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Server error'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'Server error'),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'Exception: unexpected'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadMorePlaySessions
    // ---------------------------------------------------------------
    group('LoadMorePlaySessions', () {
      final page2Item = PlaySessionListItem(
        publicId: 'playSession-002',
        libraryEntry: _entry,
        playSessionType: 'regular',
        startedAt: _now,
      );
      final page2 = PlaySessionListResponse(items: [page2Item], total: 2);

      blocTest<PlaySessionBloc, PlaySessionState>(
        'appends items when current state '
        'is PlaySessionListLoaded with hasMore',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: 10,
              offset: 1,
            ),
          ).thenAnswer((_) async => page2);
        },
        build: buildBloc,
        seed: () => PlaySessionListLoaded(
          playSessions: [_playSessionListItem],
          total: 2,
        ),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => [
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem, page2Item],
            total: 2,
          ),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'does nothing when state is not PlaySessionListLoaded',
        build: buildBloc,
        seed: () => const PlaySessionInitial(),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => <PlaySessionState>[],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'does nothing when hasMore is false',
        build: buildBloc,
        seed: () => PlaySessionListLoaded(
          playSessions: [_playSessionListItem],
          total: 1,
        ),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => <PlaySessionState>[],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'does nothing when already loading more',
        build: buildBloc,
        seed: () => PlaySessionListLoaded(
          playSessions: [_playSessionListItem],
          total: 2,
          isLoadingMore: true,
        ),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => <PlaySessionState>[],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'keeps the loaded list and surfaces loadMoreError '
        'on DioException (no full-screen PlaySessionError)',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Server error'},
              ),
            ),
          );
        },
        build: buildBloc,
        seed: () => PlaySessionListLoaded(
          playSessions: [_playSessionListItem],
          total: 2,
        ),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => [
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem],
            total: 2,
            loadMoreError: 'Server error',
          ),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'keeps the loaded list and surfaces loadMoreError '
        'on a generic Exception',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('boom'));
        },
        build: buildBloc,
        seed: () => PlaySessionListLoaded(
          playSessions: [_playSessionListItem],
          total: 2,
        ),
        act: (bloc) => bloc.add(const LoadMorePlaySessions()),
        expect: () => [
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          PlaySessionListLoaded(
            playSessions: [_playSessionListItem],
            total: 2,
            loadMoreError: 'Exception: boom',
          ),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadActivePlaySession
    // ---------------------------------------------------------------
    group('LoadActivePlaySession', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, ActivePlaySessionLoaded] '
        'with playSession on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.getActivePlaySession(),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActivePlaySession()),
        expect: () => [
          const PlaySessionLoading(),
          ActivePlaySessionLoaded(playSession: _playSession),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, ActivePlaySessionLoaded] '
        'with null when no active playSession',
        setUp: () {
          when(
            () => mockPlaySessionRepository.getActivePlaySession(),
          ).thenAnswer((_) async => null);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActivePlaySession()),
        expect: () => const [PlaySessionLoading(), ActivePlaySessionLoaded()],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.getActivePlaySession(),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'Internal error'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActivePlaySession()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'Internal error'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // PreviewRecap
    // ---------------------------------------------------------------
    group('PreviewRecap', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, RecapPreviewLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap('lib-001'),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const PreviewRecap(libraryEntryPublicId: 'lib-001')),
        expect: () => [
          const PlaySessionLoading(),
          RecapPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'passes positionOverride to repository',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              'lib-001',
              positionOverride: 'Chapter 3',
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewRecap(
            libraryEntryPublicId: 'lib-001',
            positionOverride: 'Chapter 3',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          RecapPreviewLoaded(preview: _preview),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.previewRecap(
              'lib-001',
              positionOverride: 'Chapter 3',
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              any(),
              positionOverride: any(named: 'positionOverride'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 404,
                data: <String, dynamic>{'detail': 'Entry not found'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const PreviewRecap(libraryEntryPublicId: 'lib-999')),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'Entry not found'),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'deep mode emits [DeepRecapLoading, '
        'RecapPreviewLoaded(isDeep)]',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              'lib-001',
              mode: 'deep',
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewRecap(libraryEntryPublicId: 'lib-001', mode: 'deep'),
        ),
        expect: () => [
          const DeepRecapLoading(),
          RecapPreviewLoaded(preview: _preview, isDeep: true),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.previewRecap(
              'lib-001',
              mode: 'deep',
              cancelToken: any(named: 'cancelToken'),
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'deep cancellation falls back to the quick recap',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              'lib-001',
              mode: 'deep',
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              type: DioExceptionType.cancel,
            ),
          );
          when(
            () => mockPlaySessionRepository.previewRecap('lib-001'),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewRecap(libraryEntryPublicId: 'lib-001', mode: 'deep'),
        ),
        expect: () => [
          const DeepRecapLoading(),
          RecapPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'CancelDeepRecap is a no-op when nothing is in flight',
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const CancelDeepRecap(libraryEntryPublicId: 'lib-001')),
        expect: () => <PlaySessionState>[],
      );
    });

    // ---------------------------------------------------------------
    // StartPlaySession
    // ---------------------------------------------------------------
    group('StartPlaySession', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionStarted] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.startPlaySession('lib-001'),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const StartPlaySession(libraryEntryPublicId: 'lib-001')),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionStarted(playSession: _playSession),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'passes recapText to repository',
        setUp: () {
          when(
            () => mockPlaySessionRepository.startPlaySession(
              'lib-001',
              recapText: 'Custom recap',
            ),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const StartPlaySession(
            libraryEntryPublicId: 'lib-001',
            recapText: 'Custom recap',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionStarted(playSession: _playSession),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.startPlaySession(
              'lib-001',
              recapText: 'Custom recap',
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.startPlaySession(
              any(),
              recapText: any(named: 'recapText'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 409,
                data: <String, dynamic>{'detail': 'PlaySession already active'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const StartPlaySession(libraryEntryPublicId: 'lib-001')),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'PlaySession already active'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitWrapUp
    // ---------------------------------------------------------------
    group('SubmitWrapUp', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionEnded] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.submitWrapUp(
              'playSession-001',
              'Great session!',
            ),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitWrapUp(
            publicId: 'playSession-001',
            wrapUpText: 'Great session!',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionEnded(playSession: _playSession),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.submitWrapUp(any(), any()),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 400,
                data: <String, dynamic>{'detail': 'PlaySession already ended'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitWrapUp(publicId: 'playSession-001', wrapUpText: 'text'),
        ),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'PlaySession already ended'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // EndPlaySession
    // ---------------------------------------------------------------
    group('EndPlaySession', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionEnded] '
        'on success with default endedVia',
        setUp: () {
          when(
            () => mockPlaySessionRepository.endPlaySession(
              'playSession-001',
              endedVia: any(named: 'endedVia'),
            ),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const EndPlaySession(publicId: 'playSession-001')),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionEnded(playSession: _playSession),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'passes custom endedVia to repository',
        setUp: () {
          when(
            () => mockPlaySessionRepository.endPlaySession(
              'playSession-001',
              endedVia: 'user_quit',
            ),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const EndPlaySession(
            publicId: 'playSession-001',
            endedVia: 'user_quit',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionEnded(playSession: _playSession),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.endPlaySession(
              'playSession-001',
              endedVia: 'user_quit',
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.endPlaySession(
              any(),
              endedVia: any(named: 'endedVia'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 404,
                data: <String, dynamic>{'detail': 'PlaySession not found'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const EndPlaySession(publicId: 'playSession-999')),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'PlaySession not found'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitRetroactiveWrapUp
    // ---------------------------------------------------------------
    group('SubmitRetroactiveWrapUp', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, RecapPreviewLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.submitRetroactiveWrapUp(
              'lib-001',
              'Retroactive wrapUp text',
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitRetroactiveWrapUp(
            libraryEntryPublicId: 'lib-001',
            wrapUpText: 'Retroactive wrapUp text',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          RecapPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () =>
                mockPlaySessionRepository.submitRetroactiveWrapUp(any(), any()),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{'detail': 'Invalid wrapUp'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitRetroactiveWrapUp(
            libraryEntryPublicId: 'lib-001',
            wrapUpText: '',
          ),
        ),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'Invalid wrapUp'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // RegenerateRecap
    // ---------------------------------------------------------------
    group('RegenerateRecap', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionStarted] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.regenerateRecap('playSession-001'),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const RegenerateRecap(publicId: 'playSession-001')),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionStarted(playSession: _playSession),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'passes currentPosition to repository',
        setUp: () {
          when(
            () => mockPlaySessionRepository.regenerateRecap(
              'playSession-001',
              currentPosition: 'Boss fight',
            ),
          ).thenAnswer((_) async => _playSession);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RegenerateRecap(
            publicId: 'playSession-001',
            currentPosition: 'Boss fight',
          ),
        ),
        expect: () => [
          const PlaySessionLoading(),
          PlaySessionStarted(playSession: _playSession),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.regenerateRecap(
              'playSession-001',
              currentPosition: 'Boss fight',
            ),
          ).called(1);
        },
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'emits [PlaySessionLoading, PlaySessionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.regenerateRecap(
              any(),
              currentPosition: any(named: 'currentPosition'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: <String, dynamic>{'detail': 'LLM unavailable'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const RegenerateRecap(publicId: 'playSession-001')),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'LLM unavailable'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException paths)', () {
      blocTest<PlaySessionBloc, PlaySessionState>(
        'returns fallback when response is null '
        'and message is null',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'returns e.message when response data '
        'has no detail key',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
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
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'timeout exceeded'),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'returns e.message when response data '
        'is not a Map',
        setUp: () {
          when(
            () => mockPlaySessionRepository.listPlaySessions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(
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
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPlaySessions()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'bad response'),
        ],
      );

      blocTest<PlaySessionBloc, PlaySessionState>(
        'returns fallback when response has null '
        'message and non-map data',
        setUp: () {
          when(
            () => mockPlaySessionRepository.getActivePlaySession(),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 502,
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActivePlaySession()),
        expect: () => const [
          PlaySessionLoading(),
          PlaySessionError(message: 'An unexpected error occurred.'),
        ],
      );
    });
  });
}
