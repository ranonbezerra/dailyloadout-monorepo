part of 'capture_bloc.dart';

sealed class CaptureState extends Equatable {
  const CaptureState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any capture operation has been performed.
final class CaptureInitial extends CaptureState {
  const CaptureInitial();
}

/// A capture list is being loaded.
final class CaptureLoading extends CaptureState {
  const CaptureLoading();
}

/// Capture list has been loaded successfully.
final class CaptureLoaded extends CaptureState {
  const CaptureLoaded({required this.captures, required this.total});

  final List<Capture> captures;
  final int total;

  @override
  List<Object?> get props => [captures, total];
}

/// A text capture is being submitted and processed.
final class CaptureSubmitting extends CaptureState {
  const CaptureSubmitting();
}

/// A capture has been submitted and candidates are ready for review.
final class CaptureSubmitted extends CaptureState {
  const CaptureSubmitted({required this.capture});

  final Capture capture;

  @override
  List<Object?> get props => [capture];
}

/// Audio is being transcribed.
final class CaptureTranscribing extends CaptureState {
  const CaptureTranscribing();
}

/// Audio transcription is complete; the text is ready for review/editing.
final class CaptureTranscribed extends CaptureState {
  const CaptureTranscribed({required this.text});

  final String text;

  @override
  List<Object?> get props => [text];
}

/// A capture operation failed.
final class CaptureError extends CaptureState {
  const CaptureError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
