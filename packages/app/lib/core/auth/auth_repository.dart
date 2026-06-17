import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_models.dart';
import 'package:app/core/auth/auth_token_store.dart';

/// Provides high-level authentication operations backed by the API.
class AuthRepository {
  AuthRepository({
    required ApiClient apiClient,
    required AuthTokenStore tokenStore,
  })  : _apiClient = apiClient,
        _tokenStore = tokenStore;

  final ApiClient _apiClient;
  final AuthTokenStore _tokenStore;

  /// Registers a new user account.
  Future<AuthTokens> register({
    required String email,
    required String password,
    required String displayName,
  }) async {
    final response =
        await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/auth/register',
      data: {
        'email': email,
        'password': password,
        'display_name': displayName,
      },
    );
    return AuthTokens.fromJson(response.data!);
  }

  /// Authenticates with email and password.
  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    final response =
        await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/auth/login',
      data: {
        'email': email,
        'password': password,
      },
    );
    return AuthTokens.fromJson(response.data!);
  }

  /// Exchanges a refresh token for a new token pair.
  Future<AuthTokens> refreshToken({
    required String refreshToken,
  }) async {
    final response =
        await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
    return AuthTokens.fromJson(response.data!);
  }

  /// Invalidates the current refresh token.
  Future<void> logout({required String refreshToken}) async {
    await _apiClient.dio.post<Map<String, dynamic>>(
      '/v1/auth/logout',
      data: {'refresh_token': refreshToken},
    );
  }

  /// Fetches the current user's profile.
  Future<User> getMe() async {
    final response =
        await _apiClient.dio.get<Map<String, dynamic>>('/v1/auth/me');
    return User.fromJson(response.data!);
  }

  /// Saves tokens to the token store.
  Future<void> saveTokens(AuthTokens tokens) async {
    await _tokenStore.saveTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );
  }

  /// Clears all stored tokens.
  Future<void> clearTokens() async {
    await _tokenStore.clearTokens();
  }

  /// Returns the stored refresh token, if any.
  Future<String?> getStoredRefreshToken() async {
    return _tokenStore.getRefreshToken();
  }

  /// Checks whether tokens are stored.
  Future<bool> hasTokens() async {
    return _tokenStore.hasTokens();
  }
}
