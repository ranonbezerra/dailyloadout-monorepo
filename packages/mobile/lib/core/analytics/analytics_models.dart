import 'package:equatable/equatable.dart';

/// High-level stats overview for the current user.
class StatsOverview extends Equatable {
  const StatsOverview({
    required this.totalGames,
    required this.statusCounts,
    required this.playSessionsLast30d,
    required this.userCreatedAt,
    this.avgPlaySessionDurationMinutes,
  });

  factory StatsOverview.fromJson(Map<String, dynamic> json) {
    return StatsOverview(
      totalGames: json['total_games'] as int,
      statusCounts: (json['status_counts'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
      playSessionsLast30d: json['play_sessions_last_30d'] as int,
      avgPlaySessionDurationMinutes:
          (json['avg_play_session_duration_minutes'] as num?)?.toDouble(),
      userCreatedAt: DateTime.parse(json['user_created_at'] as String),
    );
  }

  final int totalGames;
  final Map<String, int> statusCounts;
  final int playSessionsLast30d;
  final double? avgPlaySessionDurationMinutes;
  final DateTime userCreatedAt;

  @override
  List<Object?> get props => [
    totalGames,
    statusCounts,
    playSessionsLast30d,
    avgPlaySessionDurationMinutes,
    userCreatedAt,
  ];
}

/// A single day entry in the play heatmap.
class HeatmapDay extends Equatable {
  const HeatmapDay({
    required this.date,
    required this.count,
    required this.totalMinutes,
  });

  factory HeatmapDay.fromJson(Map<String, dynamic> json) {
    return HeatmapDay(
      date: json['date'] as String,
      count: json['count'] as int,
      totalMinutes: json['total_minutes'] as int,
    );
  }

  /// Date in YYYY-MM-DD format.
  final String date;
  final int count;
  final int totalMinutes;

  @override
  List<Object?> get props => [date, count, totalMinutes];
}

/// Play heatmap containing daily play session data.
class PlayHeatmap extends Equatable {
  const PlayHeatmap({required this.days});

  factory PlayHeatmap.fromJson(Map<String, dynamic> json) {
    return PlayHeatmap(
      days: (json['days'] as List<dynamic>)
          .map((e) => HeatmapDay.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final List<HeatmapDay> days;

  @override
  List<Object?> get props => [days];
}

/// Aggregated stats for a single genre.
class GenreStat extends Equatable {
  const GenreStat({
    required this.genre,
    required this.totalMinutes,
    required this.playSessionCount,
  });

  factory GenreStat.fromJson(Map<String, dynamic> json) {
    return GenreStat(
      genre: json['genre'] as String,
      totalMinutes: json['total_minutes'] as int,
      playSessionCount: json['play_session_count'] as int,
    );
  }

  final String genre;
  final int totalMinutes;
  final int playSessionCount;

  @override
  List<Object?> get props => [genre, totalMinutes, playSessionCount];
}

/// Collection of genre-level statistics.
class GenreStats extends Equatable {
  const GenreStats({required this.genres});

  factory GenreStats.fromJson(Map<String, dynamic> json) {
    return GenreStats(
      genres: (json['genres'] as List<dynamic>)
          .map((e) => GenreStat.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final List<GenreStat> genres;

  @override
  List<Object?> get props => [genres];
}

/// Aggregated stats for a single platform.
class PlatformStat extends Equatable {
  const PlatformStat({
    required this.platformSlug,
    required this.platformLabel,
    required this.gameCount,
    required this.playSessionCount,
    required this.totalMinutes,
  });

  factory PlatformStat.fromJson(Map<String, dynamic> json) {
    return PlatformStat(
      platformSlug: json['platform_slug'] as String,
      platformLabel: json['platform_label'] as String,
      gameCount: json['game_count'] as int,
      playSessionCount: json['play_session_count'] as int,
      totalMinutes: json['total_minutes'] as int,
    );
  }

  final String platformSlug;
  final String platformLabel;
  final int gameCount;
  final int playSessionCount;
  final int totalMinutes;

  @override
  List<Object?> get props => [
    platformSlug,
    platformLabel,
    gameCount,
    playSessionCount,
    totalMinutes,
  ];
}

/// Collection of platform-level statistics.
class PlatformStats extends Equatable {
  const PlatformStats({required this.platforms});

  factory PlatformStats.fromJson(Map<String, dynamic> json) {
    return PlatformStats(
      platforms: (json['platforms'] as List<dynamic>)
          .map((e) => PlatformStat.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final List<PlatformStat> platforms;

  @override
  List<Object?> get props => [platforms];
}

/// A single playSession entry in the timeline view.
class TimelineEntry extends Equatable {
  const TimelineEntry({
    required this.publicId,
    required this.gameTitle,
    required this.platformLabel,
    required this.playSessionType,
    required this.startedAt,
    this.recapText,
    this.wrapUpText,
    this.endedVia,
    this.endedAt,
    this.durationMinutes,
  });

  factory TimelineEntry.fromJson(Map<String, dynamic> json) {
    return TimelineEntry(
      publicId: json['public_id'] as String,
      gameTitle: json['game_title'] as String,
      platformLabel: json['platform_label'] as String,
      playSessionType: json['play_session_type'] as String,
      recapText: json['recap_text'] as String?,
      wrapUpText: json['wrap_up_text'] as String?,
      endedVia: json['ended_via'] as String?,
      startedAt: DateTime.parse(json['started_at'] as String),
      endedAt: json['ended_at'] != null
          ? DateTime.parse(json['ended_at'] as String)
          : null,
      durationMinutes: json['duration_minutes'] as int?,
    );
  }

  final String publicId;
  final String gameTitle;
  final String platformLabel;
  final String playSessionType;
  final String? recapText;
  final String? wrapUpText;
  final String? endedVia;
  final DateTime startedAt;
  final DateTime? endedAt;
  final int? durationMinutes;

  @override
  List<Object?> get props => [
    publicId,
    gameTitle,
    platformLabel,
    playSessionType,
    recapText,
    wrapUpText,
    endedVia,
    startedAt,
    endedAt,
    durationMinutes,
  ];
}

/// Paginated response for playSession timeline.
class TimelineResponse extends Equatable {
  const TimelineResponse({required this.items, required this.total});

  factory TimelineResponse.fromJson(Map<String, dynamic> json) {
    return TimelineResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => TimelineEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  final List<TimelineEntry> items;
  final int total;

  @override
  List<Object?> get props => [items, total];
}
