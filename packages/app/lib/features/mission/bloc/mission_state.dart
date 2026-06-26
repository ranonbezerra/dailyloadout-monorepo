part of 'mission_bloc.dart';

sealed class MissionState extends Equatable {
  const MissionState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any mission data has been loaded.
final class MissionInitial extends MissionState {
  const MissionInitial();
}

/// A mission operation is in progress.
final class MissionLoading extends MissionState {
  const MissionLoading();
}

/// Mission list has been loaded successfully.
final class MissionListLoaded extends MissionState {
  const MissionListLoaded({
    required this.missions,
    required this.total,
    this.isLoadingMore = false,
    this.loadMoreError,
  });

  final List<MissionListItem> missions;
  final int total;
  final bool isLoadingMore;

  /// Error message from a failed "load more" page fetch.
  ///
  /// Surfaced inline (snackbar/banner) so the already-loaded list stays
  /// visible. A full-screen [MissionError] is reserved for first-page
  /// load failures.
  final String? loadMoreError;

  bool get hasMore => missions.length < total;

  MissionListLoaded copyWith({
    List<MissionListItem>? missions,
    int? total,
    bool? isLoadingMore,
    String? loadMoreError,
  }) {
    return MissionListLoaded(
      missions: missions ?? this.missions,
      total: total ?? this.total,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      loadMoreError: loadMoreError,
    );
  }

  @override
  List<Object?> get props => [missions, total, isLoadingMore, loadMoreError];
}

/// Active mission has been loaded (null means no active mission).
final class ActiveMissionLoaded extends MissionState {
  const ActiveMissionLoaded({this.mission});

  final Mission? mission;

  @override
  List<Object?> get props => [mission];
}

/// Briefing preview has been loaded successfully.
final class BriefingPreviewLoaded extends MissionState {
  const BriefingPreviewLoaded({required this.preview, this.isDeep = false});

  final BriefingPreview preview;

  /// Whether this preview came from the deep web-researched path.
  final bool isDeep;

  @override
  List<Object?> get props => [preview, isDeep];
}

/// A deep (web-researched) briefing is generating; UI shows progress + cancel.
final class DeepBriefingLoading extends MissionState {
  const DeepBriefingLoading();
}

/// A mission has been started successfully.
final class MissionStarted extends MissionState {
  const MissionStarted({required this.mission});

  final Mission mission;

  @override
  List<Object?> get props => [mission];
}

/// A mission has been ended successfully.
final class MissionEnded extends MissionState {
  const MissionEnded({required this.mission});

  final Mission mission;

  @override
  List<Object?> get props => [mission];
}

/// A mission operation failed.
final class MissionError extends MissionState {
  const MissionError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
