import 'package:app/core/api/api_client.dart';
import 'package:app/core/mission/mission_models.dart';
import 'package:dio/dio.dart';

final _llmOptions = Options(receiveTimeout: llmReceiveTimeout);
final _deepLlmOptions = Options(receiveTimeout: deepBriefingReceiveTimeout);

/// Provides high-level mission operations backed by the API.
class MissionRepository {
  MissionRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Previews a briefing for a library entry before starting a mission.
  ///
  /// [mode] selects the quick single-shot briefing or the deep web-researched
  /// one. Deep mode uses a longer receive timeout and accepts a [cancelToken]
  /// so the user can abort the (slow) request.
  Future<BriefingPreview> previewBriefing(
    String libraryEntryPublicId, {
    String? positionOverride,
    String mode = 'quick',
    CancelToken? cancelToken,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/missions/preview-briefing',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'mode': mode,
        if (positionOverride != null) 'position_override': positionOverride,
      },
      options: mode == 'deep' ? _deepLlmOptions : _llmOptions,
      cancelToken: cancelToken,
    );
    return BriefingPreview.fromJson(response.data!);
  }

  /// Submits a retroactive debrief for a library entry.
  Future<BriefingPreview> submitRetroactiveDebrief(
    String libraryEntryPublicId,
    String debriefText,
  ) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/missions/retroactive-debrief',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'debrief_text': debriefText,
      },
    );
    return BriefingPreview.fromJson(response.data!);
  }

  /// Starts a new mission for a library entry.
  ///
  /// Pass [skipBriefing] to start with no briefing at all (the "just play"
  /// path) — otherwise, with no [briefingText], the backend generates one.
  Future<Mission> startMission(
    String libraryEntryPublicId, {
    String? briefingText,
    bool skipBriefing = false,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/missions',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        if (briefingText != null) 'briefing_text': briefingText,
        if (skipBriefing) 'skip_briefing': true,
      },
    );
    return Mission.fromJson(response.data!);
  }

  /// Fetches the currently active mission, or `null` if none exists.
  Future<Mission?> getActiveMission() async {
    try {
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/v1/missions/active',
      );
      return Mission.fromJson(response.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  /// Fetches a single mission by its public ID.
  Future<Mission> getMission(String publicId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/missions/$publicId',
    );
    return Mission.fromJson(response.data!);
  }

  /// Lists the current user's missions.
  Future<MissionListResponse> listMissions({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/missions',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return MissionListResponse.fromJson(response.data!);
  }

  /// Submits a debrief for a mission.
  Future<Mission> submitDebrief(String publicId, String debriefText) async {
    final response = await _apiClient.dio.patch<Map<String, dynamic>>(
      '/v1/missions/$publicId/debrief',
      data: {'debrief_text': debriefText},
    );
    return Mission.fromJson(response.data!);
  }

  /// Ends a mission with the given reason.
  Future<Mission> endMission(
    String publicId, {
    String endedVia = 'paused_app',
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/missions/$publicId/end',
      data: {'ended_via': endedVia},
    );
    return Mission.fromJson(response.data!);
  }

  /// Regenerates the briefing for an existing mission.
  Future<Mission> regenerateBriefing(
    String publicId, {
    String? currentPosition,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/missions/$publicId/briefing/regenerate',
      data: {if (currentPosition != null) 'current_position': currentPosition},
      options: _llmOptions,
    );
    return Mission.fromJson(response.data!);
  }
}
