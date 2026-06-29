part of 'pick_bloc.dart';

sealed class PickState extends Equatable {
  const PickState();

  @override
  List<Object?> get props => [];
}

/// Initial state before any pick data is loaded.
final class PickInitial extends PickState {
  const PickInitial();
}

/// A pick operation is in progress.
final class PickLoading extends PickState {
  const PickLoading();
}

/// Pick suggestions have been created.
final class PickResultsLoaded extends PickState {
  const PickResultsLoaded({required this.results});

  final List<Pick> results;

  @override
  List<Object?> get props => [results];
}

/// A pick suggestion has been accepted.
final class PickAccepted extends PickState {
  const PickAccepted({required this.pick});

  final Pick pick;

  @override
  List<Object?> get props => [pick];
}

/// A pick suggestion has been rejected.
final class PickRejected extends PickState {
  const PickRejected({required this.pick});

  final Pick pick;

  @override
  List<Object?> get props => [pick];
}

/// A quick recap is being generated for the pick [publicId].
final class PickRecapLoading extends PickState {
  const PickRecapLoading({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// A quick recap has been generated for the pick [publicId].
final class PickRecapReady extends PickState {
  const PickRecapReady({required this.publicId, required this.recapText});

  final String publicId;
  final String recapText;

  @override
  List<Object?> get props => [publicId, recapText];
}

/// Pick history list has been loaded.
final class PickListLoaded extends PickState {
  const PickListLoaded({required this.picks, required this.total});

  final List<PickListItem> picks;
  final int total;

  @override
  List<Object?> get props => [picks, total];
}

/// Latest pending pick has been loaded.
final class LatestPickLoaded extends PickState {
  const LatestPickLoaded({this.pick});

  final Pick? pick;

  @override
  List<Object?> get props => [pick];
}

/// A pick operation failed.
final class PickError extends PickState {
  const PickError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
