import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockCaptureRepository extends Mock implements CaptureRepository {}

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

final _now = DateTime.utc(2025, 6);

final _capture = Capture(
  publicId: 'cap-001',
  inputType: 'text',
  rawText: 'I just finished Elden Ring',
  status: 'review',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-001',
      title: 'Elden Ring',
      status: 'pending',
    ),
  ],
  createdAt: _now,
  updatedAt: _now,
);

final _updatedCapture = Capture(
  publicId: 'cap-001',
  inputType: 'text',
  rawText: 'I just finished Elden Ring',
  status: 'committed',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-001',
      title: 'Elden Ring',
      status: 'confirmed',
    ),
  ],
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedCapture = Capture(
  publicId: 'cap-001',
  inputType: 'text',
  rawText: 'I just finished Elden Ring',
  status: 'review',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-001',
      title: 'Elden Ring',
      status: 'rejected',
    ),
  ],
  createdAt: _now,
  updatedAt: _now,
);

final _captureListResponse = CaptureListResponse(items: [_capture], total: 1);

const _transcribeResult = TranscribeResult(
  text: 'I bought Zelda last week',
  language: 'en',
  durationSeconds: 4.2,
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

DioException _dioError({
  String? detail,
  String? message,
  int statusCode = 400,
}) {
  return DioException(
    requestOptions: RequestOptions(),
    message: message,
    response: detail != null
        ? Response(
            requestOptions: RequestOptions(),
            statusCode: statusCode,
            data: <String, dynamic>{'detail': detail},
          )
        : null,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockCaptureRepository mockCaptureRepository;

  setUp(() {
    mockCaptureRepository = MockCaptureRepository();
  });

  CaptureBloc buildBloc() =>
      CaptureBloc(captureRepository: mockCaptureRepository);

  group('CaptureBloc', () {
    test('initial state is CaptureInitial', () {
      final bloc = buildBloc();
      expect(bloc.state, const CaptureInitial());
      bloc.close();
    });

    // ---------------------------------------------------------------
    // LoadCaptures
    // ---------------------------------------------------------------
    group('LoadCaptures', () {
      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureLoading, CaptureLoaded] on success',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(),
          ).thenAnswer((_) async => _captureListResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => [
          const CaptureLoading(),
          CaptureLoaded(captures: [_capture], total: 1),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'passes status filter to repository',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(status: 'review'),
          ).thenAnswer((_) async => _captureListResponse);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures(status: 'review')),
        expect: () => [
          const CaptureLoading(),
          CaptureLoaded(captures: [_capture], total: 1),
        ],
        verify: (_) {
          verify(
            () => mockCaptureRepository.listCaptures(status: 'review'),
          ).called(1);
        },
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureLoading, CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(_dioError(detail: 'Unauthorized'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'Unauthorized'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureLoading, CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(Exception('network down'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'Exception: network down'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitTextCapture
    // ---------------------------------------------------------------
    group('SubmitTextCapture', () {
      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureSubmitted] on success',
        setUp: () {
          when(
            () => mockCaptureRepository.submitText('I beat Elden Ring'),
          ).thenAnswer((_) async => _capture);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const SubmitTextCapture(rawText: 'I beat Elden Ring')),
        expect: () => [
          const CaptureSubmitting(),
          CaptureSubmitted(capture: _capture),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.submitText(any()),
          ).thenThrow(_dioError(detail: 'Text too short'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const SubmitTextCapture(rawText: 'hi')),
        expect: () => const [
          CaptureSubmitting(),
          CaptureError(message: 'Text too short'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.submitText(any()),
          ).thenThrow(Exception('parse error'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const SubmitTextCapture(rawText: 'test')),
        expect: () => const [
          CaptureSubmitting(),
          CaptureError(message: 'Exception: parse error'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // TranscribeAudio
    // ---------------------------------------------------------------
    group('TranscribeAudio', () {
      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureTranscribing, CaptureTranscribed] on success',
        setUp: () {
          when(
            () => mockCaptureRepository.transcribeAudio('/tmp/audio.wav'),
          ).thenAnswer((_) async => _transcribeResult);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const TranscribeAudio(filePath: '/tmp/audio.wav')),
        expect: () => const [
          CaptureTranscribing(),
          CaptureTranscribed(text: 'I bought Zelda last week'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureTranscribing, CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.transcribeAudio(any()),
          ).thenThrow(_dioError(detail: 'Audio format unsupported'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const TranscribeAudio(filePath: '/tmp/bad.mp3')),
        expect: () => const [
          CaptureTranscribing(),
          CaptureError(message: 'Audio format unsupported'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureTranscribing, CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.transcribeAudio(any()),
          ).thenThrow(Exception('file not found'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const TranscribeAudio(filePath: '/tmp/missing.wav')),
        expect: () => const [
          CaptureTranscribing(),
          CaptureError(message: 'Exception: file not found'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitVoiceCapture
    // ---------------------------------------------------------------
    group('SubmitVoiceCapture', () {
      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureSubmitted] on success '
        'and calls submitText with inputType voice',
        setUp: () {
          when(
            () => mockCaptureRepository.submitText(
              'I bought Zelda last week',
              inputType: 'voice',
            ),
          ).thenAnswer((_) async => _capture);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const SubmitVoiceCapture(rawText: 'I bought Zelda last week'),
        ),
        expect: () => [
          const CaptureSubmitting(),
          CaptureSubmitted(capture: _capture),
        ],
        verify: (_) {
          verify(
            () => mockCaptureRepository.submitText(
              'I bought Zelda last week',
              inputType: 'voice',
            ),
          ).called(1);
        },
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.submitText(
              any(),
              inputType: any(named: 'inputType'),
            ),
          ).thenThrow(_dioError(detail: 'Voice processing failed'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const SubmitVoiceCapture(rawText: 'test voice')),
        expect: () => const [
          CaptureSubmitting(),
          CaptureError(message: 'Voice processing failed'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // SubmitPhotoCapture
    // ---------------------------------------------------------------
    group('SubmitPhotoCapture', () {
      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureSubmitted] on success',
        setUp: () {
          when(
            () => mockCaptureRepository.submitPhoto('/tmp/photo.jpg'),
          ).thenAnswer((_) async => _capture);
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const SubmitPhotoCapture(imagePath: '/tmp/photo.jpg')),
        expect: () => [
          const CaptureSubmitting(),
          CaptureSubmitted(capture: _capture),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.submitPhoto(any()),
          ).thenThrow(_dioError(detail: 'Image too large'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const SubmitPhotoCapture(imagePath: '/tmp/big.jpg')),
        expect: () => const [
          CaptureSubmitting(),
          CaptureError(message: 'Image too large'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureSubmitting, CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.submitPhoto(any()),
          ).thenThrow(Exception('io error'));
        },
        build: buildBloc,
        act: (bloc) =>
            bloc.add(const SubmitPhotoCapture(imagePath: '/tmp/bad.jpg')),
        expect: () => const [
          CaptureSubmitting(),
          CaptureError(message: 'Exception: io error'),
        ],
      );
    });

    // ---------------------------------------------------------------
    // ConfirmCandidate
    // ---------------------------------------------------------------
    group('ConfirmCandidate', () {
      blocTest<CaptureBloc, CaptureState>(
        'calls confirmCandidate and getCapture, '
        'emits [CaptureSubmitted(updated)]',
        setUp: () {
          when(
            () => mockCaptureRepository.confirmCandidate(
              'cap-001',
              'cand-001',
              1,
            ),
          ).thenAnswer((_) async => <String, dynamic>{});
          when(
            () => mockCaptureRepository.getCapture('cap-001'),
          ).thenAnswer((_) async => _updatedCapture);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const ConfirmCandidate(
            captureId: 'cap-001',
            candidateId: 'cand-001',
            platformId: 1,
          ),
        ),
        expect: () => [CaptureSubmitted(capture: _updatedCapture)],
        verify: (_) {
          verify(
            () => mockCaptureRepository.confirmCandidate(
              'cap-001',
              'cand-001',
              1,
            ),
          ).called(1);
          verify(() => mockCaptureRepository.getCapture('cap-001')).called(1);
        },
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.confirmCandidate(
              any(),
              any(),
              any(),
              status: any(named: 'status'),
            ),
          ).thenThrow(_dioError(detail: 'Candidate already confirmed'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const ConfirmCandidate(
            captureId: 'cap-001',
            candidateId: 'cand-001',
            platformId: 1,
          ),
        ),
        expect: () => const [
          CaptureError(message: 'Candidate already confirmed'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.confirmCandidate(
              any(),
              any(),
              any(),
              status: any(named: 'status'),
            ),
          ).thenThrow(Exception('unexpected'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const ConfirmCandidate(
            captureId: 'cap-001',
            candidateId: 'cand-001',
            platformId: 1,
          ),
        ),
        expect: () => const [CaptureError(message: 'Exception: unexpected')],
      );
    });

    // ---------------------------------------------------------------
    // RejectCandidate
    // ---------------------------------------------------------------
    group('RejectCandidate', () {
      blocTest<CaptureBloc, CaptureState>(
        'calls rejectCandidate and getCapture, '
        'emits [CaptureSubmitted(updated)]',
        setUp: () {
          when(
            () => mockCaptureRepository.rejectCandidate('cap-001', 'cand-001'),
          ).thenAnswer((_) async {});
          when(
            () => mockCaptureRepository.getCapture('cap-001'),
          ).thenAnswer((_) async => _rejectedCapture);
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RejectCandidate(captureId: 'cap-001', candidateId: 'cand-001'),
        ),
        expect: () => [CaptureSubmitted(capture: _rejectedCapture)],
        verify: (_) {
          verify(
            () => mockCaptureRepository.rejectCandidate('cap-001', 'cand-001'),
          ).called(1);
          verify(() => mockCaptureRepository.getCapture('cap-001')).called(1);
        },
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureError] on DioException',
        setUp: () {
          when(
            () => mockCaptureRepository.rejectCandidate(any(), any()),
          ).thenThrow(_dioError(detail: 'Candidate not found'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RejectCandidate(captureId: 'cap-001', candidateId: 'cand-999'),
        ),
        expect: () => const [CaptureError(message: 'Candidate not found')],
      );

      blocTest<CaptureBloc, CaptureState>(
        'emits [CaptureError] on generic Exception',
        setUp: () {
          when(
            () => mockCaptureRepository.rejectCandidate(any(), any()),
          ).thenThrow(Exception('server error'));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(
          const RejectCandidate(captureId: 'cap-001', candidateId: 'cand-001'),
        ),
        expect: () => const [CaptureError(message: 'Exception: server error')],
      );
    });

    // ---------------------------------------------------------------
    // _extractErrorMessage coverage
    // ---------------------------------------------------------------
    group('_extractErrorMessage (via DioException paths)', () {
      blocTest<CaptureBloc, CaptureState>(
        'returns fallback when response is null and message is null',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(DioException(requestOptions: RequestOptions()));
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'An unexpected error occurred.'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'returns e.message when response data has no detail key',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'socket closed',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 502,
                data: <String, dynamic>{'error': 'bad gateway'},
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'socket closed'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'returns e.message when response data is not a Map',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'unexpected format',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 500,
                data: 'plain text error',
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'unexpected format'),
        ],
      );

      blocTest<CaptureBloc, CaptureState>(
        'returns e.message when detail is not a String',
        setUp: () {
          when(
            () => mockCaptureRepository.listCaptures(
              status: any(named: 'status'),
            ),
          ).thenThrow(
            DioException(
              requestOptions: RequestOptions(),
              message: 'complex detail fallback',
              response: Response(
                requestOptions: RequestOptions(),
                statusCode: 422,
                data: <String, dynamic>{
                  'detail': <Map<String, dynamic>>[
                    {'field': 'text', 'msg': 'required'},
                  ],
                },
              ),
            ),
          );
        },
        build: buildBloc,
        act: (bloc) => bloc.add(const LoadCaptures()),
        expect: () => const [
          CaptureLoading(),
          CaptureError(message: 'complex detail fallback'),
        ],
      );
    });
  });
}
