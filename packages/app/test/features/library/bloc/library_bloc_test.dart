import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

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
  status: 'backlog',
  createdAt: _now,
  updatedAt: _now,
);

final _listResponse = LibraryListResponse(
  items: [_entry],
  total: 3,
  limit: 50,
  offset: 0,
);

final _listResponseNoMore = LibraryListResponse(
  items: [_entry],
  total: 1,
  limit: 50,
  offset: 0,
);

const _emptyListResponse = LibraryListResponse(
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockLibraryRepository mockLibraryRepository;

  setUp(() {
    mockLibraryRepository = MockLibraryRepository();
  });

  LibraryBloc buildBloc() =>
      LibraryBloc(libraryRepository: mockLibraryRepository);

  group('LibraryBloc', () {
    test('initial state is LibraryInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const LibraryInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // LoadLibrary
    // ---------------------------------------------------------------
    group('LoadLibrary', () {
      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryLoaded] with hasMore=true '
        'when offset + items < total',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(),
          ).thenAnswer((_) async => _listResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => [
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 3, hasMore: true),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryLoaded] with hasMore=false '
        'when offset + items >= total',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(),
          ).thenAnswer((_) async => _listResponseNoMore);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => [
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 1, hasMore: false),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'passes status filter to repository',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(status: 'playing'),
          ).thenAnswer((_) async => _emptyListResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLibrary(status: 'playing')),
        expect: () => const [
          LibraryLoading(),
          LibraryLoaded(entries: [], total: 0, hasMore: false),
        ],
        verify: (_) {
          verify(
            () => mockLibraryRepository.listLibrary(status: 'playing'),
          ).called(1);
        },
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryError] on DioException',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(
              status: any(named: 'status'),
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
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'Server error'),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryError] on generic Exception',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(
              status: any(named: 'status'),
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'Exception: unexpected'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // AddEntry
    // ---------------------------------------------------------------
    group('AddEntry', () {
      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryLoaded] on success (reloads)',
        setUp: () {
          when(
            () => mockLibraryRepository.addToLibrary(
              gamePublicId: 'game-001',
              platformId: 1,
            ),
          ).thenAnswer((_) async => _entry);
          // Reload call
          when(
            () => mockLibraryRepository.listLibrary(),
          ).thenAnswer((_) async => _listResponseNoMore);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const AddEntry(gamePublicId: 'game-001', platformId: 1)),
        expect: () => [
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 1, hasMore: false),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryError] on DioException',
        setUp: () {
          when(
            () => mockLibraryRepository.addToLibrary(
              gamePublicId: any(named: 'gamePublicId'),
              platformId: any(named: 'platformId'),
              status: any(named: 'status'),
              notes: any(named: 'notes'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 409,
                data: <String, dynamic>{'detail': 'Already in library'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const AddEntry(gamePublicId: 'game-001', platformId: 1)),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'Already in library'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // UpdateEntry
    // ---------------------------------------------------------------
    group('UpdateEntry', () {
      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryLoaded] on success (reloads)',
        setUp: () {
          when(
            () =>
                mockLibraryRepository.updateEntry('lib-001', status: 'playing'),
          ).thenAnswer((_) async => _entry);
          when(
            () => mockLibraryRepository.listLibrary(),
          ).thenAnswer((_) async => _listResponseNoMore);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const UpdateEntry(publicId: 'lib-001', status: 'playing')),
        expect: () => [
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 1, hasMore: false),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryError] on DioException',
        setUp: () {
          when(
            () => mockLibraryRepository.updateEntry(
              any(),
              status: any(named: 'status'),
              notes: any(named: 'notes'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'Not found',
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const UpdateEntry(publicId: 'lib-999')),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'Not found'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // DeleteEntry
    // ---------------------------------------------------------------
    group('DeleteEntry', () {
      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryLoaded] on success (reloads)',
        setUp: () {
          when(
            () => mockLibraryRepository.deleteEntry('lib-001'),
          ).thenAnswer((_) async {});
          when(
            () => mockLibraryRepository.listLibrary(),
          ).thenAnswer((_) async => _emptyListResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const DeleteEntry(publicId: 'lib-001')),
        expect: () => const [
          LibraryLoading(),
          LibraryLoaded(entries: [], total: 0, hasMore: false),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'emits [LibraryLoading, LibraryError] on DioException',
        setUp: () {
          when(() => mockLibraryRepository.deleteEntry(any())).thenThrow(
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
        act: (bloc) => bloc.add(const DeleteEntry(publicId: 'lib-999')),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'Entry not found'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SearchGames
    // ---------------------------------------------------------------
    group('SearchGames', () {
      blocTest<LibraryBloc, LibraryState>(
        'does not emit new states (handled at UI level)',
        build: buildBloc,
        act: (bloc) => bloc.add(const SearchGames(query: 'zelda')),
        expect: () => const <LibraryState>[],
      );
    });

    // ---------------------------------------------------------------
    // CreateGame
    // ---------------------------------------------------------------
    group('CreateGame', () {
      blocTest<LibraryBloc, LibraryState>(
        'does not emit new states (handled at UI level)',
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const CreateGame(slug: 'new-game', title: 'New Game')),
        expect: () => const <LibraryState>[],
      );
    });

    // ---------------------------------------------------------------
    // _currentStatusFilter remembered across reload
    // ---------------------------------------------------------------
    group('_currentStatusFilter persistence', () {
      blocTest<LibraryBloc, LibraryState>(
        'AddEntry reloads with the status filter set by prior LoadLibrary',
        setUp: () {
          // Stub all listLibrary calls with any parameters.
          when(
            () => mockLibraryRepository.listLibrary(
              status: any(named: 'status'),
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenAnswer((_) async => _listResponseNoMore);
          // AddEntry mutation call.
          when(
            () => mockLibraryRepository.addToLibrary(
              gamePublicId: 'game-002',
              platformId: 1,
              status: 'playing',
            ),
          ).thenAnswer((_) async => _entry);
        },
        build: buildBloc,
        act: (bloc) async {
          bloc.add(const LoadLibrary(status: 'playing'));
          await Future<void>.delayed(Duration.zero);
          bloc.add(
            const AddEntry(
              gamePublicId: 'game-002',
              platformId: 1,
              status: 'playing',
            ),
          );
        },
        expect: () => [
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 1, hasMore: false),
          const LibraryLoading(),
          LibraryLoaded(entries: [_entry], total: 1, hasMore: false),
        ],
        verify: (_) {
          // listLibrary was called twice: once for LoadLibrary and once
          // for the _reload after AddEntry. Both should use 'playing'.
          final captured = verify(
            () => mockLibraryRepository.listLibrary(
              status: captureAny(named: 'status'),
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).captured;

          // Both calls used the remembered 'playing' status filter.
          expect(captured, equals(['playing', 'playing']));

          // Critically, listLibrary was never called with null status,
          // proving the filter was remembered after LoadLibrary.
          verifyNever(
            () => mockLibraryRepository.listLibrary(
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          );
        },
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException paths)', () {
      blocTest<LibraryBloc, LibraryState>(
        'returns fallback when response is null and message is null',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(
              status: any(named: 'status'),
              limit: any(named: 'limit'),
              offset: any(named: 'offset'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<LibraryBloc, LibraryState>(
        'returns e.message when response data has no detail key',
        setUp: () {
          when(
            () => mockLibraryRepository.listLibrary(
              status: any(named: 'status'),
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
        act: (bloc) => bloc.add(const LoadLibrary()),
        expect: () => const [
          LibraryLoading(),
          LibraryError(message: 'timeout exceeded'),
        ],
      );
    });
  });
}
