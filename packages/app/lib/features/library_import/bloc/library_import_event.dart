part of 'library_import_bloc.dart';

sealed class LibraryImportEvent extends Equatable {
  const LibraryImportEvent();

  @override
  List<Object?> get props => [];
}

/// Uploads the selected screenshots for bulk extraction.
final class SubmitLibraryImport extends LibraryImportEvent {
  const SubmitLibraryImport({required this.imagePaths});

  final List<String> imagePaths;

  @override
  List<Object?> get props => [imagePaths];
}

/// Confirms the checked candidates against a platform and status.
final class BulkConfirmImport extends LibraryImportEvent {
  const BulkConfirmImport({
    required this.captureId,
    required this.confirmIds,
    required this.platformId,
    this.status = 'backlog',
  });

  final String captureId;
  final List<String> confirmIds;
  final int platformId;
  final String status;

  @override
  List<Object?> get props => [captureId, confirmIds, platformId, status];
}
