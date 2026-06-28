part of 'analytics_bloc.dart';

sealed class AnalyticsEvent extends Equatable {
  const AnalyticsEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched to load overview, heatmap, genre, and platform stats.
final class LoadAnalytics extends AnalyticsEvent {
  const LoadAnalytics();
}

/// Dispatched to load the first page of the mission timeline.
final class LoadTimeline extends AnalyticsEvent {
  const LoadTimeline();
}

/// Dispatched to load the next page of the mission timeline.
final class LoadMoreTimeline extends AnalyticsEvent {
  const LoadMoreTimeline();
}
