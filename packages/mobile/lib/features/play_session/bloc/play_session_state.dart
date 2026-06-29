part of 'play_session_bloc.dart';

sealed class PlaySessionState extends Equatable {
  const PlaySessionState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any playSession data has been loaded.
final class PlaySessionInitial extends PlaySessionState {
  const PlaySessionInitial();
}

/// A playSession operation is in progress.
final class PlaySessionLoading extends PlaySessionState {
  const PlaySessionLoading();
}

/// PlaySession list has been loaded successfully.
final class PlaySessionListLoaded extends PlaySessionState {
  const PlaySessionListLoaded({
    required this.playSessions,
    required this.total,
    this.isLoadingMore = false,
    this.loadMoreError,
  });

  final List<PlaySessionListItem> playSessions;
  final int total;
  final bool isLoadingMore;

  /// Error message from a failed "load more" page fetch.
  ///
  /// Surfaced inline (snackbar/banner) so the already-loaded list stays
  /// visible. A full-screen [PlaySessionError] is reserved for first-page
  /// load failures.
  final String? loadMoreError;

  bool get hasMore => playSessions.length < total;

  PlaySessionListLoaded copyWith({
    List<PlaySessionListItem>? playSessions,
    int? total,
    bool? isLoadingMore,
    String? loadMoreError,
  }) {
    return PlaySessionListLoaded(
      playSessions: playSessions ?? this.playSessions,
      total: total ?? this.total,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      loadMoreError: loadMoreError,
    );
  }

  @override
  List<Object?> get props => [
    playSessions,
    total,
    isLoadingMore,
    loadMoreError,
  ];
}

/// Active session has been loaded (null means no active playSession).
final class ActivePlaySessionLoaded extends PlaySessionState {
  const ActivePlaySessionLoaded({this.playSession});

  final PlaySession? playSession;

  @override
  List<Object?> get props => [playSession];
}

/// Recap preview has been loaded successfully.
final class RecapPreviewLoaded extends PlaySessionState {
  const RecapPreviewLoaded({required this.preview, this.isDeep = false});

  final RecapPreview preview;

  /// Whether this preview came from the deep web-researched path.
  final bool isDeep;

  @override
  List<Object?> get props => [preview, isDeep];
}

/// A deep (web-researched) recap is generating; UI shows progress + cancel.
final class DeepRecapLoading extends PlaySessionState {
  const DeepRecapLoading();
}

/// A playSession has been started successfully.
final class PlaySessionStarted extends PlaySessionState {
  const PlaySessionStarted({required this.playSession});

  final PlaySession playSession;

  @override
  List<Object?> get props => [playSession];
}

/// A playSession has been ended successfully.
final class PlaySessionEnded extends PlaySessionState {
  const PlaySessionEnded({required this.playSession});

  final PlaySession playSession;

  @override
  List<Object?> get props => [playSession];
}

/// A playSession operation failed.
final class PlaySessionError extends PlaySessionState {
  const PlaySessionError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
