part of 'auth_bloc.dart';

sealed class AuthState extends Equatable {
  const AuthState();

  @override
  List<Object?> get props => [];
}

/// The initial state before any auth check has been performed.
final class AuthInitial extends AuthState {
  const AuthInitial();
}

/// An auth operation is in progress.
final class AuthLoading extends AuthState {
  const AuthLoading();
}

/// Base for every state in which the user holds a valid session.
///
/// The router treats any [AuthenticatedState] as logged-in, so transient
/// feedback states (e.g. [VerificationEmailSent]) don't bounce the user back
/// to the login screen.
sealed class AuthenticatedState extends AuthState {
  const AuthenticatedState({required this.user});

  final User user;
}

/// The user is authenticated with a valid session.
final class Authenticated extends AuthenticatedState {
  const Authenticated({required super.user});

  @override
  List<Object?> get props => [user];
}

/// Transient: a verification email was just requested successfully.
///
/// Carries the unchanged [user] so the session is preserved; the UI shows a
/// confirmation snackbar in response.
final class VerificationEmailSent extends AuthenticatedState {
  const VerificationEmailSent({required super.user, required this.message});

  final String message;

  @override
  List<Object?> get props => [user, message];
}

/// Transient: requesting a verification email failed.
final class VerificationEmailFailed extends AuthenticatedState {
  const VerificationEmailFailed({required super.user, required this.message});

  final String message;

  @override
  List<Object?> get props => [user, message];
}

/// The user is not authenticated.
final class Unauthenticated extends AuthState {
  const Unauthenticated();
}

/// An auth operation failed.
final class AuthError extends AuthState {
  const AuthError({required this.message});

  final String message;

  @override
  List<Object?> get props => [message];
}
