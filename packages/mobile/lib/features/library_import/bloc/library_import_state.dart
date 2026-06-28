part of 'library_import_bloc.dart';

sealed class LibraryImportState extends Equatable {
  const LibraryImportState();

  @override
  List<Object?> get props => [];
}

/// Nothing uploaded yet.
final class LibraryImportInitial extends LibraryImportState {
  const LibraryImportInitial();
}

/// Screenshots are uploading / being extracted.
final class LibraryImportSubmitting extends LibraryImportState {
  const LibraryImportSubmitting();
}

/// Extraction returned a capture with candidates ready for review.
final class LibraryImportReview extends LibraryImportState {
  const LibraryImportReview({required this.capture});

  final Capture capture;

  @override
  List<Object?> get props => [capture];
}

/// A bulk-confirm request is in flight.
final class LibraryImportConfirming extends LibraryImportState {
  const LibraryImportConfirming();
}

/// Bulk-confirm completed.
final class LibraryImportDone extends LibraryImportState {
  const LibraryImportDone({required this.confirmed, required this.rejected});

  final int confirmed;
  final int rejected;

  @override
  List<Object?> get props => [confirmed, rejected];
}

/// Something went wrong during upload or confirmation.
final class LibraryImportError extends LibraryImportState {
  const LibraryImportError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
