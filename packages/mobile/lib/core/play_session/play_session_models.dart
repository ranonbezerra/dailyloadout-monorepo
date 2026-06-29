import 'package:app/core/library/library_models.dart';
import 'package:equatable/equatable.dart';

/// Contextual information from the last playSession session.
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

/// Represents a full playSession with recap, wrapUp, and session context.
class PlaySession extends Equatable {
  const PlaySession({
    required this.publicId,
    required this.libraryEntry,
    required this.playSessionType,
    required this.startedAt,
    required this.createdAt,
    required this.updatedAt,
    this.recapText,
    this.wrapUpText,
    this.extractedState,
    this.endedVia,
    this.endedAt,
    this.lastSessionContext,
  });

  factory PlaySession.fromJson(Map<String, dynamic> json) {
    return PlaySession(
      publicId: json['public_id'] as String,
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      playSessionType: json['play_session_type'] as String,
      recapText: json['recap_text'] as String?,
      wrapUpText: json['wrap_up_text'] as String?,
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
  final String playSessionType;
  final String? recapText;
  final String? wrapUpText;
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
    playSessionType,
    recapText,
    wrapUpText,
    extractedState,
    endedVia,
    startedAt,
    endedAt,
    createdAt,
    updatedAt,
    lastSessionContext,
  ];
}

/// Lightweight playSession item for list views.
class PlaySessionListItem extends Equatable {
  const PlaySessionListItem({
    required this.publicId,
    required this.libraryEntry,
    required this.playSessionType,
    required this.startedAt,
    this.endedVia,
    this.endedAt,
  });

  factory PlaySessionListItem.fromJson(Map<String, dynamic> json) {
    return PlaySessionListItem(
      publicId: json['public_id'] as String,
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      playSessionType: json['play_session_type'] as String,
      endedVia: json['ended_via'] as String?,
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] != null
          ? DateTime.parse(json['ended_at'] as String)
          : null,
    );
  }

  final String publicId;
  final LibraryEntry libraryEntry;
  final String playSessionType;
  final String? endedVia;
  final DateTime startedAt;
  final DateTime? endedAt;

  @override
  List<Object?> get props => [
    publicId,
    libraryEntry,
    playSessionType,
    endedVia,
    startedAt,
    endedAt,
  ];
}

/// Paginated response for playSession listings.
class PlaySessionListResponse extends Equatable {
  const PlaySessionListResponse({required this.items, required this.total});

  factory PlaySessionListResponse.fromJson(Map<String, dynamic> json) {
    return PlaySessionListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => PlaySessionListItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  final List<PlaySessionListItem> items;
  final int total;

  @override
  List<Object?> get props => [items, total];
}

/// Preview returned before starting a playSession, including recap text.
class RecapPreview extends Equatable {
  const RecapPreview({
    required this.libraryEntry,
    this.recapText,
    this.lastSessionContext,
  });

  factory RecapPreview.fromJson(Map<String, dynamic> json) {
    return RecapPreview(
      libraryEntry: LibraryEntry.fromJson(
        json['library_entry'] as Map<String, dynamic>,
      ),
      recapText: json['recap_text'] as String?,
      lastSessionContext: json['last_session_context'] != null
          ? SessionContext.fromJson(
              json['last_session_context'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  final LibraryEntry libraryEntry;
  final String? recapText;
  final SessionContext? lastSessionContext;

  @override
  List<Object?> get props => [libraryEntry, recapText, lastSessionContext];
}
