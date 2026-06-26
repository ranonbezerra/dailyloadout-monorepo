import 'package:app/core/library/library_models.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockMissionRepository extends Mock implements MissionRepository {}

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

final _mission = Mission(
  publicId: 'mission-001',
  libraryEntry: _entry,
  missionType: 'new_game',
  startedAt: _now,
  createdAt: _now,
  updatedAt: _now,
  briefingText: 'Welcome back!',
);

final _missionListItem = MissionListItem(
  publicId: 'mission-001',
  libraryEntry: _entry,
  missionType: 'new_game',
  startedAt: _now,
);

final _listResponse = MissionListResponse(items: [_missionListItem], total: 1);

final _preview = BriefingPreview(
  libraryEntry: _entry,
  briefingText: 'Your briefing',
);

// -------------------------------------------------------------------
// Tests
// -------------------------------------------------------------------

void main() {
  late MockMissionRepository mockMissionRepository;

  setUp(() {
    mockMissionRepository = MockMissionRepository();
  });

  MissionBloc buildBloc() =>
      MissionBloc(missionRepository: mockMissionRepository);

  group('MissionBloc', () {
    test('initial state is MissionInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const MissionInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // LoadMissions
    // ---------------------------------------------------------------
    group('LoadMissions', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionListLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => [
          const MissionLoading(),
          MissionListLoaded(missions: [_missionListItem], total: 1),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'passes limit and offset to repository',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(limit: 10, offset: 20),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadMissions(limit: 10, offset: 20)),
        expect: () => [
          const MissionLoading(),
          MissionListLoaded(missions: [_missionListItem], total: 1),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.listMissions(limit: 10, offset: 20),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
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
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Server error'),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Exception: unexpected'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadMoreMissions
    // ---------------------------------------------------------------
    group('LoadMoreMissions', () {
      final page2Item = MissionListItem(
        publicId: 'mission-002',
        libraryEntry: _entry,
        missionType: 'regular',
        startedAt: _now,
      );
      final page2 = MissionListResponse(items: [page2Item], total: 2);

      blocTest<MissionBloc, MissionState>(
        'appends items when current state '
        'is MissionListLoaded with hasMore',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(limit: 10, offset: 1),
          ).thenAnswer((_) async => page2);
        },
        build: buildBloc,
        seed: () => MissionListLoaded(missions: [_missionListItem], total: 2),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => [
          MissionListLoaded(
            missions: [_missionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          MissionListLoaded(missions: [_missionListItem, page2Item], total: 2),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'does nothing when state is not MissionListLoaded',
        build: buildBloc,
        seed: () => const MissionInitial(),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => <MissionState>[],
      );

      blocTest<MissionBloc, MissionState>(
        'does nothing when hasMore is false',
        build: buildBloc,
        seed: () => MissionListLoaded(missions: [_missionListItem], total: 1),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => <MissionState>[],
      );

      blocTest<MissionBloc, MissionState>(
        'does nothing when already loading more',
        build: buildBloc,
        seed: () => MissionListLoaded(
          missions: [_missionListItem],
          total: 2,
          isLoadingMore: true,
        ),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => <MissionState>[],
      );

      blocTest<MissionBloc, MissionState>(
        'keeps the loaded list and surfaces loadMoreError '
        'on DioException (no full-screen MissionError)',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
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
        seed: () => MissionListLoaded(missions: [_missionListItem], total: 2),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => [
          MissionListLoaded(
            missions: [_missionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          MissionListLoaded(
            missions: [_missionListItem],
            total: 2,
            loadMoreError: 'Server error',
          ),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'keeps the loaded list and surfaces loadMoreError '
        'on a generic Exception',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('boom'));
        },
        build: buildBloc,
        seed: () => MissionListLoaded(missions: [_missionListItem], total: 2),
        act: (bloc) => bloc.add(const LoadMoreMissions()),
        expect: () => [
          MissionListLoaded(
            missions: [_missionListItem],
            total: 2,
            isLoadingMore: true,
          ),
          MissionListLoaded(
            missions: [_missionListItem],
            total: 2,
            loadMoreError: 'Exception: boom',
          ),
        ],
      );
    });

    // ---------------------------------------------------------------
    // LoadActiveMission
    // ---------------------------------------------------------------
    group('LoadActiveMission', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, ActiveMissionLoaded] '
        'with mission on success',
        setUp: () {
          when(
            () => mockMissionRepository.getActiveMission(),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActiveMission()),
        expect: () => [
          const MissionLoading(),
          ActiveMissionLoaded(mission: _mission),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, ActiveMissionLoaded] '
        'with null when no active mission',
        setUp: () {
          when(
            () => mockMissionRepository.getActiveMission(),
          ).thenAnswer((_) async => null);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadActiveMission()),
        expect: () => const [MissionLoading(), ActiveMissionLoaded()],
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(() => mockMissionRepository.getActiveMission()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadActiveMission()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Internal error'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // PreviewBriefing
    // ---------------------------------------------------------------
    group('PreviewBriefing', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, BriefingPreviewLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing('lib-001'),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const PreviewBriefing(libraryEntryPublicId: 'lib-001')),
        expect: () => [
          const MissionLoading(),
          BriefingPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'passes positionOverride to repository',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              'lib-001',
              positionOverride: 'Chapter 3',
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewBriefing(
            libraryEntryPublicId: 'lib-001',
            positionOverride: 'Chapter 3',
          ),
        ),
        expect: () => [
          const MissionLoading(),
          BriefingPreviewLoaded(preview: _preview),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.previewBriefing(
              'lib-001',
              positionOverride: 'Chapter 3',
            ),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
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
            bloc.add(const PreviewBriefing(libraryEntryPublicId: 'lib-999')),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Entry not found'),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'deep mode emits [DeepBriefingLoading, '
        'BriefingPreviewLoaded(isDeep)]',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              'lib-001',
              mode: 'deep',
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewBriefing(libraryEntryPublicId: 'lib-001', mode: 'deep'),
        ),
        expect: () => [
          const DeepBriefingLoading(),
          BriefingPreviewLoaded(preview: _preview, isDeep: true),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.previewBriefing(
              'lib-001',
              mode: 'deep',
              cancelToken: any(named: 'cancelToken'),
            ),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'deep cancellation falls back to the quick briefing',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
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
            () => mockMissionRepository.previewBriefing('lib-001'),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const PreviewBriefing(libraryEntryPublicId: 'lib-001', mode: 'deep'),
        ),
        expect: () => [
          const DeepBriefingLoading(),
          BriefingPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'CancelDeepBriefing is a no-op when nothing is in flight',
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const CancelDeepBriefing(libraryEntryPublicId: 'lib-001')),
        expect: () => <MissionState>[],
      );
    });

    // ---------------------------------------------------------------
    // StartMission
    // ---------------------------------------------------------------
    group('StartMission', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionStarted] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.startMission('lib-001'),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const StartMission(libraryEntryPublicId: 'lib-001')),
        expect: () => [
          const MissionLoading(),
          MissionStarted(mission: _mission),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'passes briefingText to repository',
        setUp: () {
          when(
            () => mockMissionRepository.startMission(
              'lib-001',
              briefingText: 'Custom briefing',
            ),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const StartMission(
            libraryEntryPublicId: 'lib-001',
            briefingText: 'Custom briefing',
          ),
        ),
        expect: () => [
          const MissionLoading(),
          MissionStarted(mission: _mission),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.startMission(
              'lib-001',
              briefingText: 'Custom briefing',
            ),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.startMission(
              any(),
              briefingText: any(named: 'briefingText'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 409,
                data: <String, dynamic>{'detail': 'Mission already active'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const StartMission(libraryEntryPublicId: 'lib-001')),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Mission already active'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitDebrief
    // ---------------------------------------------------------------
    group('SubmitDebrief', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionEnded] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.submitDebrief(
              'mission-001',
              'Great session!',
            ),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitDebrief(
            publicId: 'mission-001',
            debriefText: 'Great session!',
          ),
        ),
        expect: () => [const MissionLoading(), MissionEnded(mission: _mission)],
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.submitDebrief(any(), any()),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 400,
                data: <String, dynamic>{'detail': 'Mission already ended'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitDebrief(publicId: 'mission-001', debriefText: 'text'),
        ),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Mission already ended'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // EndMission
    // ---------------------------------------------------------------
    group('EndMission', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionEnded] '
        'on success with default endedVia',
        setUp: () {
          when(
            () => mockMissionRepository.endMission(
              'mission-001',
              endedVia: any(named: 'endedVia'),
            ),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const EndMission(publicId: 'mission-001')),
        expect: () => [const MissionLoading(), MissionEnded(mission: _mission)],
      );

      blocTest<MissionBloc, MissionState>(
        'passes custom endedVia to repository',
        setUp: () {
          when(
            () => mockMissionRepository.endMission(
              'mission-001',
              endedVia: 'user_quit',
            ),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const EndMission(publicId: 'mission-001', endedVia: 'user_quit'),
        ),
        expect: () => [const MissionLoading(), MissionEnded(mission: _mission)],
        verify: (_) {
          verify(
            () => mockMissionRepository.endMission(
              'mission-001',
              endedVia: 'user_quit',
            ),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.endMission(
              any(),
              endedVia: any(named: 'endedVia'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 404,
                data: <String, dynamic>{'detail': 'Mission not found'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const EndMission(publicId: 'mission-999')),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Mission not found'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitRetroactiveDebrief
    // ---------------------------------------------------------------
    group('SubmitRetroactiveDebrief', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, BriefingPreviewLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.submitRetroactiveDebrief(
              'lib-001',
              'Retroactive debrief text',
            ),
          ).thenAnswer((_) async => _preview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitRetroactiveDebrief(
            libraryEntryPublicId: 'lib-001',
            debriefText: 'Retroactive debrief text',
          ),
        ),
        expect: () => [
          const MissionLoading(),
          BriefingPreviewLoaded(preview: _preview),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.submitRetroactiveDebrief(any(), any()),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{'detail': 'Invalid debrief'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitRetroactiveDebrief(
            libraryEntryPublicId: 'lib-001',
            debriefText: '',
          ),
        ),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'Invalid debrief'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // RegenerateBriefing
    // ---------------------------------------------------------------
    group('RegenerateBriefing', () {
      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionStarted] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.regenerateBriefing('mission-001'),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const RegenerateBriefing(publicId: 'mission-001')),
        expect: () => [
          const MissionLoading(),
          MissionStarted(mission: _mission),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'passes currentPosition to repository',
        setUp: () {
          when(
            () => mockMissionRepository.regenerateBriefing(
              'mission-001',
              currentPosition: 'Boss fight',
            ),
          ).thenAnswer((_) async => _mission);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RegenerateBriefing(
            publicId: 'mission-001',
            currentPosition: 'Boss fight',
          ),
        ),
        expect: () => [
          const MissionLoading(),
          MissionStarted(mission: _mission),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.regenerateBriefing(
              'mission-001',
              currentPosition: 'Boss fight',
            ),
          ).called(1);
        },
      );

      blocTest<MissionBloc, MissionState>(
        'emits [MissionLoading, MissionError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.regenerateBriefing(
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
            bloc.add(const RegenerateBriefing(publicId: 'mission-001')),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'LLM unavailable'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException paths)', () {
      blocTest<MissionBloc, MissionState>(
        'returns fallback when response is null '
        'and message is null',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'returns e.message when response data '
        'has no detail key',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
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
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'timeout exceeded'),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'returns e.message when response data '
        'is not a Map',
        setUp: () {
          when(
            () => mockMissionRepository.listMissions(
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
        act: (bloc) => bloc.add(const LoadMissions()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'bad response'),
        ],
      );

      blocTest<MissionBloc, MissionState>(
        'returns fallback when response has null '
        'message and non-map data',
        setUp: () {
          when(() => mockMissionRepository.getActiveMission()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadActiveMission()),
        expect: () => const [
          MissionLoading(),
          MissionError(message: 'An unexpected error occurred.'),
        ],
      );
    });
  });
}
