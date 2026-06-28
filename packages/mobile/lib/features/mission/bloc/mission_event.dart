part of 'mission_bloc.dart';

sealed class MissionEvent extends Equatable {
  const MissionEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to load the mission history list.
final class LoadMissions extends MissionEvent {
  const LoadMissions({this.limit, this.offset});

  final int? limit;
  final int? offset;

  @override
  List<Object?> get props => [limit, offset];
}

/// Dispatched to load the next page of missions.
final class LoadMoreMissions extends MissionEvent {
  const LoadMoreMissions();
}

/// Dispatched to load the currently active mission.
final class LoadActiveMission extends MissionEvent {
  const LoadActiveMission();
}

/// Dispatched to preview a briefing before starting a mission.
final class PreviewBriefing extends MissionEvent {
  const PreviewBriefing({
    required this.libraryEntryPublicId,
    this.positionOverride,
    this.mode = 'quick',
  });

  final String libraryEntryPublicId;
  final String? positionOverride;

  /// Briefing mode: `'quick'` (single-shot) or `'deep'` (web-researched).
  final String mode;

  @override
  List<Object?> get props => [libraryEntryPublicId, positionOverride, mode];
}

/// Dispatched to cancel an in-flight deep briefing request.
final class CancelDeepBriefing extends MissionEvent {
  const CancelDeepBriefing({required this.libraryEntryPublicId});

  final String libraryEntryPublicId;

  @override
  List<Object?> get props => [libraryEntryPublicId];
}

/// Dispatched to start a new mission.
final class StartMission extends MissionEvent {
  const StartMission({
    required this.libraryEntryPublicId,
    this.briefingText,
    this.skipBriefing = false,
  });

  final String libraryEntryPublicId;
  final String? briefingText;

  /// Start with no briefing at all (the "just play" path).
  final bool skipBriefing;

  @override
  List<Object?> get props => [libraryEntryPublicId, briefingText, skipBriefing];
}

/// Dispatched to submit a debrief for a mission.
final class SubmitDebrief extends MissionEvent {
  const SubmitDebrief({required this.publicId, required this.debriefText});

  final String publicId;
  final String debriefText;

  @override
  List<Object?> get props => [publicId, debriefText];
}

/// Dispatched to end a mission.
final class EndMission extends MissionEvent {
  const EndMission({required this.publicId, this.endedVia = 'paused_app'});

  final String publicId;
  final String endedVia;

  @override
  List<Object?> get props => [publicId, endedVia];
}

/// Dispatched to submit a retroactive debrief for a library entry.
final class SubmitRetroactiveDebrief extends MissionEvent {
  const SubmitRetroactiveDebrief({
    required this.libraryEntryPublicId,
    required this.debriefText,
  });

  final String libraryEntryPublicId;
  final String debriefText;

  @override
  List<Object?> get props => [libraryEntryPublicId, debriefText];
}

/// Dispatched to regenerate the briefing for an existing mission.
final class RegenerateBriefing extends MissionEvent {
  const RegenerateBriefing({required this.publicId, this.currentPosition});

  final String publicId;
  final String? currentPosition;

  @override
  List<Object?> get props => [publicId, currentPosition];
}
