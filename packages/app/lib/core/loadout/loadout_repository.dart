import 'package:app/core/api/api_client.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:dio/dio.dart';

final _llmOptions = Options(receiveTimeout: llmReceiveTimeout);

/// Provides high-level loadout operations backed by the API.
class LoadoutRepository {
  LoadoutRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Creates loadout suggestions based on the
  /// user's mood, time, and energy level.
  Future<List<Loadout>> createLoadout({
    required String mood,
    required int availableMinutes,
    required String mentalEnergy,
    int count = 1,
    String? context,
  }) async {
    final response = await _apiClient.dio.post<List<dynamic>>(
      '/v1/loadouts',
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
        .map((e) => Loadout.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Accepts a loadout suggestion and auto-starts a
  /// mission for it.
  ///
  /// When [briefingText] is provided it is forwarded to the backend so the
  /// auto-started mission carries that briefing.
  Future<Loadout> acceptLoadout(String publicId, {String? briefingText}) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/loadouts/$publicId/accept',
      data: {if (briefingText != null) 'briefing_text': briefingText},
    );
    return Loadout.fromJson(response.data!);
  }

  /// Rejects a loadout suggestion.
  Future<Loadout> rejectLoadout(String publicId) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/loadouts/$publicId/reject',
    );
    return Loadout.fromJson(response.data!);
  }

  /// Lists the user's loadout history.
  Future<LoadoutListResponse> listLoadouts({
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/loadouts',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return LoadoutListResponse.fromJson(response.data!);
  }

  /// Fetches the latest pending loadout, or `null`
  /// if none exists.
  Future<Loadout?> getLatestLoadout() async {
    try {
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/v1/loadouts/latest',
      );
      if (response.data == null) return null;
      return Loadout.fromJson(response.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }
}
