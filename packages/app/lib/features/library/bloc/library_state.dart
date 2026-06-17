part of 'library_bloc.dart';

sealed class LibraryState extends Equatable {
  const LibraryState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any library data has been loaded.
final class LibraryInitial extends LibraryState {
  const LibraryInitial();
}

/// A library operation is in progress.
final class LibraryLoading extends LibraryState {
  const LibraryLoading();
}

/// Library entries have been loaded successfully.
final class LibraryLoaded extends LibraryState {
  const LibraryLoaded({
    required this.entries,
    required this.total,
    required this.hasMore,
  });

  final List<LibraryEntry> entries;
  final int total;
  final bool hasMore;

  @override
  List<Object?> get props => [entries, total, hasMore];
}

/// A library operation failed.
final class LibraryError extends LibraryState {
  const LibraryError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
