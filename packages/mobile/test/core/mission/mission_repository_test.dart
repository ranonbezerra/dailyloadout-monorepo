import 'package:app/core/api/api_client.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

Map<String, dynamic> _libraryEntryJson({String publicId = 'entry-001'}) {
  return <String, dynamic>{
    'public_id': publicId,
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
}

Map<String, dynamic> _missionJson({String publicId = 'mission-001'}) {
  return <String, dynamic>{
    'public_id': publicId,
    'library_entry': _libraryEntryJson(),
    'mission_type': 'story',
    'briefing_text': 'Your mission today...',
    'started_at': '2025-06-20T18:00:00Z',
    'created_at': '2025-06-20T17:55:00Z',
    'updated_at': '2025-06-20T18:00:00Z',
  };
}

Map<String, dynamic> _briefingPreviewJson() {
  return <String, dynamic>{
    'library_entry': _libraryEntryJson(),
    'briefing_text': 'Welcome back, Tarnished.',
    'last_session_context': null,
  };
}

Response<T> _response<T>(String path, T data) {
  return Response<T>(
    requestOptions: RequestOptions(path: path),
    data: data,
  );
}

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late MissionRepository repository;

  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
    registerFallbackValue(Options());
  });

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = MissionRepository(apiClient: apiClient);
  });

  group('previewBriefing', () {
    test('posts quick mode and parses BriefingPreview', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).thenAnswer(
        (_) async =>
            _response('/v1/missions/preview-briefing', _briefingPreviewJson()),
      );

      final preview = await repository.previewBriefing('entry-001');

      expect(preview, isA<BriefingPreview>());
      expect(preview.briefingText, 'Welcome back, Tarnished.');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions/preview-briefing');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['library_entry_public_id'], 'entry-001');
      expect(body['mode'], 'quick');
      expect(body.containsKey('position_override'), isFalse);
    });

    test('includes position override and deep mode', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).thenAnswer(
        (_) async =>
            _response('/v1/missions/preview-briefing', _briefingPreviewJson()),
      );

      await repository.previewBriefing(
        'entry-002',
        mode: 'deep',
        positionOverride: 'Level 5',
      );

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['mode'], 'deep');
      expect(body['position_override'], 'Level 5');
    });

    test('rethrows DioException', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).thenThrow(DioException(requestOptions: RequestOptions(path: '/x')));

      expect(
        () => repository.previewBriefing('entry-001'),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('submitRetroactiveDebrief', () {
    test('posts debrief and parses BriefingPreview', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/missions/retroactive-debrief',
          _briefingPreviewJson(),
        ),
      );

      final preview = await repository.submitRetroactiveDebrief(
        'entry-001',
        'Beat boss',
      );

      expect(preview, isA<BriefingPreview>());
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions/retroactive-debrief');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['library_entry_public_id'], 'entry-001');
      expect(body['debrief_text'], 'Beat boss');
    });
  });

  group('startMission', () {
    test('posts and parses Mission', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/missions', _missionJson()));

      final mission = await repository.startMission(
        'entry-001',
        briefingText: 'Go!',
      );

      expect(mission.publicId, 'mission-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['library_entry_public_id'], 'entry-001');
      expect(body['briefing_text'], 'Go!');
    });

    test('omits briefing_text when null', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/missions', _missionJson()));

      await repository.startMission('entry-001');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body.containsKey('briefing_text'), isFalse);
    });

    test('sends skip_briefing for the "just play" path', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/missions', _missionJson()));

      await repository.startMission('entry-001', skipBriefing: true);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['skip_briefing'], isTrue);
      expect(body.containsKey('briefing_text'), isFalse);
    });
  });

  group('getActiveMission', () {
    test('returns Mission on success', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/missions/active', _missionJson()),
      );

      final mission = await repository.getActiveMission();

      expect(mission, isNotNull);
      expect(mission!.publicId, 'mission-001');
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/missions/active'),
      ).called(1);
    });

    test('returns null on 404', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/missions/active'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/missions/active'),
            statusCode: 404,
          ),
        ),
      );

      final mission = await repository.getActiveMission();

      expect(mission, isNull);
    });

    test('rethrows non-404 DioException', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/missions/active'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/missions/active'),
            statusCode: 500,
          ),
        ),
      );

      expect(repository.getActiveMission, throwsA(isA<DioException>()));
    });
  });

  group('getMission', () {
    test('gets by id and parses Mission', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/missions/mission-001', _missionJson()),
      );

      final mission = await repository.getMission('mission-001');

      expect(mission.publicId, 'mission-001');
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/missions/mission-001'),
      ).called(1);
    });
  });

  group('listMissions', () {
    test('passes pagination and parses list', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/missions', <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        }),
      );

      final result = await repository.listMissions(limit: 10, offset: 5);

      expect(result, isA<MissionListResponse>());
      expect(result.total, 0);
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/missions',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['limit'], 10);
      expect(query['offset'], 5);
    });
  });

  group('submitDebrief', () {
    test('patches debrief and parses Mission', () async {
      when(
        () => dio.patch<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async =>
            _response('/v1/missions/mission-001/debrief', _missionJson()),
      );

      final mission = await repository.submitDebrief('mission-001', 'Had fun');

      expect(mission.publicId, 'mission-001');
      final captured = verify(
        () => dio.patch<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions/mission-001/debrief');
      expect((captured[1] as Map)['debrief_text'], 'Had fun');
    });
  });

  group('endMission', () {
    test('posts ended_via and parses Mission', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/missions/mission-001/end', _missionJson()),
      );

      final mission = await repository.endMission(
        'mission-001',
        endedVia: 'debrief',
      );

      expect(mission.publicId, 'mission-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions/mission-001/end');
      expect((captured[1] as Map)['ended_via'], 'debrief');
    });

    test('defaults ended_via to paused_app', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/missions/mission-001/end', _missionJson()),
      );

      await repository.endMission('mission-001');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map)['ended_via'], 'paused_app');
    });
  });

  group('regenerateBriefing', () {
    test('posts current position and parses Mission', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => _response(
          '/v1/missions/mission-001/briefing/regenerate',
          _missionJson(),
        ),
      );

      final mission = await repository.regenerateBriefing(
        'mission-001',
        currentPosition: 'Limgrave',
      );

      expect(mission.publicId, 'mission-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      expect(captured[0], '/v1/missions/mission-001/briefing/regenerate');
      expect((captured[1] as Map)['current_position'], 'Limgrave');
    });

    test('omits current_position when null', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => _response(
          '/v1/missions/mission-001/briefing/regenerate',
          _missionJson(),
        ),
      );

      await repository.regenerateBriefing('mission-001');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      expect((captured[0] as Map).containsKey('current_position'), isFalse);
    });
  });
}
