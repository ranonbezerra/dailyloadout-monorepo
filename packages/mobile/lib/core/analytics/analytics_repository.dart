import 'package:app/core/analytics/analytics_models.dart';
import 'package:app/core/api/api_client.dart';

/// Provides high-level analytics operations backed by the API.
class AnalyticsRepository {
  AnalyticsRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Fetches the high-level stats overview for the current user.
  Future<StatsOverview> getOverview() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/stats/overview',
    );
    return StatsOverview.fromJson(response.data!);
  }

  /// Fetches the play heatmap, optionally filtered by date range.
  Future<PlayHeatmap> getPlayHeatmap({String? from, String? to}) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/stats/play-heatmap',
      queryParameters: {
        if (from != null) 'from': from,
        if (to != null) 'to': to,
      },
    );
    return PlayHeatmap.fromJson(response.data!);
  }

  /// Fetches genre-level aggregated statistics.
  Future<GenreStats> getGenreStats() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/stats/genres',
    );
    return GenreStats.fromJson(response.data!);
  }

  /// Fetches platform-level aggregated statistics.
  Future<PlatformStats> getPlatformStats() async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/stats/platforms',
    );
    return PlatformStats.fromJson(response.data!);
  }

  /// Fetches the paginated playSession timeline.
  Future<TimelineResponse> getTimeline({int limit = 20, int offset = 0}) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/stats/timeline',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return TimelineResponse.fromJson(response.data!);
  }
}
