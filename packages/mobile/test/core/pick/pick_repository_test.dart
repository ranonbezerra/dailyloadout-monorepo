import 'package:app/core/api/api_client.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/core/pick/pick_repository.dart';
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

Map<String, dynamic> _pickJson({String publicId = 'pick-001'}) =>
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

Map<String, dynamic> _pickListItemJson() => <String, dynamic>{
  'public_id': 'pick-001',
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
  late PickRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = PickRepository(apiClient: apiClient);
  });

  group('createPick', () {
    test('posts body and parses list of picks', () async {
      when(
        () => dio.post<List<dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer((_) async => _response('/v1/picks', <dynamic>[_pickJson()]));

      final picks = await repository.createPick(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'After work',
      );

      expect(picks, hasLength(1));
      expect(picks.first, isA<Pick>());
      final captured = verify(
        () => dio.post<List<dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      expect(captured[0], '/v1/picks');
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
      ).thenAnswer((_) async => _response('/v1/picks', <dynamic>[_pickJson()]));

      await repository.createPick(
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
        DioException(requestOptions: RequestOptions(path: '/v1/picks')),
      );

      expect(
        () => repository.createPick(
          mood: 'chill',
          availableMinutes: 60,
          mentalEnergy: 'medium',
        ),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('acceptPick', () {
    test('posts to accept path with empty body and parses Pick', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/picks/pick-001/accept', _pickJson()),
      );

      final pick = await repository.acceptPick('pick-001');

      expect(pick.publicId, 'pick-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          '/v1/picks/pick-001/accept',
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body.containsKey('recap_text'), isFalse);
    });

    test('includes recap_text in body when provided', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/picks/pick-001/accept', _pickJson()),
      );

      await repository.acceptPick(
        'pick-001',
        recapText: 'Head to the catacombs.',
      );

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          '/v1/picks/pick-001/accept',
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['recap_text'], 'Head to the catacombs.');
    });
  });

  group('rejectPick', () {
    test('posts to reject path and parses Pick', () async {
      when(() => dio.post<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/picks/pick-001/reject', _pickJson()),
      );

      final pick = await repository.rejectPick('pick-001');

      expect(pick.publicId, 'pick-001');
      verify(
        () => dio.post<Map<String, dynamic>>('/v1/picks/pick-001/reject'),
      ).called(1);
    });
  });

  group('listPicks', () {
    test('passes pagination and parses response', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/picks', <String, dynamic>{
          'items': <Map<String, dynamic>>[_pickListItemJson()],
          'total': 1,
        }),
      );

      final result = await repository.listPicks(limit: 5, offset: 10);

      expect(result, isA<PickListResponse>());
      expect(result.items, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/picks',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['limit'], 5);
      expect(query['offset'], 10);
    });
  });

  group('getLatestPick', () {
    test('returns Pick when present', () async {
      when(
        () => dio.get<Map<String, dynamic>>(any()),
      ).thenAnswer((_) async => _response('/v1/picks/latest', _pickJson()));

      final pick = await repository.getLatestPick();

      expect(pick, isNotNull);
      expect(pick!.publicId, 'pick-001');
    });

    test('returns null when data is null', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/v1/picks/latest'),
        ),
      );

      final pick = await repository.getLatestPick();

      expect(pick, isNull);
    });

    test('returns null on 404', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/picks/latest'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/picks/latest'),
            statusCode: 404,
          ),
        ),
      );

      final pick = await repository.getLatestPick();

      expect(pick, isNull);
    });

    test('rethrows non-404 DioException', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/picks/latest'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/picks/latest'),
            statusCode: 500,
          ),
        ),
      );

      expect(repository.getLatestPick, throwsA(isA<DioException>()));
    });
  });
}
