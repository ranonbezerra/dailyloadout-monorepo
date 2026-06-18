import 'package:app/core/api/api_client.dart';
import 'package:app/core/capture/capture_models.dart';

/// Provides high-level capture operations backed by the API.
class CaptureRepository {
  CaptureRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Submits free text for game extraction.
  Future<Capture> submitText(String rawText) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/captures/text',
      data: {'raw_text': rawText},
    );
    return Capture.fromJson(response.data!);
  }

  /// Lists the current user's captures.
  Future<CaptureListResponse> listCaptures({
    String? status,
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/captures',
      queryParameters: {
        if (status != null) 'status': status,
        'limit': limit,
        'offset': offset,
      },
    );
    return CaptureListResponse.fromJson(response.data!);
  }

  /// Gets a single capture with its candidates.
  Future<Capture> getCapture(String publicId) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/captures/$publicId',
    );
    return Capture.fromJson(response.data!);
  }

  /// Confirms a candidate and adds it to the user's library.
  ///
  /// Returns the created library entry data.
  Future<Map<String, dynamic>> confirmCandidate(
    String captureId,
    String candidateId,
    int platformId, {
    String status = 'backlog',
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/captures/$captureId/candidates/$candidateId/confirm',
      data: {
        'platform_id': platformId,
        'status': status,
      },
    );
    return response.data!;
  }

  /// Rejects a candidate.
  Future<void> rejectCandidate(
    String captureId,
    String candidateId,
  ) async {
    await _apiClient.dio.post<void>(
      '/v1/captures/$captureId/candidates/$candidateId/reject',
    );
  }
}
