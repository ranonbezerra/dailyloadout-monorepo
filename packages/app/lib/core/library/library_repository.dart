import 'package:app/core/api/api_client.dart';
import 'package:app/core/library/library_models.dart';

/// Provides high-level library operations backed by the API.
class LibraryRepository {
  LibraryRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  /// Fetches all available platforms.
  Future<List<Platform>> listPlatforms() async {
    final response = await _apiClient.dio.get<List<dynamic>>('/v1/platforms');
    return response.data!
        .map((e) => Platform.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fuzzy-searches games by title.
  Future<List<Game>> searchGames(String query, {int limit = 20}) async {
    final response = await _apiClient.dio.get<List<dynamic>>(
      '/v1/games/search',
      queryParameters: {'q': query, 'limit': limit},
    );
    return response.data!
        .map((e) => Game.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Creates a game manually.
  Future<Game> createGame({
    required String slug,
    required String title,
    String? summary,
    String? coverUrl,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/games',
      data: {
        'slug': slug,
        'title': title,
        if (summary != null) 'summary': summary,
        if (coverUrl != null) 'cover_url': coverUrl,
      },
    );
    return Game.fromJson(response.data!);
  }

  /// Lists the current user's library entries.
  Future<LibraryListResponse> listLibrary({
    String? status,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _apiClient.dio.get<Map<String, dynamic>>(
      '/v1/library',
      queryParameters: {
        if (status != null) 'status': status,
        'limit': limit,
        'offset': offset,
      },
    );
    return LibraryListResponse.fromJson(response.data!);
  }

  /// Adds a game to the current user's library on one or more platforms.
  ///
  /// Returns the resulting grouped game with all its per-platform states.
  /// Re-adding an already-owned platform is idempotent server-side.
  Future<LibraryGameGroup> addToLibrary({
    required String gamePublicId,
    required List<int> platformIds,
    String status = 'backlog',
    String? notes,
  }) async {
    final response = await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/library',
      data: {
        'game_public_id': gamePublicId,
        'platform_ids': platformIds,
        'status': status,
        if (notes != null) 'notes': notes,
      },
    );
    return LibraryGameGroup.fromJson(response.data!);
  }

  /// Updates a single library entry (one platform) by its entry public_id.
  Future<LibraryPlatformState> updateEntry(
    String publicId, {
    String? status,
    String? notes,
  }) async {
    final response = await _apiClient.dio.patch<Map<String, dynamic>>(
      '/v1/library/$publicId',
      data: {
        if (status != null) 'status': status,
        if (notes != null) 'notes': notes,
      },
    );
    return LibraryPlatformState.fromJson(response.data!);
  }

  /// Deletes a library entry.
  Future<void> deleteEntry(String publicId) async {
    await _apiClient.dio.delete<void>('/v1/library/$publicId');
  }
}
