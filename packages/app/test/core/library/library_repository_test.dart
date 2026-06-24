import 'package:app/core/api/api_client.dart';
import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

Map<String, dynamic> _platformJson() => <String, dynamic>{
  'id': 48,
  'slug': 'ps5',
  'label': 'PlayStation 5',
  'family': 'PlayStation',
};

Map<String, dynamic> _gameJson({String publicId = 'game-001'}) =>
    <String, dynamic>{
      'public_id': publicId,
      'slug': 'elden-ring',
      'title': 'Elden Ring',
      'metadata_source': 'igdb',
      'created_at': '2025-01-01T00:00:00Z',
    };

Map<String, dynamic> _libraryEntryJson({String publicId = 'entry-001'}) =>
    <String, dynamic>{
      'public_id': publicId,
      'game': _gameJson(),
      'platform': _platformJson(),
      'status': 'playing',
      'created_at': '2025-01-01T00:00:00Z',
      'updated_at': '2025-01-01T00:00:00Z',
    };

Response<T> _response<T>(String path, T data) => Response<T>(
  requestOptions: RequestOptions(path: path),
  data: data,
);

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late LibraryRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = LibraryRepository(apiClient: apiClient);
  });

  group('listPlatforms', () {
    test('parses list of platforms', () async {
      when(() => dio.get<List<dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/platforms', <dynamic>[_platformJson()]),
      );

      final platforms = await repository.listPlatforms();

      expect(platforms, hasLength(1));
      expect(platforms.first, isA<Platform>());
      expect(platforms.first.slug, 'ps5');
      verify(() => dio.get<List<dynamic>>('/v1/platforms')).called(1);
    });

    test('rethrows DioException', () async {
      when(() => dio.get<List<dynamic>>(any())).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/v1/platforms')),
      );

      expect(repository.listPlatforms, throwsA(isA<DioException>()));
    });
  });

  group('searchGames', () {
    test('passes query params and parses games', () async {
      when(
        () => dio.get<List<dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/games/search', <dynamic>[_gameJson()]),
      );

      final games = await repository.searchGames('elden', limit: 5);

      expect(games, hasLength(1));
      expect(games.first.title, 'Elden Ring');
      final captured = verify(
        () => dio.get<List<dynamic>>(
          '/v1/games/search',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['q'], 'elden');
      expect(query['limit'], 5);
    });
  });

  group('createGame', () {
    test('posts full body and parses Game', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/games', _gameJson()));

      final game = await repository.createGame(
        slug: 'elden-ring',
        title: 'Elden Ring',
        summary: 'RPG',
        coverUrl: 'https://cover.jpg',
      );

      expect(game.publicId, 'game-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/games');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['slug'], 'elden-ring');
      expect(body['title'], 'Elden Ring');
      expect(body['summary'], 'RPG');
      expect(body['cover_url'], 'https://cover.jpg');
    });

    test('omits optional fields when null', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/games', _gameJson()));

      await repository.createGame(slug: 'minimal', title: 'Minimal');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body.containsKey('summary'), isFalse);
      expect(body.containsKey('cover_url'), isFalse);
    });
  });

  group('listLibrary', () {
    test('passes status and pagination, parses response', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/library', <String, dynamic>{
          'items': <Map<String, dynamic>>[_libraryEntryJson()],
          'total': 1,
          'limit': 50,
          'offset': 0,
        }),
      );

      final result = await repository.listLibrary(status: 'playing');

      expect(result, isA<LibraryListResponse>());
      expect(result.items, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/library',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['status'], 'playing');
      expect(query['limit'], 50);
      expect(query['offset'], 0);
    });

    test('omits status when null', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/library', <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
          'limit': 50,
          'offset': 0,
        }),
      );

      await repository.listLibrary();

      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      expect((captured[0] as Map).containsKey('status'), isFalse);
    });
  });

  group('addToLibrary', () {
    test('posts body and parses LibraryEntry', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/library', _libraryEntryJson()));

      final entry = await repository.addToLibrary(
        gamePublicId: 'game-001',
        platformId: 48,
        status: 'playing',
        notes: 'Hi',
      );

      expect(entry.publicId, 'entry-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/library');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['game_public_id'], 'game-001');
      expect(body['platform_id'], 48);
      expect(body['status'], 'playing');
      expect(body['notes'], 'Hi');
    });

    test('omits notes when null and defaults status to backlog', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/library', _libraryEntryJson()));

      await repository.addToLibrary(gamePublicId: 'g', platformId: 1);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['status'], 'backlog');
      expect(body.containsKey('notes'), isFalse);
    });
  });

  group('updateEntry', () {
    test('patches changed fields and parses LibraryEntry', () async {
      when(
        () => dio.patch<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/library/entry-001', _libraryEntryJson()),
      );

      final entry = await repository.updateEntry(
        'entry-001',
        status: 'completed',
        notes: 'Done',
      );

      expect(entry.publicId, 'entry-001');
      final captured = verify(
        () => dio.patch<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/library/entry-001');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['status'], 'completed');
      expect(body['notes'], 'Done');
    });

    test('sends empty body when no fields provided', () async {
      when(
        () => dio.patch<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/library/entry-001', _libraryEntryJson()),
      );

      await repository.updateEntry('entry-001');

      final captured = verify(
        () => dio.patch<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map).isEmpty, isTrue);
    });
  });

  group('deleteEntry', () {
    test('calls delete on the entry path', () async {
      when(() => dio.delete<void>(any())).thenAnswer(
        (_) async => Response<void>(
          requestOptions: RequestOptions(path: '/v1/library/entry-001'),
        ),
      );

      await repository.deleteEntry('entry-001');

      verify(() => dio.delete<void>('/v1/library/entry-001')).called(1);
    });

    test('rethrows DioException', () async {
      when(() => dio.delete<void>(any())).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/v1/library/x')),
      );

      expect(() => repository.deleteEntry('x'), throwsA(isA<DioException>()));
    });
  });
}
