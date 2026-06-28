import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'library_import_event.dart';
part 'library_import_state.dart';

/// Drives the bulk library-import flow: uploading screenshots, reviewing the
/// extracted candidates, and bulk-confirming the chosen titles.
class LibraryImportBloc extends Bloc<LibraryImportEvent, LibraryImportState> {
  LibraryImportBloc({required CaptureRepository captureRepository})
    : _captureRepository = captureRepository,
      super(const LibraryImportInitial()) {
    on<SubmitLibraryImport>(_onSubmit);
    on<BulkConfirmImport>(_onBulkConfirm);
  }

  final CaptureRepository _captureRepository;

  Future<void> _onSubmit(
    SubmitLibraryImport event,
    Emitter<LibraryImportState> emit,
  ) async {
    emit(const LibraryImportSubmitting());

    try {
      final capture = await _captureRepository.submitLibraryImport(
        event.imagePaths,
      );
      emit(LibraryImportReview(capture: capture));
    } on DioException catch (e) {
      emit(LibraryImportError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LibraryImportError(message: e.toString()));
    }
  }

  Future<void> _onBulkConfirm(
    BulkConfirmImport event,
    Emitter<LibraryImportState> emit,
  ) async {
    emit(const LibraryImportConfirming());

    try {
      final result = await _captureRepository.bulkConfirmCandidates(
        event.captureId,
        event.confirmIds,
        event.platformId,
        status: event.status,
      );
      emit(
        LibraryImportDone(
          confirmed: result.confirmed,
          rejected: result.rejected,
        ),
      );
    } on DioException catch (e) {
      emit(LibraryImportError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(LibraryImportError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
