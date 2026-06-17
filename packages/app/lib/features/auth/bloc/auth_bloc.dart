import 'package:app/core/auth/auth_models.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:bloc/bloc.dart';
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';
import 'package:logger/logger.dart';

part 'auth_event.dart';
part 'auth_state.dart';

class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc({required AuthRepository authRepository})
      : _authRepository = authRepository,
        super(const AuthInitial()) {
    on<AppStarted>(_onAppStarted);
    on<LoginRequested>(_onLoginRequested);
    on<RegisterRequested>(_onRegisterRequested);
    on<LogoutRequested>(_onLogoutRequested);
  }

  final AuthRepository _authRepository;
  final Logger _logger = Logger(printer: PrettyPrinter(methodCount: 0));

  Future<void> _onAppStarted(
    AppStarted event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      final hasTokens = await _authRepository.hasTokens();
      if (!hasTokens) {
        emit(const Unauthenticated());
        return;
      }

      final refreshToken = await _authRepository.getStoredRefreshToken();
      if (refreshToken == null) {
        emit(const Unauthenticated());
        return;
      }

      // Attempt to refresh the token pair.
      final tokens = await _authRepository.refreshToken(
        refreshToken: refreshToken,
      );
      await _authRepository.saveTokens(tokens);

      // Fetch the user profile.
      final user = await _authRepository.getMe();
      emit(Authenticated(user: user));
    } on Exception catch (e) {
      _logger.w('Auto-login failed: $e');
      await _authRepository.clearTokens();
      emit(const Unauthenticated());
    }
  }

  Future<void> _onLoginRequested(
    LoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      final tokens = await _authRepository.login(
        email: event.email,
        password: event.password,
      );
      await _authRepository.saveTokens(tokens);

      final user = await _authRepository.getMe();
      emit(Authenticated(user: user));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(AuthError(message: message));
    } on Exception catch (e) {
      emit(AuthError(message: e.toString()));
    }
  }

  Future<void> _onRegisterRequested(
    RegisterRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(const AuthLoading());

    try {
      final tokens = await _authRepository.register(
        email: event.email,
        password: event.password,
        displayName: event.displayName,
      );
      await _authRepository.saveTokens(tokens);

      final user = await _authRepository.getMe();
      emit(Authenticated(user: user));
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      emit(AuthError(message: message));
    } on Exception catch (e) {
      emit(AuthError(message: e.toString()));
    }
  }

  Future<void> _onLogoutRequested(
    LogoutRequested event,
    Emitter<AuthState> emit,
  ) async {
    try {
      final refreshToken = await _authRepository.getStoredRefreshToken();
      if (refreshToken != null) {
        await _authRepository.logout(refreshToken: refreshToken);
      }
    } on Exception catch (e) {
      _logger.w('Logout API call failed: $e');
    } finally {
      await _authRepository.clearTokens();
      emit(const Unauthenticated());
    }
  }

  String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }
    return e.message ?? 'An unexpected error occurred.';
  }
}
