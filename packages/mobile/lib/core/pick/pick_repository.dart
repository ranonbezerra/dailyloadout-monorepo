import 'package:app/core/api/api_client.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:dio/dio.dart';

final _llmOptions = Options(receiveTimeout: llmReceiveTimeout);

/// Provides high-level pick operations backed by the API.
class PickRepository {
  PickRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Creates pick suggestions based on the
  /// user's mood, time, and energy level.
  Future<List<Pick>> createPick({
    required String mood,
    required int availableMinutes,
    required String mentalEnergy,
    int count = 1,
    String? context,
  }) async {
    final response = await _apiClient.dio.post<List<dynamic>>(
      '/v1/picks',
      data: {
        'mood': mood,
        'available_minutes': availableMinutes,
        'mental_energy': mentalEnergy,
        'count': count,
        if (context != null) 'context': context,
      },
      options: _llmOptions,
    );
    return response.data!
        .map((e) => Pick.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Accepts a pick suggestion and auto-starts a
  /// playSession for it.
  ///
  /// When [recapText] is provided it is forwarded to the backend so the
  /// auto-started playSession carries that recap.
  Future<Pick> acceptPick(String publicId, {String? recapText}) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/picks/$publicId/accept',
      data: {if (recapText != null) 'recap_text': recapText},
    );
    return Pick.fromJson(response.data!);
  }

  /// Rejects a pick suggestion.
  Future<Pick> rejectPick(String publicId) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/picks/$publicId/reject',
    );
    return Pick.fromJson(response.data!);
  }

  /// Lists the user's pick history.
  Future<PickListResponse> listPicks({int limit = 20, int offset = 0}) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/picks',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return PickListResponse.fromJson(response.data!);
  }

  /// Fetches the latest pending pick, or `null`
  /// if none exists.
  Future<Pick?> getLatestPick() async {
    try {
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/v1/picks/latest',
      );
      if (response.data == null) return null;
      return Pick.fromJson(response.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }
}
