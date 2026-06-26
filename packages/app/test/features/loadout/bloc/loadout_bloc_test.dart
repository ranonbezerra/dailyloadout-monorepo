import 'package:app/core/library/library_models.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLoadoutRepository extends Mock implements LoadoutRepository {}

class MockMissionRepository extends Mock implements MissionRepository {}

// -----------------------------------------------------------------
// Test fixtures
// -----------------------------------------------------------------

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

final _loadout = Loadout(
  publicId: 'loadout-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
  updatedAt: _now,
);

final _loadoutListItem = LoadoutListItem(
  publicId: 'loadout-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
);

final _listResponse = LoadoutListResponse(items: [_loadoutListItem], total: 1);

final _briefingPreview = BriefingPreview(
  libraryEntry: _entry,
  briefingText: 'Continue toward the Erdtree.',
);

// -----------------------------------------------------------------
// Tests
// -----------------------------------------------------------------

void main() {
  late MockLoadoutRepository mockLoadoutRepository;
  late MockMissionRepository mockMissionRepository;

  setUp(() {
    mockLoadoutRepository = MockLoadoutRepository();
    mockMissionRepository = MockMissionRepository();
  });

  LoadoutBloc buildBloc() => LoadoutBloc(
    loadoutRepository: mockLoadoutRepository,
    missionRepository: mockMissionRepository,
  );

  group('LoadoutBloc', () {
    test('initial state is LoadoutInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const LoadoutInitial());
      bloc.close();
    });

    // -------------------------------------------------------------
    // CreateLoadout
    // -------------------------------------------------------------
    group('CreateLoadout', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutResultsLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockLoadoutRepository.createLoadout(
              mood: any(named: 'mood'),
              availableMinutes: any(named: 'availableMinutes'),
              mentalEnergy: any(named: 'mentalEnergy'),
              count: any(named: 'count'),
              context: any(named: 'context'),
            ),
          ).thenAnswer((_) async => [_loadout]);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreateLoadout(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => [
          const LoadoutLoading(),
          LoadoutResultsLoaded(results: [_loadout]),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'passes all parameters to repository',
        setUp: () {
          when(
            () => mockLoadoutRepository.createLoadout(
              mood: 'focused',
              availableMinutes: 120,
              mentalEnergy: 'high',
              count: 3,
              context: 'Want a challenge',
            ),
          ).thenAnswer((_) async => [_loadout]);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreateLoadout(
            mood: 'focused',
            availableMinutes: 120,
            mentalEnergy: 'high',
            count: 3,
            context: 'Want a challenge',
          ),
        ),
        expect: () => [
          const LoadoutLoading(),
          LoadoutResultsLoaded(results: [_loadout]),
        ],
        verify: (_) {
          verify(
            () => mockLoadoutRepository.createLoadout(
              mood: 'focused',
              availableMinutes: 120,
              mentalEnergy: 'high',
              count: 3,
              context: 'Want a challenge',
            ),
          ).called(1);
        },
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(
            () => mockLoadoutRepository.createLoadout(
              mood: any(named: 'mood'),
              availableMinutes: any(named: 'availableMinutes'),
              mentalEnergy: any(named: 'mentalEnergy'),
              count: any(named: 'count'),
              context: any(named: 'context'),
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
        act: (bloc) => bloc.add(
          const CreateLoadout(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'LLM unavailable'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockLoadoutRepository.createLoadout(
              mood: any(named: 'mood'),
              availableMinutes: any(named: 'availableMinutes'),
              mentalEnergy: any(named: 'mentalEnergy'),
              count: any(named: 'count'),
              context: any(named: 'context'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreateLoadout(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Exception: unexpected'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'surfaces the verify-email prompt on a 403 "Email not verified"',
        setUp: () {
          when(
            () => mockLoadoutRepository.createLoadout(
              mood: any(named: 'mood'),
              availableMinutes: any(named: 'availableMinutes'),
              mentalEnergy: any(named: 'mentalEnergy'),
              count: any(named: 'count'),
              context: any(named: 'context'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 403,
                data: <String, dynamic>{'detail': 'Email not verified'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreateLoadout(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => [
          const LoadoutLoading(),
          isA<LoadoutError>().having(
            (e) => e.message,
            'message',
            contains('Verify your email'),
          ),
        ],
      );
    });

    // -------------------------------------------------------------
    // AcceptLoadout
    // -------------------------------------------------------------
    group('AcceptLoadout', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutAccepted] '
        'on success',
        setUp: () {
          when(
            () => mockLoadoutRepository.acceptLoadout(
              'loadout-001',
              briefingText: any(named: 'briefingText'),
            ),
          ).thenAnswer((_) async => _loadout);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptLoadout(publicId: 'loadout-001')),
        expect: () => [
          const LoadoutLoading(),
          LoadoutAccepted(loadout: _loadout),
        ],
        verify: (_) {
          final captured = verify(
            () => mockLoadoutRepository.acceptLoadout(
              'loadout-001',
              briefingText: captureAny(named: 'briefingText'),
            ),
          ).captured;
          expect(captured.single, isNull);
        },
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'forwards briefingText to repository when provided',
        setUp: () {
          when(
            () => mockLoadoutRepository.acceptLoadout(
              any(),
              briefingText: any(named: 'briefingText'),
            ),
          ).thenAnswer((_) async => _loadout);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const AcceptLoadout(
            publicId: 'loadout-001',
            briefingText: 'Beware the boss ahead.',
          ),
        ),
        expect: () => [
          const LoadoutLoading(),
          LoadoutAccepted(loadout: _loadout),
        ],
        verify: (_) {
          verify(
            () => mockLoadoutRepository.acceptLoadout(
              'loadout-001',
              briefingText: 'Beware the boss ahead.',
            ),
          ).called(1);
        },
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(
            () => mockLoadoutRepository.acceptLoadout(
              any(),
              briefingText: any(named: 'briefingText'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 409,
                data: <String, dynamic>{'detail': 'Already accepted'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptLoadout(publicId: 'loadout-001')),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Already accepted'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockLoadoutRepository.acceptLoadout(
              any(),
              briefingText: any(named: 'briefingText'),
            ),
          ).thenThrow(Exception('network down'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptLoadout(publicId: 'loadout-001')),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Exception: network down'),
        ],
      );
    });

    // -------------------------------------------------------------
    // GenerateLoadoutBriefing
    // -------------------------------------------------------------
    group('GenerateLoadoutBriefing', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutBriefingLoading, LoadoutBriefingReady] '
        'on success',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => _briefingPreview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          LoadoutBriefingLoading(publicId: 'loadout-001'),
          LoadoutBriefingReady(
            publicId: 'loadout-001',
            briefingText: 'Continue toward the Erdtree.',
          ),
        ],
        verify: (_) {
          verify(
            () => mockMissionRepository.previewBriefing('lib-001'),
          ).called(1);
        },
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits empty briefing text when preview has none',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => BriefingPreview(libraryEntry: _entry));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          LoadoutBriefingLoading(publicId: 'loadout-001'),
          LoadoutBriefingReady(publicId: 'loadout-001', briefingText: ''),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutBriefingLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
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
        act: (bloc) => bloc.add(
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          LoadoutBriefingLoading(publicId: 'loadout-001'),
          LoadoutError(message: 'LLM unavailable'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutBriefingLoading, LoadoutError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockMissionRepository.previewBriefing(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenThrow(Exception('boom'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GenerateLoadoutBriefing(
            publicId: 'loadout-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          LoadoutBriefingLoading(publicId: 'loadout-001'),
          LoadoutError(message: 'Exception: boom'),
        ],
      );
    });

    // -------------------------------------------------------------
    // RejectLoadout
    // -------------------------------------------------------------
    group('RejectLoadout', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutRejected] '
        'on success',
        setUp: () {
          when(
            () => mockLoadoutRepository.rejectLoadout('loadout-001'),
          ).thenAnswer((_) async => _loadout);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RejectLoadout(publicId: 'loadout-001')),
        expect: () => [
          const LoadoutLoading(),
          LoadoutRejected(loadout: _loadout),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(() => mockLoadoutRepository.rejectLoadout(any())).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 404,
                data: <String, dynamic>{'detail': 'Loadout not found'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RejectLoadout(publicId: 'loadout-999')),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Loadout not found'),
        ],
      );
    });

    // -------------------------------------------------------------
    // LoadLoadouts
    // -------------------------------------------------------------
    group('LoadLoadouts', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutListLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => [
          const LoadoutLoading(),
          LoadoutListLoaded(loadouts: [_loadoutListItem], total: 1),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'passes limit and offset to repository',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(limit: 10, offset: 20),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLoadouts(limit: 10, offset: 20)),
        expect: () => [
          const LoadoutLoading(),
          LoadoutListLoaded(loadouts: [_loadoutListItem], total: 1),
        ],
        verify: (_) {
          verify(
            () => mockLoadoutRepository.listLoadouts(limit: 10, offset: 20),
          ).called(1);
        },
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
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
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Server error'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Exception: unexpected'),
        ],
      );
    });

    // -------------------------------------------------------------
    // LoadLatestLoadout
    // -------------------------------------------------------------
    group('LoadLatestLoadout', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LatestLoadoutLoaded] '
        'with loadout on success',
        setUp: () {
          when(
            () => mockLoadoutRepository.getLatestLoadout(),
          ).thenAnswer((_) async => _loadout);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLatestLoadout()),
        expect: () => [
          const LoadoutLoading(),
          LatestLoadoutLoaded(loadout: _loadout),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LatestLoadoutLoaded] '
        'with null when no pending loadout',
        setUp: () {
          when(
            () => mockLoadoutRepository.getLatestLoadout(),
          ).thenAnswer((_) async => null);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLatestLoadout()),
        expect: () => const [LoadoutLoading(), LatestLoadoutLoaded()],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'emits [LoadoutLoading, LoadoutError] '
        'on DioException',
        setUp: () {
          when(() => mockLoadoutRepository.getLatestLoadout()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadLatestLoadout()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Internal error'),
        ],
      );
    });

    // -------------------------------------------------------------
    // _extractErrorMessage coverage
    // -------------------------------------------------------------
    group('_extractErrorMessage '
        '(via DioException paths)', () {
      blocTest<LoadoutBloc, LoadoutState>(
        'returns fallback when response is null '
        'and message is null',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'returns e.message when response data '
        'has no detail key',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
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
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'timeout exceeded'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'returns e.message when response data '
        'is not a Map',
        setUp: () {
          when(
            () => mockLoadoutRepository.listLoadouts(
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
        act: (bloc) => bloc.add(const LoadLoadouts()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'bad response'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'returns fallback when response has '
        'null message and non-map data',
        setUp: () {
          when(() => mockLoadoutRepository.getLatestLoadout()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadLatestLoadout()),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'returns detail when response data '
        'detail is a String',
        setUp: () {
          when(
            () => mockLoadoutRepository.acceptLoadout(
              any(),
              briefingText: any(named: 'briefingText'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'should be ignored',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{'detail': 'Validation failed'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptLoadout(publicId: 'loadout-001')),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'Validation failed'),
        ],
      );

      blocTest<LoadoutBloc, LoadoutState>(
        'falls through when detail is not '
        'a String',
        setUp: () {
          when(() => mockLoadoutRepository.rejectLoadout(any())).thenThrow(
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
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RejectLoadout(publicId: 'loadout-001')),
        expect: () => const [
          LoadoutLoading(),
          LoadoutError(message: 'fallback msg'),
        ],
      );
    });
  });
}
