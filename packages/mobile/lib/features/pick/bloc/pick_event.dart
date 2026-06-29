part of 'pick_bloc.dart';

sealed class PickEvent extends Equatable {
  const PickEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to create new pick suggestions.
final class CreatePick extends PickEvent {
  const CreatePick({
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

/// Dispatched to accept a pick suggestion.
///
/// When [recapText] is provided, the auto-started playSession carries that
/// recap (see [GeneratePickRecap]).
final class AcceptPick extends PickEvent {
  const AcceptPick({required this.publicId, this.recapText});

  final String publicId;
  final String? recapText;

  @override
  List<Object?> get props => [publicId, recapText];
}

/// Dispatched to generate a quick recap for a pick's game before
/// starting the playSession. The picked library entry is identified by
/// [libraryEntryPublicId]; [publicId] is the pick being actioned.
final class GeneratePickRecap extends PickEvent {
  const GeneratePickRecap({
    required this.publicId,
    required this.libraryEntryPublicId,
    this.mode = 'quick',
  });

  final String publicId;
  final String libraryEntryPublicId;

  /// 'quick' (single-shot) or 'deep' (web-researched).
  final String mode;

  @override
  List<Object?> get props => [publicId, libraryEntryPublicId, mode];
}

/// Dispatched to reject a pick suggestion.
final class RejectPick extends PickEvent {
  const RejectPick({required this.publicId});

  final String publicId;

  @override
  List<Object?> get props => [publicId];
}

/// Dispatched to load the pick history list.
final class LoadPicks extends PickEvent {
  const LoadPicks({this.limit, this.offset});

  final int? limit;
  final int? offset;

  @override
  List<Object?> get props => [limit, offset];
}

/// Dispatched to load the latest pending pick.
final class LoadLatestPick extends PickEvent {
  const LoadLatestPick();
}
