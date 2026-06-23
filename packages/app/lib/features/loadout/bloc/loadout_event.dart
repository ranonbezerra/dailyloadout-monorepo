part of 'loadout_bloc.dart';

sealed class LoadoutEvent extends Equatable {
  const LoadoutEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to create new loadout suggestions.
final class CreateLoadout extends LoadoutEvent {
  const CreateLoadout({
    required this.mood,
    required this.availableMinutes,
    required this.mentalEnergy,
    this.count = 1,
    this.context,
  });

  final String mood;
  final int availableMinutes;
  final String mentalEnergy;
  final int count;
  final String? context;

  @override
  List<Object?> get props => [
    mood,
    availableMinutes,
    mentalEnergy,
    count,
    context,
  ];
}

/// Dispatched to accept a loadout suggestion.
final class AcceptLoadout extends LoadoutEvent {
  const AcceptLoadout({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// Dispatched to reject a loadout suggestion.
final class RejectLoadout extends LoadoutEvent {
  const RejectLoadout({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// Dispatched to load the loadout history list.
final class LoadLoadouts extends LoadoutEvent {
  const LoadLoadouts({this.limit, this.offset});

  final int? limit;
  final int? offset;

  @override
  List<Object?> get props => [limit, offset];
}

/// Dispatched to load the latest pending loadout.
final class LoadLatestLoadout extends LoadoutEvent {
  const LoadLatestLoadout();
}
