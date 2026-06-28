import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockCaptureRepository extends Mock implements CaptureRepository {}

final _now = DateTime.utc(2025, 6);

final _capture = Capture(
  publicId: 'cap-001',
  inputType: 'library_import',
  status: 'review',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-1',
      title: 'Elden Ring',
      igdbTitle: 'Elden Ring',
      status: 'pending',
    ),
    CaptureCandidate(publicId: 'cand-2', title: 'Hades', status: 'pending'),
  ],
  createdAt: _now,
  updatedAt: _now,
);

DioException _dioError({String? detail, String? message}) {
  return DioException(
    requestOptions: RequestOptions(),
    message: message,
    response: detail != null
        ? Response<dynamic>(
            requestOptions: RequestOptions(),
            statusCode: 429,
            data: <String, dynamic>{'detail': detail},
          )
        : null,
  );
}

void main() {
  late MockCaptureRepository repository;

  setUp(() {
    repository = MockCaptureRepository();
  });

  group('SubmitLibraryImport', () {
    blocTest<LibraryImportBloc, LibraryImportState>(
      'emits [Submitting, Review] on successful upload',
      build: () {
        when(
          () => repository.submitLibraryImport(any()),
        ).thenAnswer((_) async => _capture);
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) =>
          bloc.add(const SubmitLibraryImport(imagePaths: ['a.jpg', 'b.jpg'])),
      expect: () => [
        const LibraryImportSubmitting(),
        LibraryImportReview(capture: _capture),
      ],
      verify: (_) {
        verify(
          () => repository.submitLibraryImport(['a.jpg', 'b.jpg']),
        ).called(1);
      },
    );

    blocTest<LibraryImportBloc, LibraryImportState>(
      'emits [Submitting, Error] with detail message on DioException',
      build: () {
        when(
          () => repository.submitLibraryImport(any()),
        ).thenThrow(_dioError(detail: 'Daily cap reached'));
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) => bloc.add(const SubmitLibraryImport(imagePaths: ['a.jpg'])),
      expect: () => [
        const LibraryImportSubmitting(),
        const LibraryImportError(message: 'Daily cap reached'),
      ],
    );

    blocTest<LibraryImportBloc, LibraryImportState>(
      'falls back to message when no detail',
      build: () {
        when(
          () => repository.submitLibraryImport(any()),
        ).thenThrow(_dioError(message: 'network down'));
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) => bloc.add(const SubmitLibraryImport(imagePaths: ['a.jpg'])),
      expect: () => [
        const LibraryImportSubmitting(),
        const LibraryImportError(message: 'network down'),
      ],
    );

    blocTest<LibraryImportBloc, LibraryImportState>(
      'emits Error for a non-Dio exception',
      build: () {
        when(
          () => repository.submitLibraryImport(any()),
        ).thenThrow(Exception('boom'));
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) => bloc.add(const SubmitLibraryImport(imagePaths: ['a.jpg'])),
      expect: () => [
        const LibraryImportSubmitting(),
        const LibraryImportError(message: 'Exception: boom'),
      ],
    );
  });

  group('BulkConfirmImport', () {
    blocTest<LibraryImportBloc, LibraryImportState>(
      'emits [Confirming, Done] on success',
      build: () {
        when(
          () => repository.bulkConfirmCandidates(
            any(),
            any(),
            any(),
            status: any(named: 'status'),
          ),
        ).thenAnswer(
          (_) async => const BulkConfirmResult(confirmed: 2, rejected: 0),
        );
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) => bloc.add(
        const BulkConfirmImport(
          captureId: 'cap-001',
          confirmIds: ['cand-1', 'cand-2'],
          platformId: 5,
        ),
      ),
      expect: () => [
        const LibraryImportConfirming(),
        const LibraryImportDone(confirmed: 2, rejected: 0),
      ],
      verify: (_) {
        verify(
          () => repository.bulkConfirmCandidates(
            'cap-001',
            ['cand-1', 'cand-2'],
            5,
            status: any(named: 'status'),
          ),
        ).called(1);
      },
    );

    blocTest<LibraryImportBloc, LibraryImportState>(
      'emits [Confirming, Error] on DioException',
      build: () {
        when(
          () => repository.bulkConfirmCandidates(
            any(),
            any(),
            any(),
            status: any(named: 'status'),
          ),
        ).thenThrow(_dioError(detail: 'bad request'));
        return LibraryImportBloc(captureRepository: repository);
      },
      act: (bloc) => bloc.add(
        const BulkConfirmImport(
          captureId: 'cap-001',
          confirmIds: ['cand-1'],
          platformId: 5,
        ),
      ),
      expect: () => [
        const LibraryImportConfirming(),
        const LibraryImportError(message: 'bad request'),
      ],
    );
  });
}
