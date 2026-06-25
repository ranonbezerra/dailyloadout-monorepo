import 'dart:io';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockApiClient extends Mock implements ApiClient {}

class MockDio extends Mock implements Dio {}

Map<String, dynamic> _captureJson({String publicId = 'cap-001'}) =>
    <String, dynamic>{
      'public_id': publicId,
      'input_type': 'text',
      'raw_text': 'I bought Elden Ring',
      'status': 'review',
      'error_message': null,
      'candidates': <Map<String, dynamic>>[],
      'created_at': '2025-06-01T12:00:00Z',
      'updated_at': '2025-06-01T12:05:00Z',
    };

Response<T> _response<T>(String path, T data) => Response<T>(
  requestOptions: RequestOptions(path: path),
  data: data,
);

void main() {
  late MockApiClient apiClient;
  late MockDio dio;
  late CaptureRepository repository;

  setUp(() {
    apiClient = MockApiClient();
    dio = MockDio();
    when(() => apiClient.dio).thenReturn(dio);
    repository = CaptureRepository(apiClient: apiClient);
  });

  group('submitText', () {
    test('posts raw text and parses Capture', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/captures/text', _captureJson()));

      final capture = await repository.submitText('I bought Elden Ring');

      expect(capture, isA<Capture>());
      expect(capture.publicId, 'cap-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/text');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['raw_text'], 'I bought Elden Ring');
      expect(body['input_type'], 'text');
    });

    test('passes voice input type', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/captures/text', _captureJson()));

      await repository.submitText('hello', inputType: 'voice');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map)['input_type'], 'voice');
    });

    test('rethrows DioException', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenThrow(
        DioException(requestOptions: RequestOptions(path: '/v1/captures/text')),
      );

      expect(() => repository.submitText('x'), throwsA(isA<DioException>()));
    });
  });

  group('transcribeAudio', () {
    test('uploads form data and parses TranscribeResult', () async {
      final tmp = File('${Directory.systemTemp.path}/dl_test_audio.wav')
        ..writeAsBytesSync(<int>[0, 1, 2, 3]);
      addTearDown(() {
        if (tmp.existsSync()) tmp.deleteSync();
      });

      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/captures/transcribe', <String, dynamic>{
          'text': 'I finished Zelda',
          'language': 'en',
          'duration_seconds': 4.2,
        }),
      );

      final result = await repository.transcribeAudio(tmp.path);

      expect(result, isA<TranscribeResult>());
      expect(result.text, 'I finished Zelda');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/transcribe');
      expect(captured[1], isA<FormData>());
    });
  });

  group('submitPhoto', () {
    test('uploads form data and parses Capture', () async {
      final tmp = File('${Directory.systemTemp.path}/dl_test_photo.jpg')
        ..writeAsBytesSync(<int>[255, 216, 255]);
      addTearDown(() {
        if (tmp.existsSync()) tmp.deleteSync();
      });

      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response('/v1/captures/photo', _captureJson()),
      );

      final capture = await repository.submitPhoto(tmp.path);

      expect(capture.publicId, 'cap-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/photo');
      expect(captured[1], isA<FormData>());
    });
  });

  group('listCaptures', () {
    test('passes status and pagination, parses response', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/captures', <String, dynamic>{
          'items': <Map<String, dynamic>>[_captureJson()],
          'total': 1,
        }),
      );

      final result = await repository.listCaptures(
        status: 'review',
        limit: 5,
        offset: 2,
      );

      expect(result, isA<CaptureListResponse>());
      expect(result.items, hasLength(1));
      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          '/v1/captures',
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      final query = captured[0] as Map<String, dynamic>;
      expect(query['status'], 'review');
      expect(query['limit'], 5);
      expect(query['offset'], 2);
    });

    test('omits status when null', () async {
      when(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: any(named: 'queryParameters'),
        ),
      ).thenAnswer(
        (_) async => _response('/v1/captures', <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        }),
      );

      await repository.listCaptures();

      final captured = verify(
        () => dio.get<Map<String, dynamic>>(
          any(),
          queryParameters: captureAny(named: 'queryParameters'),
        ),
      ).captured;
      expect((captured[0] as Map).containsKey('status'), isFalse);
    });
  });

  group('getCapture', () {
    test('gets by id and parses Capture', () async {
      when(() => dio.get<Map<String, dynamic>>(any())).thenAnswer(
        (_) async => _response('/v1/captures/cap-001', _captureJson()),
      );

      final capture = await repository.getCapture('cap-001');

      expect(capture.publicId, 'cap-001');
      verify(
        () => dio.get<Map<String, dynamic>>('/v1/captures/cap-001'),
      ).called(1);
    });
  });

  group('confirmCandidate', () {
    test('posts platform and status, returns raw data', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/captures/cap-001/candidates/cand-001/confirm',
          <String, dynamic>{'public_id': 'entry-001'},
        ),
      );

      final data = await repository.confirmCandidate(
        'cap-001',
        'cand-001',
        48,
        status: 'playing',
      );

      expect(data['public_id'], 'entry-001');
      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/cap-001/candidates/cand-001/confirm');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['platform_id'], 48);
      expect(body['status'], 'playing');
    });

    test('defaults status to backlog', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/captures/cap-001/candidates/cand-001/confirm',
          <String, dynamic>{'public_id': 'entry-001'},
        ),
      );

      await repository.confirmCandidate('cap-001', 'cand-001', 1);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map)['status'], 'backlog');
    });
  });

  group('submitLibraryImport', () {
    test('posts repeated files form data and parses candidates', () async {
      final tmp1 = File('${Directory.systemTemp.path}/dl_lib_1.jpg')
        ..writeAsBytesSync(<int>[255, 216, 255]);
      final tmp2 = File('${Directory.systemTemp.path}/dl_lib_2.jpg')
        ..writeAsBytesSync(<int>[255, 216, 255]);
      addTearDown(() {
        if (tmp1.existsSync()) tmp1.deleteSync();
        if (tmp2.existsSync()) tmp2.deleteSync();
      });

      final json = _captureJson()
        ..['input_type'] = 'library_import'
        ..['candidates'] = <Map<String, dynamic>>[
          {
            'public_id': 'cand-1',
            'title': 'Elden Ring',
            'igdb_title': 'Elden Ring',
            'igdb_cover_url': 'https://img/eldenring.jpg',
            'status': 'pending',
          },
          {'public_id': 'cand-2', 'title': 'Hades', 'status': 'pending'},
        ];

      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer((_) async => _response('/v1/captures/library-import', json));

      final capture = await repository.submitLibraryImport([
        tmp1.path,
        tmp2.path,
      ]);

      expect(capture, isA<Capture>());
      expect(capture.candidates, hasLength(2));
      expect(capture.candidates.first.title, 'Elden Ring');
      expect(capture.candidates.first.igdbTitle, 'Elden Ring');

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/library-import');
      final form = captured[1] as FormData;
      // Both images attached under the repeated "files" field.
      expect(form.files.where((e) => e.key == 'files'), hasLength(2));
    });

    test('rethrows DioException (e.g. 429 daily cap)', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/v1/captures/library-import'),
          response: Response<dynamic>(
            requestOptions: RequestOptions(),
            statusCode: 429,
            data: <String, dynamic>{'detail': 'Daily cap reached'},
          ),
        ),
      );

      final tmp = File('${Directory.systemTemp.path}/dl_lib_err.jpg')
        ..writeAsBytesSync(<int>[255, 216, 255]);
      addTearDown(() {
        if (tmp.existsSync()) tmp.deleteSync();
      });

      expect(
        () => repository.submitLibraryImport([tmp.path]),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('bulkConfirmCandidates', () {
    test('posts the right body to the right path and parses result', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/captures/cap-001/candidates/bulk-confirm',
          <String, dynamic>{'confirmed': 3, 'rejected': 1},
        ),
      );

      final result = await repository.bulkConfirmCandidates(
        'cap-001',
        ['cand-1', 'cand-2', 'cand-3'],
        48,
        status: 'playing',
      );

      expect(result.confirmed, 3);
      expect(result.rejected, 1);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          captureAny(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect(captured[0], '/v1/captures/cap-001/candidates/bulk-confirm');
      final body = captured[1] as Map<String, dynamic>;
      expect(body['confirm_public_ids'], ['cand-1', 'cand-2', 'cand-3']);
      expect(body['platform_id'], 48);
      expect(body['status'], 'playing');
    });

    test('defaults status to backlog', () async {
      when(
        () => dio.post<Map<String, dynamic>>(any(), data: any(named: 'data')),
      ).thenAnswer(
        (_) async => _response(
          '/v1/captures/cap-001/candidates/bulk-confirm',
          <String, dynamic>{'confirmed': 1, 'rejected': 0},
        ),
      );

      await repository.bulkConfirmCandidates('cap-001', ['cand-1'], 1);

      final captured = verify(
        () => dio.post<Map<String, dynamic>>(
          any(),
          data: captureAny(named: 'data'),
        ),
      ).captured;
      expect((captured[0] as Map)['status'], 'backlog');
    });
  });

  group('rejectCandidate', () {
    test('posts to reject path', () async {
      when(() => dio.post<void>(any())).thenAnswer(
        (_) async => Response<void>(
          requestOptions: RequestOptions(
            path: '/v1/captures/cap-001/candidates/cand-001/reject',
          ),
        ),
      );

      await repository.rejectCandidate('cap-001', 'cand-001');

      verify(
        () => dio.post<void>('/v1/captures/cap-001/candidates/cand-001/reject'),
      ).called(1);
    });
  });
}
