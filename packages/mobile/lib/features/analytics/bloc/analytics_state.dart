part of 'analytics_bloc.dart';

sealed class AnalyticsState extends Equatable {
  const AnalyticsState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any analytics data has been loaded.
final class AnalyticsInitial extends AnalyticsState {
  const AnalyticsInitial();
}

/// An analytics operation is in progress.
final class AnalyticsLoading extends AnalyticsState {
  const AnalyticsLoading();
}

/// All analytics data has been loaded successfully.
final class AnalyticsLoaded extends AnalyticsState {
  const AnalyticsLoaded({
    required this.overview,
    required this.heatmap,
    required this.genreStats,
    required this.platformStats,
    this.timelineItems = const [],
    this.timelineTotal = 0,
    this.isLoadingMoreTimeline = false,
    this.loadMoreTimelineError,
  });

  final StatsOverview overview;
  final PlayHeatmap heatmap;
  final GenreStats genreStats;
  final PlatformStats platformStats;
  final List<TimelineEntry> timelineItems;
  final int timelineTotal;
  final bool isLoadingMoreTimeline;

  /// Error message from a failed timeline "load more" page fetch.
  ///
  /// Surfaced inline so the dashboard stays visible. A full-screen
  /// [AnalyticsError] is reserved for the initial load failure.
  final String? loadMoreTimelineError;

  bool get hasMoreTimeline => timelineItems.length < timelineTotal;

  AnalyticsLoaded copyWith({
    StatsOverview? overview,
    PlayHeatmap? heatmap,
    GenreStats? genreStats,
    PlatformStats? platformStats,
    List<TimelineEntry>? timelineItems,
    int? timelineTotal,
    bool? isLoadingMoreTimeline,
    String? loadMoreTimelineError,
  }) {
    return AnalyticsLoaded(
      overview: overview ?? this.overview,
      heatmap: heatmap ?? this.heatmap,
      genreStats: genreStats ?? this.genreStats,
      platformStats: platformStats ?? this.platformStats,
      timelineItems: timelineItems ?? this.timelineItems,
      timelineTotal: timelineTotal ?? this.timelineTotal,
      isLoadingMoreTimeline:
          isLoadingMoreTimeline ?? this.isLoadingMoreTimeline,
      loadMoreTimelineError: loadMoreTimelineError,
    );
  }

  @override
  List<Object?> get props => [
    overview,
    heatmap,
    genreStats,
    platformStats,
    timelineItems,
    timelineTotal,
    isLoadingMoreTimeline,
    loadMoreTimelineError,
  ];
}

/// An analytics operation failed.
final class AnalyticsError extends AnalyticsState {
  const AnalyticsError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
