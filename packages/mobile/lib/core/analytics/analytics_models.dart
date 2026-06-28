import 'package:equatable/equatable.dart';

/// High-level stats overview for the current user.
class StatsOverview extends Equatable {
  const StatsOverview({
    required this.totalGames,
    required this.statusCounts,
    required this.missionsLast30d,
    required this.userCreatedAt,
    this.avgMissionDurationMinutes,
  });

  factory StatsOverview.fromJson(Map<String, dynamic> json) {
    return StatsOverview(
      totalGames: json['total_games'] as int,
      statusCounts: (json['status_counts'] as Map<String, dynamic>).map(
        (key, value) => MapEntry(key, value as int),
      ),
      missionsLast30d: json['missions_last_30d'] as int,
      avgMissionDurationMinutes: (json['avg_mission_duration_minutes'] as num?)
          ?.toDouble(),
      userCreatedAt: DateTime.parse(json['user_created_at'] as String),
    );
  }

  final int totalGames;
  final Map<String, int> statusCounts;
  final int missionsLast30d;
  final double? avgMissionDurationMinutes;
  final DateTime userCreatedAt;

  @override
  List<Object?> get props => [
    totalGames,
    statusCounts,
    missionsLast30d,
    avgMissionDurationMinutes,
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
    required this.missionCount,
  });

  factory GenreStat.fromJson(Map<String, dynamic> json) {
    return GenreStat(
      genre: json['genre'] as String,
      totalMinutes: json['total_minutes'] as int,
      missionCount: json['mission_count'] as int,
    );
  }

  final String genre;
  final int totalMinutes;
  final int missionCount;

  @override
  List<Object?> get props => [genre, totalMinutes, missionCount];
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
    required this.missionCount,
    required this.totalMinutes,
  });

  factory PlatformStat.fromJson(Map<String, dynamic> json) {
    return PlatformStat(
      platformSlug: json['platform_slug'] as String,
      platformLabel: json['platform_label'] as String,
      gameCount: json['game_count'] as int,
      missionCount: json['mission_count'] as int,
      totalMinutes: json['total_minutes'] as int,
    );
  }

  final String platformSlug;
  final String platformLabel;
  final int gameCount;
  final int missionCount;
  final int totalMinutes;

  @override
  List<Object?> get props => [
    platformSlug,
    platformLabel,
    gameCount,
    missionCount,
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

/// A single mission entry in the timeline view.
class TimelineEntry extends Equatable {
  const TimelineEntry({
    required this.publicId,
    required this.gameTitle,
    required this.platformLabel,
    required this.missionType,
    required this.startedAt,
    this.briefingText,
    this.debriefText,
    this.endedVia,
    this.endedAt,
    this.durationMinutes,
  });

  factory TimelineEntry.fromJson(Map<String, dynamic> json) {
    return TimelineEntry(
      publicId: json['public_id'] as String,
      gameTitle: json['game_title'] as String,
      platformLabel: json['platform_label'] as String,
      missionType: json['mission_type'] as String,
      briefingText: json['briefing_text'] as String?,
      debriefText: json['debrief_text'] as String?,
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
  final String missionType;
  final String? briefingText;
  final String? debriefText;
  final String? endedVia;
  final DateTime startedAt;
  final DateTime? endedAt;
  final int? durationMinutes;

  @override
  List<Object?> get props => [
    publicId,
    gameTitle,
    platformLabel,
    missionType,
    briefingText,
    debriefText,
    endedVia,
    startedAt,
    endedAt,
    durationMinutes,
  ];
}

/// Paginated response for mission timeline.
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
