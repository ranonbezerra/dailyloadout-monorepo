import 'package:dio/dio.dart';

/// Helpers for recognising the "email not verified" guard that cost-bearing
/// API routes return until the user verifies their address.
abstract final class EmailVerification {
  /// The detail string the API sends with the 403 on cost-bearing routes.
  static const String apiDetail = 'Email not verified';

  /// A friendly, actionable message shown in place of the raw API error.
  static const String friendlyMessage =
      'Verify your email to use AI features. '
      'Check your inbox for the verification link.';

  /// Whether [error] is the 403 raised because the account is unverified.
  static bool isUnverifiedError(DioException error) {
    final response = error.response;
    if (response?.statusCode != 403) return false;
    final data = response?.data;
    if (data is Map<String, dynamic>) {
      return data['detail'] == apiDetail;
    }
    return false;
  }
}
