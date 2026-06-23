import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

part 'analytics_event.dart';
part 'analytics_state.dart';

class AnalyticsBloc extends Bloc<AnalyticsEvent, AnalyticsState> {
  AnalyticsBloc({required AnalyticsRepository analyticsRepository})
    : _analyticsRepository = analyticsRepository,
      super(const AnalyticsInitial()) {
    on<LoadAnalytics>(_onLoadAnalytics);
    on<LoadTimeline>(_onLoadTimeline);
    on<LoadMoreTimeline>(_onLoadMoreTimeline);
  }

  final AnalyticsRepository _analyticsRepository;

  Future<void> _onLoadAnalytics(
    LoadAnalytics event,
    Emitter<AnalyticsState> emit,
  ) async {
    emit(const AnalyticsLoading());

    try {
      final results = await Future.wait([
        _analyticsRepository.getOverview(),
        _analyticsRepository.getPlayHeatmap(),
        _analyticsRepository.getGenreStats(),
        _analyticsRepository.getPlatformStats(),
      ]);

      emit(
        AnalyticsLoaded(
          overview: results[0] as StatsOverview,
          heatmap: results[1] as PlayHeatmap,
          genreStats: results[2] as GenreStats,
          platformStats: results[3] as PlatformStats,
        ),
      );
    } on DioException catch (e) {
      emit(AnalyticsError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(AnalyticsError(message: e.toString()));
    }
  }

  Future<void> _onLoadTimeline(
    LoadTimeline event,
    Emitter<AnalyticsState> emit,
  ) async {
    final currentState = state;

    // If we already have analytics data, preserve it while loading timeline.
    if (currentState is! AnalyticsLoaded) {
      emit(const AnalyticsLoading());
    }

    try {
      final response = await _analyticsRepository.getTimeline();

      if (currentState is AnalyticsLoaded) {
        emit(
          currentState.copyWith(
            timelineItems: response.items,
            timelineTotal: response.total,
            isLoadingMoreTimeline: false,
          ),
        );
      }
    } on DioException catch (e) {
      emit(AnalyticsError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(AnalyticsError(message: e.toString()));
    }
  }

  Future<void> _onLoadMoreTimeline(
    LoadMoreTimeline event,
    Emitter<AnalyticsState> emit,
  ) async {
    final currentState = state;
    if (currentState is! AnalyticsLoaded || !currentState.hasMoreTimeline) {
      return;
    }
    if (currentState.isLoadingMoreTimeline) return;

    emit(currentState.copyWith(isLoadingMoreTimeline: true));

    try {
      final response = await _analyticsRepository.getTimeline(
        offset: currentState.timelineItems.length,
      );

      emit(
        currentState.copyWith(
          timelineItems: [...currentState.timelineItems, ...response.items],
          timelineTotal: response.total,
          isLoadingMoreTimeline: false,
        ),
      );
    } on DioException catch (e) {
      emit(currentState.copyWith(isLoadingMoreTimeline: false));
      emit(AnalyticsError(message: _extractErrorMessage(e)));
    } on Exception catch (e) {
      emit(currentState.copyWith(isLoadingMoreTimeline: false));
      emit(AnalyticsError(message: e.toString()));
    }
  }

  String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
