import 'package:app/core/library/library_models.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/core/pick/pick_repository.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockPickRepository extends Mock implements PickRepository {}

class MockPlaySessionRepository extends Mock implements PlaySessionRepository {}

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

final _pick = Pick(
  publicId: 'pick-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
  updatedAt: _now,
);

final _pickListItem = PickListItem(
  publicId: 'pick-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
);

final _listResponse = PickListResponse(items: [_pickListItem], total: 1);

final _recapPreview = RecapPreview(
  libraryEntry: _entry,
  recapText: 'Continue toward the Erdtree.',
);

// -----------------------------------------------------------------
// Tests
// -----------------------------------------------------------------

void main() {
  late MockPickRepository mockPickRepository;
  late MockPlaySessionRepository mockPlaySessionRepository;

  setUp(() {
    mockPickRepository = MockPickRepository();
    mockPlaySessionRepository = MockPlaySessionRepository();
  });

  PickBloc buildBloc() => PickBloc(
    pickRepository: mockPickRepository,
    playSessionRepository: mockPlaySessionRepository,
  );

  group('PickBloc', () {
    test('initial state is PickInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const PickInitial());
      bloc.close();
    });

    // -------------------------------------------------------------
    // CreatePick
    // -------------------------------------------------------------
    group('CreatePick', () {
      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickResultsLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockPickRepository.createPick(
              mood: any(named: 'mood'),
              availableMinutes: any(named: 'availableMinutes'),
              mentalEnergy: any(named: 'mentalEnergy'),
              count: any(named: 'count'),
              context: any(named: 'context'),
            ),
          ).thenAnswer((_) async => [_pick]);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreatePick(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => [
          const PickLoading(),
          PickResultsLoaded(results: [_pick]),
        ],
      );

      blocTest<PickBloc, PickState>(
        'passes all parameters to repository',
        setUp: () {
          when(
            () => mockPickRepository.createPick(
              mood: 'focused',
              availableMinutes: 120,
              mentalEnergy: 'high',
              count: 3,
              context: 'Want a challenge',
            ),
          ).thenAnswer((_) async => [_pick]);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const CreatePick(
            mood: 'focused',
            availableMinutes: 120,
            mentalEnergy: 'high',
            count: 3,
            context: 'Want a challenge',
          ),
        ),
        expect: () => [
          const PickLoading(),
          PickResultsLoaded(results: [_pick]),
        ],
        verify: (_) {
          verify(
            () => mockPickRepository.createPick(
              mood: 'focused',
              availableMinutes: 120,
              mentalEnergy: 'high',
              count: 3,
              context: 'Want a challenge',
            ),
          ).called(1);
        },
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPickRepository.createPick(
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
          const CreatePick(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => const [
          PickLoading(),
          PickError(message: 'LLM unavailable'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockPickRepository.createPick(
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
          const CreatePick(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Exception: unexpected'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'surfaces the verify-email prompt on a 403 "Email not verified"',
        setUp: () {
          when(
            () => mockPickRepository.createPick(
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
          const CreatePick(
            mood: 'chill',
            availableMinutes: 60,
            mentalEnergy: 'medium',
          ),
        ),
        expect: () => [
          const PickLoading(),
          isA<PickError>().having(
            (e) => e.message,
            'message',
            contains('Verify your email'),
          ),
        ],
      );
    });

    // -------------------------------------------------------------
    // AcceptPick
    // -------------------------------------------------------------
    group('AcceptPick', () {
      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickAccepted] '
        'on success',
        setUp: () {
          when(
            () => mockPickRepository.acceptPick(
              'pick-001',
              recapText: any(named: 'recapText'),
            ),
          ).thenAnswer((_) async => _pick);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptPick(publicId: 'pick-001')),
        expect: () => [const PickLoading(), PickAccepted(pick: _pick)],
        verify: (_) {
          final captured = verify(
            () => mockPickRepository.acceptPick(
              'pick-001',
              recapText: captureAny(named: 'recapText'),
            ),
          ).captured;
          expect(captured.single, isNull);
        },
      );

      blocTest<PickBloc, PickState>(
        'forwards recapText to repository when provided',
        setUp: () {
          when(
            () => mockPickRepository.acceptPick(
              any(),
              recapText: any(named: 'recapText'),
            ),
          ).thenAnswer((_) async => _pick);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const AcceptPick(
            publicId: 'pick-001',
            recapText: 'Beware the boss ahead.',
          ),
        ),
        expect: () => [const PickLoading(), PickAccepted(pick: _pick)],
        verify: (_) {
          verify(
            () => mockPickRepository.acceptPick(
              'pick-001',
              recapText: 'Beware the boss ahead.',
            ),
          ).called(1);
        },
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPickRepository.acceptPick(
              any(),
              recapText: any(named: 'recapText'),
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
        act: (bloc) => bloc.add(const AcceptPick(publicId: 'pick-001')),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Already accepted'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockPickRepository.acceptPick(
              any(),
              recapText: any(named: 'recapText'),
            ),
          ).thenThrow(Exception('network down'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const AcceptPick(publicId: 'pick-001')),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Exception: network down'),
        ],
      );
    });

    // -------------------------------------------------------------
    // GeneratePickRecap
    // -------------------------------------------------------------
    group('GeneratePickRecap', () {
      blocTest<PickBloc, PickState>(
        'emits [PickRecapLoading, PickRecapReady] '
        'on success',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => _recapPreview);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          PickRecapLoading(publicId: 'pick-001'),
          PickRecapReady(
            publicId: 'pick-001',
            recapText: 'Continue toward the Erdtree.',
          ),
        ],
        verify: (_) {
          verify(
            () => mockPlaySessionRepository.previewRecap('lib-001'),
          ).called(1);
        },
      );

      blocTest<PickBloc, PickState>(
        'emits empty recap text when preview has none',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenAnswer((_) async => RecapPreview(libraryEntry: _entry));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          PickRecapLoading(publicId: 'pick-001'),
          PickRecapReady(publicId: 'pick-001', recapText: ''),
        ],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickRecapLoading, PickError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
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
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          PickRecapLoading(publicId: 'pick-001'),
          PickError(message: 'LLM unavailable'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickRecapLoading, PickError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockPlaySessionRepository.previewRecap(
              any(),
              positionOverride: any(named: 'positionOverride'),
              mode: any(named: 'mode'),
              cancelToken: any(named: 'cancelToken'),
            ),
          ).thenThrow(Exception('boom'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const GeneratePickRecap(
            publicId: 'pick-001',
            libraryEntryPublicId: 'lib-001',
          ),
        ),
        expect: () => const [
          PickRecapLoading(publicId: 'pick-001'),
          PickError(message: 'Exception: boom'),
        ],
      );
    });

    // -------------------------------------------------------------
    // RejectPick
    // -------------------------------------------------------------
    group('RejectPick', () {
      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickRejected] '
        'on success',
        setUp: () {
          when(
            () => mockPickRepository.rejectPick('pick-001'),
          ).thenAnswer((_) async => _pick);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RejectPick(publicId: 'pick-001')),
        expect: () => [const PickLoading(), PickRejected(pick: _pick)],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on DioException',
        setUp: () {
          when(() => mockPickRepository.rejectPick(any())).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 404,
                data: <String, dynamic>{'detail': 'Pick not found'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const RejectPick(publicId: 'pick-999')),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Pick not found'),
        ],
      );
    });

    // -------------------------------------------------------------
    // LoadPicks
    // -------------------------------------------------------------
    group('LoadPicks', () {
      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickListLoaded] '
        'on success',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => [
          const PickLoading(),
          PickListLoaded(picks: [_pickListItem], total: 1),
        ],
      );

      blocTest<PickBloc, PickState>(
        'passes limit and offset to repository',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(limit: 10, offset: 20),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPicks(limit: 10, offset: 20)),
        expect: () => [
          const PickLoading(),
          PickListLoaded(picks: [_pickListItem], total: 1),
        ],
        verify: (_) {
          verify(
            () => mockPickRepository.listPicks(limit: 10, offset: 20),
          ).called(1);
        },
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on DioException',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
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
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => const [PickLoading(), PickError(message: 'Server error')],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on generic Exception',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Exception: unexpected'),
        ],
      );
    });

    // -------------------------------------------------------------
    // LoadLatestPick
    // -------------------------------------------------------------
    group('LoadLatestPick', () {
      blocTest<PickBloc, PickState>(
        'emits [PickLoading, LatestPickLoaded] '
        'with pick on success',
        setUp: () {
          when(
            () => mockPickRepository.getLatestPick(),
          ).thenAnswer((_) async => _pick);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLatestPick()),
        expect: () => [const PickLoading(), LatestPickLoaded(pick: _pick)],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, LatestPickLoaded] '
        'with null when no pending pick',
        setUp: () {
          when(
            () => mockPickRepository.getLatestPick(),
          ).thenAnswer((_) async => null);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLatestPick()),
        expect: () => const [PickLoading(), LatestPickLoaded()],
      );

      blocTest<PickBloc, PickState>(
        'emits [PickLoading, PickError] '
        'on DioException',
        setUp: () {
          when(() => mockPickRepository.getLatestPick()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadLatestPick()),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Internal error'),
        ],
      );
    });

    // -------------------------------------------------------------
    // _extractErrorMessage coverage
    // -------------------------------------------------------------
    group('_extractErrorMessage '
        '(via DioException paths)', () {
      blocTest<PickBloc, PickState>(
        'returns fallback when response is null '
        'and message is null',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => const [
          PickLoading(),
          PickError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'returns e.message when response data '
        'has no detail key',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
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
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => const [
          PickLoading(),
          PickError(message: 'timeout exceeded'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'returns e.message when response data '
        'is not a Map',
        setUp: () {
          when(
            () => mockPickRepository.listPicks(
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
        act: (bloc) => bloc.add(const LoadPicks()),
        expect: () => const [PickLoading(), PickError(message: 'bad response')],
      );

      blocTest<PickBloc, PickState>(
        'returns fallback when response has '
        'null message and non-map data',
        setUp: () {
          when(() => mockPickRepository.getLatestPick()).thenThrow(
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
        act: (bloc) => bloc.add(const LoadLatestPick()),
        expect: () => const [
          PickLoading(),
          PickError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'returns detail when response data '
        'detail is a String',
        setUp: () {
          when(
            () => mockPickRepository.acceptPick(
              any(),
              recapText: any(named: 'recapText'),
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
        act: (bloc) => bloc.add(const AcceptPick(publicId: 'pick-001')),
        expect: () => const [
          PickLoading(),
          PickError(message: 'Validation failed'),
        ],
      );

      blocTest<PickBloc, PickState>(
        'falls through when detail is not '
        'a String',
        setUp: () {
          when(() => mockPickRepository.rejectPick(any())).thenThrow(
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
        act: (bloc) => bloc.add(const RejectPick(publicId: 'pick-001')),
        expect: () => const [PickLoading(), PickError(message: 'fallback msg')],
      );
    });
  });
}
