part of 'auth_bloc.dart';

sealed class AuthEvent extends Equatable {
  const AuthEvent();

  @override
  List<Object?> get props => [];
}

/// Dispatched when the app first starts to check existing auth state.
final class AppStarted extends AuthEvent {
  const AppStarted();
}

/// Dispatched when the user submits the login form.
final class LoginRequested extends AuthEvent {
  const LoginRequested({required this.email, required this.password});

  final String email;
  final String password;

  @override
  List<Object?> get props => [email, password];
}

/// Dispatched when the user submits the registration form.
final class RegisterRequested extends AuthEvent {
  const RegisterRequested({
    required this.email,
    required this.password,
    required this.displayName,
  });

  final String email;
  final String password;
  final String displayName;

  @override
  List<Object?> get props => [email, password, displayName];
}

/// Dispatched when the user requests to log out.
final class LogoutRequested extends AuthEvent {
  const LogoutRequested();
}

/// Dispatched to re-fetch the current user's profile from `/me`.
///
/// Used after the user has clicked the email verification link in the web
/// app: re-fetching updates [User.emailVerified] so the verify prompt clears.
/// Unlike [AppStarted], this does not emit [AuthLoading], so the UI stays put
/// while the profile refreshes in the background.
final class RefreshUserRequested extends AuthEvent {
  const RefreshUserRequested();
}

/// Dispatched to request a fresh verification email be sent.
final class ResendVerificationRequested extends AuthEvent {
  const ResendVerificationRequested();
}
