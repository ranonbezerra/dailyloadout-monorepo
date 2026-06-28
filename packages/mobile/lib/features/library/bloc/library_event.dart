part of 'library_bloc.dart';

sealed class LibraryEvent extends Equatable {
  const LibraryEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to load/reload library entries.
final class LoadLibrary extends LibraryEvent {
  const LoadLibrary({this.status, this.limit, this.offset});

  final String? status;
  final int? limit;
  final int? offset;

  @override
  List<Object?> get props => [status, limit, offset];
}

/// Dispatched to add a game to the user's library on one or more platforms.
final class AddEntry extends LibraryEvent {
  const AddEntry({
    required this.gamePublicId,
    required this.platformIds,
    this.status = 'backlog',
    this.notes,
  });

  final String gamePublicId;
  final List<int> platformIds;
  final String status;
  final String? notes;

  @override
  List<Object?> get props => [gamePublicId, platformIds, status, notes];
}

/// Dispatched to update an existing library entry.
final class UpdateEntry extends LibraryEvent {
  const UpdateEntry({required this.publicId, this.status, this.notes});

  final String publicId;
  final String? status;
  final String? notes;

  @override
  List<Object?> get props => [publicId, status, notes];
}

/// Dispatched to delete a library entry.
final class DeleteEntry extends LibraryEvent {
  const DeleteEntry({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// Dispatched to search for games by title.
final class SearchGames extends LibraryEvent {
  const SearchGames({required this.query});

  final String query;

  @override
  List<Object?> get props => [query];
}

/// Dispatched to create a game manually.
final class CreateGame extends LibraryEvent {
  const CreateGame({required this.slug, required this.title});

  final String slug;
  final String title;

  @override
  List<Object?> get props => [slug, title];
}
