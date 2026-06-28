part of 'capture_bloc.dart';

sealed class CaptureEvent extends Equatable {
  const CaptureEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to load the list of captures.
final class LoadCaptures extends CaptureEvent {
  const LoadCaptures({this.status});

  final String? status;

  @override
  List<Object?> get props => [status];
}

/// Dispatched when the user submits free text for processing.
final class SubmitTextCapture extends CaptureEvent {
  const SubmitTextCapture({required this.rawText});

  final String rawText;

  @override
  List<Object?> get props => [rawText];
}

/// Dispatched when the user submits voice-transcribed (possibly edited) text.
final class SubmitVoiceCapture extends CaptureEvent {
  const SubmitVoiceCapture({required this.rawText});

  final String rawText;

  @override
  List<Object?> get props => [rawText];
}

/// Dispatched when the user uploads audio for transcription.
final class TranscribeAudio extends CaptureEvent {
  const TranscribeAudio({required this.filePath});

  final String filePath;

  @override
  List<Object?> get props => [filePath];
}

/// Dispatched when the user submits a photo for vision processing.
final class SubmitPhotoCapture extends CaptureEvent {
  const SubmitPhotoCapture({required this.imagePath});

  final String imagePath;

  @override
  List<Object?> get props => [imagePath];
}

/// Dispatched when the user confirms a candidate into their library.
final class ConfirmCandidate extends CaptureEvent {
  const ConfirmCandidate({
    required this.captureId,
    required this.candidateId,
    required this.platformId,
    this.status = 'backlog',
  });

  final String captureId;
  final String candidateId;
  final int platformId;
  final String status;

  @override
  List<Object?> get props => [captureId, candidateId, platformId, status];
}

/// Dispatched when the user rejects a candidate.
final class RejectCandidate extends CaptureEvent {
  const RejectCandidate({required this.captureId, required this.candidateId});

  final String captureId;
  final String candidateId;

  @override
  List<Object?> get props => [captureId, candidateId];
}
