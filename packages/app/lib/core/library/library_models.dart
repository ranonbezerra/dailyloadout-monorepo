import 'package:equatable/equatable.dart';

/// Represents a gaming platform (e.g. PS5, Nintendo Switch).
class Platform extends Equatable {
  const Platform({
    required this.id,
    required this.slug,
    required this.label,
    required this.family,
  });

  factory Platform.fromJson(Map<String, dynamic> json) {
    return Platform(
      id: json['id'] as int,
      slug: json['slug'] as String,
      label: json['label'] as String,
      family: json['family'] as String,
    );
  }

  final int id;
  final String slug;
  final String label;
  final String family;

  @override
  List<Object?> get props => [id, slug, label, family];
}

/// Represents a game in the catalog.
class Game extends Equatable {
  const Game({
    required this.publicId,
    required this.slug,
    required this.title,
    required this.metadataSource,
    required this.createdAt,
    this.igdbId,
    this.summary,
    this.coverUrl,
    this.firstReleaseDate,
    this.genres,
  });

  factory Game.fromJson(Map<String, dynamic> json) {
    return Game(
      publicId: json['public_id'] as String,
      slug: json['slug'] as String,
      title: json['title'] as String,
      igdbId: json['igdb_id'] as int?,
      summary: json['summary'] as String?,
      coverUrl: json['cover_url'] as String?,
      firstReleaseDate: json['first_release_date'] != null
          ? DateTime.parse(json['first_release_date'] as String)
          : null,
      genres: (json['genres'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      metadataSource: json['metadata_source'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String publicId;
  final String slug;
  final String title;
  final int? igdbId;
  final String? summary;
  final String? coverUrl;
  final DateTime? firstReleaseDate;
  final List<String>? genres;
  final String metadataSource;
  final DateTime createdAt;

  @override
  List<Object?> get props => [
    publicId,
    slug,
    title,
    igdbId,
    summary,
    coverUrl,
    firstReleaseDate,
    genres,
    metadataSource,
    createdAt,
  ];
}

/// Represents a game entry in the user's library.
class LibraryEntry extends Equatable {
  const LibraryEntry({
    required this.publicId,
    required this.game,
    required this.platform,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.acquiredAt,
    this.lastPlayedAt,
    this.missionNextAction,
    this.notes,
  });

  factory LibraryEntry.fromJson(Map<String, dynamic> json) {
    return LibraryEntry(
      publicId: json['public_id'] as String,
      game: Game.fromJson(json['game'] as Map<String, dynamic>),
      platform: Platform.fromJson(json['platform'] as Map<String, dynamic>),
      status: json['status'] as String,
      acquiredAt: json['acquired_at'] != null
          ? DateTime.parse(json['acquired_at'] as String)
          : null,
      lastPlayedAt: json['last_played_at'] != null
          ? DateTime.parse(json['last_played_at'] as String)
          : null,
      missionNextAction: json['mission_next_action'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  final String publicId;
  final Game game;
  final Platform platform;
  final String status;
  final DateTime? acquiredAt;
  final DateTime? lastPlayedAt;
  final String? missionNextAction;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  @override
  List<Object?> get props => [
    publicId,
    game,
    platform,
    status,
    acquiredAt,
    lastPlayedAt,
    missionNextAction,
    notes,
    createdAt,
    updatedAt,
  ];
}

/// Per-platform state for an owned game.
///
/// `publicId` is the library ENTRY id — the target for update, delete, and
/// mission-start operations on this specific platform.
class LibraryPlatformState extends Equatable {
  const LibraryPlatformState({
    required this.publicId,
    required this.platform,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.acquiredAt,
    this.lastPlayedAt,
    this.missionNextAction,
    this.notes,
  });

  factory LibraryPlatformState.fromJson(Map<String, dynamic> json) {
    return LibraryPlatformState(
      publicId: json['public_id'] as String,
      platform: Platform.fromJson(json['platform'] as Map<String, dynamic>),
      status: json['status'] as String,
      acquiredAt: json['acquired_at'] != null
          ? DateTime.parse(json['acquired_at'] as String)
          : null,
      lastPlayedAt: json['last_played_at'] != null
          ? DateTime.parse(json['last_played_at'] as String)
          : null,
      missionNextAction: json['mission_next_action'] as String?,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  final String publicId;
  final Platform platform;
  final String status;
  final DateTime? acquiredAt;
  final DateTime? lastPlayedAt;
  final String? missionNextAction;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  @override
  List<Object?> get props => [
    publicId,
    platform,
    status,
    acquiredAt,
    lastPlayedAt,
    missionNextAction,
    notes,
    createdAt,
    updatedAt,
  ];
}

/// A single game owned across one or more platforms.
///
/// The backend groups library rows by game; the client renders this shape
/// as-is without any further grouping or aggregation.
class LibraryGameGroup extends Equatable {
  const LibraryGameGroup({required this.game, required this.platforms});

  factory LibraryGameGroup.fromJson(Map<String, dynamic> json) {
    return LibraryGameGroup(
      game: Game.fromJson(json['game'] as Map<String, dynamic>),
      platforms: (json['platforms'] as List<dynamic>)
          .map((e) => LibraryPlatformState.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final Game game;
  final List<LibraryPlatformState> platforms;

  @override
  List<Object?> get props => [game, platforms];
}

/// Paginated response for the grouped library.
///
/// `total` is the count of distinct GAMES (pagination is by game).
class LibraryListResponse extends Equatable {
  const LibraryListResponse({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  factory LibraryListResponse.fromJson(Map<String, dynamic> json) {
    return LibraryListResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => LibraryGameGroup.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      limit: json['limit'] as int,
      offset: json['offset'] as int,
    );
  }

  final List<LibraryGameGroup> items;
  final int total;
  final int limit;
  final int offset;

  @override
  List<Object?> get props => [items, total, limit, offset];
}
