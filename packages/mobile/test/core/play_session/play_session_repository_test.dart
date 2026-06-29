import 'package:app/core/api/api_client.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/core/play_session/play_session_repository.dart';
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

Map<String, dynamic> _playSessionJson({String publicId = 'playSession-001'}) {
  return <String, dynamic>{
    'public_id': publicId,
    'library_entry': _libraryEntryJson(),
    'play_session_type': 'story',
    'recap_text': 'Your playSession today...',
    'started_at': '2025-06-20T18:00:00Z',
    'created_at': '2025-06-20T17:55:00Z',
    'updated_at': '2025-06-20T18:00:00Z',
  };
}

Map<String, dynamic> _recapPreviewJson() {
  return <String, dynamic>{
    'library_entry': _libraryEntryJson(),
    'recap_text': 'Welcome back, Tarnished.',
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
  late PlaySessionRepository repository;

  setUpAll(() {
    registerFallbackValue(RequestOptions(path: '/'));
    registerFallbackValue(Options());
  });

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = PlaySessionRepository(apiClient: apiClient);
  });

  group('previewRecap', () {
    test('posts quick mode and parses RecapPreview', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).thenAnswer(
        (_) async =>
            _response('/v1/play-sessions/preview-recap', _recapPreviewJson()),
      );

      final preview = await repository.previewRecap('entry-001');

      expect(preview, isA<RecapPreview>());
      expect(preview.recapText, 'Welcome back, Tarnished.');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
          cancelToken: any(named: 'cancelToken'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions/preview-recap');
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
            _response('/v1/play-sessions/preview-recap', _recapPreviewJson()),
      );

      await repository.previewRecap(
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
        () => repository.previewRecap('entry-001'),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('submitRetroactiveWrapUp', () {
    test('posts wrapUp and parses RecapPreview', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/play-sessions/retroactive-wrap-up',
          _recapPreviewJson(),
        ),
      );

      final preview = await repository.submitRetroactiveWrapUp(
        'entry-001',
        'Beat boss',
      );

      expect(preview, isA<RecapPreview>());
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions/retroactive-wrap-up');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['library_entry_public_id'], 'entry-001');
      expect(body['wrap_up_text'], 'Beat boss');
    });
  });

  group('startPlaySession', () {
    test('posts and parses PlaySession', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/play-sessions', _playSessionJson()),
      );

      final playSession = await repository.startPlaySession(
        'entry-001',
        recapText: 'Go!',
      );

      expect(playSession.publicId, 'playSession-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['library_entry_public_id'], 'entry-001');
      expect(body['recap_text'], 'Go!');
    });

    test('omits recap_text when null', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/play-sessions', _playSessionJson()),
      );

      await repository.startPlaySession('entry-001');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body.containsKey('recap_text'), isFalse);
    });

    test('sends skip_recap for the "just play" path', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/play-sessions', _playSessionJson()),
      );

      await repository.startPlaySession('entry-001', skipRecap: true);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      final body = captured[0] as Map<String, dynamic>;
      expect(body['skip_recap'], isTrue);
      expect(body.containsKey('recap_text'), isFalse);
    });
  });

  group('getActivePlaySession', () {
    test('returns PlaySession on success', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/play-sessions/active', _playSessionJson()),
      );

      final playSession = await repository.getActivePlaySession();

      expect(playSession, isNotNull);
      expect(playSession!.publicId, 'playSession-001');
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/play-sessions/active'),
      ).called(1);
    });

    test('returns null on 404', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/play-sessions/active'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/play-sessions/active'),
            statusCode: 404,
          ),
        ),
      );

      final playSession = await repository.getActivePlaySession();

      expect(playSession, isNull);
    });

    test('rethrows non-404 DioException', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/play-sessions/active'),
          response: Response(
            requestOptions: RequestOptions(path: '/v1/play-sessions/active'),
            statusCode: 500,
          ),
        ),
      );

      expect(repository.getActivePlaySession, throwsA(isA<DioException>()));
    });
  });

  group('getPlaySession', () {
    test('gets by id and parses PlaySession', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async =>
            _response('/v1/play-sessions/playSession-001', _playSessionJson()),
      );

      final playSession = await repository.getPlaySession('playSession-001');

      expect(playSession.publicId, 'playSession-001');
      verify(
        () =>
            dio.get<Map<String, dynamic>>('/v1/play-sessions/playSession-001'),
      ).called(1);
    });
  });

  group('listPlaySessions', () {
    test('passes pagination and parses list', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/play-sessions', <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        }),
      );

      final result = await repository.listPlaySessions(limit: 10, offset: 5);

      expect(result, isA<PlaySessionListResponse>());
      expect(result.total, 0);
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/play-sessions',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['limit'], 10);
      expect(query['offset'], 5);
    });
  });

  group('submitWrapUp', () {
    test('patches wrapUp and parses PlaySession', () async {
      when(
        () => dio.patch<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/play-sessions/playSession-001/wrap-up',
          _playSessionJson(),
        ),
      );

      final playSession = await repository.submitWrapUp(
        'playSession-001',
        'Had fun',
      );

      expect(playSession.publicId, 'playSession-001');
      final captured = verify(
        () => dio.patch<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions/playSession-001/wrap-up');
      expect((captured[1] as Map)['wrap_up_text'], 'Had fun');
    });
  });

  group('endPlaySession', () {
    test('posts ended_via and parses PlaySession', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/play-sessions/playSession-001/end',
          _playSessionJson(),
        ),
      );

      final playSession = await repository.endPlaySession(
        'playSession-001',
        endedVia: 'wrapUp',
      );

      expect(playSession.publicId, 'playSession-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions/playSession-001/end');
      expect((captured[1] as Map)['ended_via'], 'wrapUp');
    });

    test('defaults ended_via to paused_app', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/play-sessions/playSession-001/end',
          _playSessionJson(),
        ),
      );

      await repository.endPlaySession('playSession-001');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map)['ended_via'], 'paused_app');
    });
  });

  group('regenerateRecap', () {
    test('posts current position and parses PlaySession', () async {
      when(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async => _response(
          '/v1/play-sessions/playSession-001/recap/regenerate',
          _playSessionJson(),
        ),
      );

      final playSession = await repository.regenerateRecap(
        'playSession-001',
        currentPosition: 'Limgrave',
      );

      expect(playSession.publicId, 'playSession-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
          options: any(named: 'options'),
        ),
      ).captured;
      expect(captured[0], '/v1/play-sessions/playSession-001/recap/regenerate');
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
          '/v1/play-sessions/playSession-001/recap/regenerate',
          _playSessionJson(),
        ),
      );

      await repository.regenerateRecap('playSession-001');

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
