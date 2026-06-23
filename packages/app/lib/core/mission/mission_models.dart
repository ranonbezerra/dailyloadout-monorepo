import 'package:app/core/library/library_models.dart';
import 'package:equatable/equatable.dart';

/// Contextual information from the last mission session.
class SessionContext extends Equatable {
  const SessionContext({
    this.location,
    this.nextAction,
    this.level,
    this.currentQuest,
  });

  factory SessionContext.fromJson(Map<String, dynamic> json) {
    return SessionContext(
      location: json['location'] as String?,
      nextAction: json['next_action'] as String?,
      level: json['level'] as String?,
      currentQuest: json['current_quest'] as String?,
    );
  }

  final String? location;
  final String? nextAction;
  final String? level;
  final String? currentQuest;

  @override
  List<Object?> get props => [location, nextAction, level, currentQuest];
}

/// Represents a full mission with briefing, debrief, and session context.
class Mission extends Equatable {
  const Mission({
    required this.publicId,
    required this.libraryEntry,
    required this.missionType,
    required this.startedAt,
    required this.createdAt,
    required this.updatedAt,
    this.briefingText,
    this.debriefText,
    this.extractedState,
    this.endedVia,
    this.endedAt,
    this.lastSessionContext,
  });

  factory Mission.fromJson(Map<String, dynamic> json) {
    return Mission(
      publicId: json['public_id'] as String,
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      missionType: json['mission_type'] as String,
      briefingText: json['briefing_text'] as String?,
      debriefText: json['debrief_text'] as String?,
      extractedState: json['extracted_state'] as Map<String, dynamic>?,
      endedVia: json['ended_via'] as String?,
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] != null
          ? DateTime.parse(json['ended_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      lastSessionContext: json['last_session_context'] != null
          ? SessionContext.fromJson(
              json['last_session_context'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  final String publicId;
  final LibraryEntry libraryEntry;
  final String missionType;
  final String? briefingText;
  final String? debriefText;
  final Map<String, dynamic>? extractedState;
  final String? endedVia;
  final DateTime startedAt;
  final DateTime? endedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
  final SessionContext? lastSessionContext;

  @override
  List<Object?> get props => [
    publicId,
    libraryEntry,
    missionType,
    briefingText,
    debriefText,
    extractedState,
    endedVia,
    startedAt,
    endedAt,
    createdAt,
    updatedAt,
    lastSessionContext,
  ];
}

/// Lightweight mission item for list views.
class MissionListItem extends Equatable {
  const MissionListItem({
    required this.publicId,
    required this.libraryEntry,
    required this.missionType,
    required this.startedAt,
    this.endedVia,
    this.endedAt,
  });

  factory MissionListItem.fromJson(Map<String, dynamic> json) {
    return MissionListItem(
      publicId: json['public_id'] as String,
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      missionType: json['mission_type'] as String,
      endedVia: json['ended_via'] as String?,
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] != null
          ? DateTime.parse(json['ended_at'] as String)
          : null,
    );
  }

  final String publicId;
  final LibraryEntry libraryEntry;
  final String missionType;
  final String? endedVia;
  final DateTime startedAt;
  final DateTime? endedAt;

  @override
  List<Object?> get props => [
    publicId,
    libraryEntry,
    missionType,
    endedVia,
    startedAt,
    endedAt,
  ];
}

/// Paginated response for mission listings.
class MissionListResponse extends Equatable {
  const MissionListResponse({required this.items, required this.total});

  factory MissionListResponse.fromJson(Map<String, dynamic> json) {
    return MissionListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => MissionListItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  final List<MissionListItem> items;
  final int total;

  @override
  List<Object?> get props => [items, total];
}

/// Preview returned before starting a mission, including briefing text.
class BriefingPreview extends Equatable {
  const BriefingPreview({
    required this.libraryEntry,
    this.briefingText,
    this.lastSessionContext,
  });

  factory BriefingPreview.fromJson(Map<String, dynamic> json) {
    return BriefingPreview(
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      briefingText: json['briefing_text'] as String?,
      lastSessionContext: json['last_session_context'] != null
          ? SessionContext.fromJson(
              json['last_session_context'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  final LibraryEntry libraryEntry;
  final String? briefingText;
  final SessionContext? lastSessionContext;

  @override
  List<Object?> get props => [libraryEntry, briefingText, lastSessionContext];
}
