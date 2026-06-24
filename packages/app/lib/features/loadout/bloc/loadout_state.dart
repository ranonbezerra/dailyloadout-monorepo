part of 'loadout_bloc.dart';

sealed class LoadoutState extends Equatable {
  const LoadoutState();

  @override
  List<Object?> get props => [];
}

/// Initial state before any loadout data is loaded.
final class LoadoutInitial extends LoadoutState {
  const LoadoutInitial();
}

/// A loadout operation is in progress.
final class LoadoutLoading extends LoadoutState {
  const LoadoutLoading();
}

/// Loadout suggestions have been created.
final class LoadoutResultsLoaded extends LoadoutState {
  const LoadoutResultsLoaded({required this.results});

  final List<Loadout> results;

  @override
  List<Object?> get props => [results];
}

/// A loadout suggestion has been accepted.
final class LoadoutAccepted extends LoadoutState {
  const LoadoutAccepted({required this.loadout});

  final Loadout loadout;

  @override
  List<Object?> get props => [loadout];
}

/// A loadout suggestion has been rejected.
final class LoadoutRejected extends LoadoutState {
  const LoadoutRejected({required this.loadout});

  final Loadout loadout;

  @override
  List<Object?> get props => [loadout];
}

/// A quick briefing is being generated for the loadout [publicId].
final class LoadoutBriefingLoading extends LoadoutState {
  const LoadoutBriefingLoading({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// A quick briefing has been generated for the loadout [publicId].
final class LoadoutBriefingReady extends LoadoutState {
  const LoadoutBriefingReady({
    required this.publicId,
    required this.briefingText,
  });

  final String publicId;
  final String briefingText;

  @override
  List<Object?> get props => [publicId, briefingText];
}

/// Loadout history list has been loaded.
final class LoadoutListLoaded extends LoadoutState {
  const LoadoutListLoaded({required this.loadouts, required this.total});

  final List<LoadoutListItem> loadouts;
  final int total;

  @override
  List<Object?> get props => [loadouts, total];
}

/// Latest pending loadout has been loaded.
final class LatestLoadoutLoaded extends LoadoutState {
  const LatestLoadoutLoaded({this.loadout});

  final Loadout? loadout;

  @override
  List<Object?> get props => [loadout];
}

/// A loadout operation failed.
final class LoadoutError extends LoadoutState {
  const LoadoutError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
