import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:logger/logger.dart';

part 'capture_event.dart';
part 'capture_state.dart';

class CaptureBloc extends Bloc<CaptureEvent, CaptureState> {
  CaptureBloc({required CaptureRepository captureRepository})
    : _captureRepository = captureRepository,
      super(const CaptureInitial()) {
    on<LoadCaptures>(_onLoadCaptures);
    on<SubmitTextCapture>(_onSubmitTextCapture);
    on<SubmitVoiceCapture>(_onSubmitVoiceCapture);
    on<TranscribeAudio>(_onTranscribeAudio);
    on<SubmitPhotoCapture>(_onSubmitPhotoCapture);
    on<ConfirmCandidate>(_onConfirmCandidate);
    on<RejectCandidate>(_onRejectCandidate);
  }

  final CaptureRepository _captureRepository;
  final Logger _logger = Logger(printer: PrettyPrinter(methodCount: 0));

  Future<void> _onLoadCaptures(
    LoadCaptures event,
    Emitter<CaptureState> emit,
  ) async {
    emit(const CaptureLoading());

    try {
      final response = await _captureRepository.listCaptures(
        status: event.status,
      );

      emit(CaptureLoaded(captures: response.items, total: response.total));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onSubmitTextCapture(
    SubmitTextCapture event,
    Emitter<CaptureState> emit,
  ) async {
    emit(const CaptureSubmitting());

    try {
      final capture = await _captureRepository.submitText(event.rawText);
      emit(CaptureSubmitted(capture: capture));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onTranscribeAudio(
    TranscribeAudio event,
    Emitter<CaptureState> emit,
  ) async {
    emit(const CaptureTranscribing());

    try {
      final result = await _captureRepository.transcribeAudio(event.filePath);
      emit(CaptureTranscribed(text: result.text));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onSubmitVoiceCapture(
    SubmitVoiceCapture event,
    Emitter<CaptureState> emit,
  ) async {
    emit(const CaptureSubmitting());

    try {
      final capture = await _captureRepository.submitText(
        event.rawText,
        inputType: 'voice',
      );
      emit(CaptureSubmitted(capture: capture));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onSubmitPhotoCapture(
    SubmitPhotoCapture event,
    Emitter<CaptureState> emit,
  ) async {
    emit(const CaptureSubmitting());

    try {
      final capture = await _captureRepository.submitPhoto(event.imagePath);
      emit(CaptureSubmitted(capture: capture));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onConfirmCandidate(
    ConfirmCandidate event,
    Emitter<CaptureState> emit,
  ) async {
    try {
      await _captureRepository.confirmCandidate(
        event.captureId,
        event.candidateId,
        event.platformId,
        status: event.status,
      );

      // Re-fetch the capture to get updated candidate statuses.
      final capture = await _captureRepository.getCapture(event.captureId);
      emit(CaptureSubmitted(capture: capture));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      _logger.w('Confirm candidate failed: $message');
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
    }
  }

  Future<void> _onRejectCandidate(
    RejectCandidate event,
    Emitter<CaptureState> emit,
  ) async {
    try {
      await _captureRepository.rejectCandidate(
        event.captureId,
        event.candidateId,
      );

      // Re-fetch the capture to get updated candidate statuses.
      final capture = await _captureRepository.getCapture(event.captureId);
      emit(CaptureSubmitted(capture: capture));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      _logger.w('Reject candidate failed: $message');
      emit(CaptureError(message: message));
    } on Exception catch (e) {
      emit(CaptureError(message: e.toString()));
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
