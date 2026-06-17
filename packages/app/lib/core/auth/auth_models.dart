import 'package:equatable/equatable.dart';

/// Holds the access and refresh tokens returned by auth endpoints.
class AuthTokens extends Equatable {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
  });

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
    );
  }

  final String accessToken;
  final String refreshToken;

  @override
  List<Object?> get props => [accessToken, refreshToken];
}

/// Represents the authenticated user profile.
class User extends Equatable {
  const User({
    required this.publicId,
    required this.email,
    required this.displayName,
    required this.emailVerified,
    required this.locale,
    required this.timezone,
    required this.createdAt,
    this.avatarUrl,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      publicId: json['public_id'] as String,
      email: json['email'] as String,
      displayName: json['display_name'] as String,
      avatarUrl: json['avatar_url'] as String?,
      emailVerified: json['email_verified'] as bool,
      locale: json['locale'] as String,
      timezone: json['timezone'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  final String publicId;
  final String email;
  final String displayName;
  final String? avatarUrl;
  final bool emailVerified;
  final String locale;
  final String timezone;
  final DateTime createdAt;

  @override
  List<Object?> get props => [
        publicId,
        email,
        displayName,
        avatarUrl,
        emailVerified,
        locale,
        timezone,
        createdAt,
      ];
}
