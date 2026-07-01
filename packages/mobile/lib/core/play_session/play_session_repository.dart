import 'package:app/core/api/api_client.dart';
import 'package:app/core/play_session/play_session_models.dart';
import 'package:dio/dio.dart';

final _llmOptions = Options(receiveTimeout: llmReceiveTimeout);
final _deepLlmOptions = Options(receiveTimeout: deepRecapReceiveTimeout);

/// Provides high-level playSession operations backed by the API.
class PlaySessionRepository {
  PlaySessionRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Previews a recap for a library entry before starting a playSession.
  ///
  /// [mode] is `'quick'` (single-shot), `'deep'` (web-researched), or `'auto'`
  /// (server routes quick/deep from the player's history). Anything but
  /// `'quick'` may run the slow deep path, so it uses the longer receive
  /// timeout and accepts a [cancelToken] so the user can abort.
  Future<RecapPreview> previewRecap(
    String libraryEntryPublicId, {
    String? positionOverride,
    String mode = 'quick',
    CancelToken? cancelToken,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/preview-recap',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'mode': mode,
        if (positionOverride != null) 'position_override': positionOverride,
      },
      options: mode == 'quick' ? _llmOptions : _deepLlmOptions,
      cancelToken: cancelToken,
    );
    return RecapPreview.fromJson(response.data!);
  }

  /// Submits a retroactive wrapUp for a library entry.
  Future<RecapPreview> submitRetroactiveWrapUp(
    String libraryEntryPublicId,
    String wrapUpText,
  ) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/retroactive-wrap-up',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        'wrap_up_text': wrapUpText,
      },
    );
    return RecapPreview.fromJson(response.data!);
  }

  /// Starts a new playSession for a library entry.
  ///
  /// Pass [skipRecap] to start with no recap at all (the "just play"
  /// path) — otherwise, with no [recapText], the backend generates one.
  Future<PlaySession> startPlaySession(
    String libraryEntryPublicId, {
    String? recapText,
    bool skipRecap = false,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions',
      data: {
        'library_entry_public_id': libraryEntryPublicId,
        if (recapText != null) 'recap_text': recapText,
        if (skipRecap) 'skip_recap': true,
      },
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Fetches the currently active playSession, or `null` if none exists.
  Future<PlaySession?> getActivePlaySession() async {
    try {
      final response = await _apiClient.dio.get<Map<String, dynamic>>(
        '/v1/play-sessions/active',
      );
      return PlaySession.fromJson(response.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }

  /// Fetches a single playSession by its public ID.
  Future<PlaySession> getPlaySession(String publicId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId',
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Lists the current user's play sessions.
  Future<PlaySessionListResponse> listPlaySessions({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/play-sessions',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return PlaySessionListResponse.fromJson(response.data!);
  }

  /// Submits a wrapUp for a playSession.
  Future<PlaySession> submitWrapUp(String publicId, String wrapUpText) async {
    final response = await _apiClient.dio.patch<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/wrap-up',
      data: {'wrap_up_text': wrapUpText},
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Ends a playSession with the given reason.
  Future<PlaySession> endPlaySession(
    String publicId, {
    String endedVia = 'paused_app',
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/end',
      data: {'ended_via': endedVia},
    );
    return PlaySession.fromJson(response.data!);
  }

  /// Regenerates the recap for an existing playSession.
  Future<PlaySession> regenerateRecap(
    String publicId, {
    String? currentPosition,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/play-sessions/$publicId/recap/regenerate',
      data: {if (currentPosition != null) 'current_position': currentPosition},
      options: _llmOptions,
    );
    return PlaySession.fromJson(response.data!);
  }
}
