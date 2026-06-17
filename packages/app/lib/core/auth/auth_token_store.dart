import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Manages authentication token storage.
///
/// Access tokens are kept in-memory only for security.
/// Refresh tokens are persisted using flutter_secure_storage.
class AuthTokenStore {
  AuthTokenStore({FlutterSecureStorage? secureStorage})
      : _secureStorage = secureStorage ?? const FlutterSecureStorage();

  static const String _refreshTokenKey = 'refresh_token';

  final FlutterSecureStorage _secureStorage;
  String? _accessToken;

  /// Saves both tokens. Access token is stored in-memory,
  /// refresh token is persisted securely.
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    _accessToken = accessToken;
    await _secureStorage.write(key: _refreshTokenKey, value: refreshToken);
  }

  /// Returns the in-memory access token, or null if not set.
  String? getAccessToken() => _accessToken;

  /// Returns the persisted refresh token, or null if not set.
  Future<String?> getRefreshToken() async {
    return _secureStorage.read(key: _refreshTokenKey);
  }

  /// Returns true if a refresh token is stored.
  Future<bool> hasTokens() async {
    final refreshToken = await getRefreshToken();
    return refreshToken != null && refreshToken.isNotEmpty;
  }

  /// Clears both tokens.
  Future<void> clearTokens() async {
    _accessToken = null;
    await _secureStorage.delete(key: _refreshTokenKey);
  }
}
