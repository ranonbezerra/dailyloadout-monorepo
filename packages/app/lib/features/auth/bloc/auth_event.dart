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
  const LoginRequested({
    required this.email,
    required this.password,
  });

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
