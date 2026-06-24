import 'package:app/core/api/api_client.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

Map<String, dynamic> _libraryEntryJson() => <String, dynamic>{
  'public_id': 'entry-001',
  'game': <String, dynamic>{
    'public_id': 'game-001',
    'slug': 'elden-ring',
    'title': 'Elden Ring',
    'metadata_source': 'igdb',
    'created_at': '2025-01-01T00:00:00Z',
  },
  'platform': <String, dynamic>{
    'id': 48,
    'slug': 'ps5',
    'label': 'PS5',
    'family': 'PlayStation',
  },
  'status': 'playing',
  'created_at': '2025-01-01T00:00:00Z',
  'updated_at': '2025-01-01T00:00:00Z',
};

Map<String, dynamic> _loadoutJson({String publicId = 'loadout-001'}) =>
    <String, dynamic>{
      'public_id': publicId,
      'mood': 'chill',
      'available_minutes': 60,
      'mental_energy': 'medium',
      'context': null,
      'reasoning': 'Calm game',
      'action': 'Explore',
      'created_at': '2025-06-01T10:00:00Z',
      'updated_at': '2025-06-01T10:30:00Z',
      'library_entry': _libraryEntryJson(),
    };

Map<String, dynamic> _loadoutListItemJson() => <String, dynamic>{
  'public_id': 'loadout-001',
  'mood': 'chill',
  'available_minutes': 60,
  'mental_energy': 'medium',
  'reasoning': 'Calm game',
  'action': 'Explore',
  'created_at': '2025-06-01T10:00:00Z',
  'library_entry': _libraryEntryJson(),
};

Response<T> _response<T>(String path, T data) => Response<T>(
  requestOptions: RequestOptions(path: path),
  data: data,
);

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late LoadoutRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = LoadoutRepository(apiClient: apiClient);
  });

  group('createLoadout', () {
    test('posts body and parses list of loadouts', () async {
      when(
        () => dio.post<List<dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/loadouts', <dynamic>[_loadoutJson()]),
      );

      final loadouts = await repository.createLoadout(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'After work',
      );

      expect(loadouts, hasLength(1));
      expect(loadouts.first, isA<Loadout>());
      final captured = verify(
        () => dio.post<List<dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      expect(captured[0], '/v1/loadouts');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['mood'], 'chill');
      expect(body['available_minutes'], 60);
      expect(body['mental_energy'], 'medium');
      expect(body['count'], 2);
      expect(body['context'], 'After work');
    });

    test('omits context when null and defaults count to 1', () async {
      when(
        () => dio.post<List<dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/loadouts', <dynamic>[_loadoutJson()]),
      );

      await repository.createLoadout(
        mood: 'focused',
        availableMinutes: 30,
        mentalEnergy: 'high',
      );

      final captured = verify(
        () => dio.post<List<dynamic>>(
          any(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['count'], 1);
      expect(body.containsKey('context'), isFalse);
    });

    test('rethrows DioException', () async {
      when(
        () => dio.post<List<dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/v1/loadouts')),
      );

      expect(
        () => repository.createLoadout(
          mood: 'chill',
          availableMinutes: 60,
          mentalEnergy: 'medium',
        ),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('acceptLoadout', () {
    test('posts to accept path with empty body and parses Loadout', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async =>
            _response('/v1/loadouts/loadout-001/accept', _loadoutJson()),
      );

      final loadout = await repository.acceptLoadout('loadout-001');

      expect(loadout.publicId, 'loadout-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          '/v1/loadouts/loadout-001/accept',
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body.containsKey('briefing_text'), isFalse);
    });

    test('includes briefing_text in body when provided', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async =>
            _response('/v1/loadouts/loadout-001/accept', _loadoutJson()),
      );

      await repository.acceptLoadout(
        'loadout-001',
        briefingText: 'Head to the catacombs.',
      );

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          '/v1/loadouts/loadout-001/accept',
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['briefing_text'], 'Head to the catacombs.');
    });
  });

  group('rejectLoadout', () {
    test('posts to reject path and parses Loadout', () async {
      when(() => dio.post<Map<String, dynamic>>(any())).thenAnswer(
        (_) async =>
            _response('/v1/loadouts/loadout-001/reject', _loadoutJson()),
      );

      final loadout = await repository.rejectLoadout('loadout-001');

      expect(loadout.publicId, 'loadout-001');
      verify(
        () => dio.post<Map<String, dynamic>>('/v1/loadouts/loadout-001/reject'),
      ).called(1);
    });
  });

  group('listLoadouts', () {
    test('passes pagination and parses response', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/loadouts', <String, dynamic>{
          'items': <Map<String, dynamic>>[_loadoutListItemJson()],
          'total': 1,
        }),
      );

      final result = await repository.listLoadouts(limit: 5, offset: 10);

      expect(result, isA<LoadoutListResponse>());
      expect(result.items, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/loadouts',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['limit'], 5);
      expect(query['offset'], 10);
    });
  });

  group('getLatestLoadout', () {
    test('returns Loadout when present', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/loadouts/latest', _loadoutJson()),
      );

      final loadout = await repository.getLatestLoadout();

      expect(loadout, isNotNull);
      expect(loadout!.publicId, 'loadout-001');
    });

    test('returns null when data is null', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/v1/loadouts/latest'),
        ),
      );

      final loadout = await repository.getLatestLoadout();

      expect(loadout, isNull);
    });

    test('returns null on 404', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/loadouts/latest'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/loadouts/latest'),
            statusCode: 404,
          ),
        ),
      );

      final loadout = await repository.getLatestLoadout();

      expect(loadout, isNull);
    });

    test('rethrows non-404 DioException', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/loadouts/latest'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/loadouts/latest'),
            statusCode: 500,
          ),
        ),
      );

      expect(repository.getLatestLoadout, throwsA(isA<DioException>()));
    });
  });
}
