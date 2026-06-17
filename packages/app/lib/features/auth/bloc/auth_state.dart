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

/// The user is authenticated with a valid session.
final class Authenticated extends AuthState {
  const Authenticated({required this.user});

  final User user;

  @override
  List<Object?> get props => [user];
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
