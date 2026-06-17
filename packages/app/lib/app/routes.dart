import 'dart:async';

import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/login_page.dart';
import 'package:app/features/auth/view/register_page.dart';
import 'package:app/features/auth/view/splash_page.dart';
import 'package:app/features/home/view/home_page.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

GoRouter createRouter(AuthBloc authBloc) {
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: _AuthBlocListenable(authBloc),
    redirect: (BuildContext context, GoRouterState state) {
      final authState = authBloc.state;
      final currentPath = state.matchedLocation;

      // While we are still determining auth status, stay on splash.
      if (authState is AuthInitial || authState is AuthLoading) {
        if (currentPath != '/splash') return '/splash';
        return null;
      }

      final isAuthenticated = authState is Authenticated;
      final isOnAuthPage =
          currentPath == '/login' || currentPath == '/register';
      final isOnSplash = currentPath == '/splash';

      if (!isAuthenticated) {
        // Redirect unauthenticated users to login.
        if (!isOnAuthPage) return '/login';
        return null;
      }

      // Redirect authenticated users away from auth/splash pages.
      if (isOnAuthPage || isOnSplash) return '/';
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),
      GoRoute(
        path: '/',
        builder: (context, state) => const HomePage(),
      ),
    ],
  );
}

/// Adapts [AuthBloc] stream into a [ChangeNotifier] so GoRouter can
/// listen for auth state changes and trigger redirects.
class _AuthBlocListenable extends ChangeNotifier {
  _AuthBlocListenable(AuthBloc authBloc) {
    _subscription = authBloc.stream.listen((_) {
      notifyListeners();
    });
  }

  late final StreamSubscription<AuthState> _subscription;

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}
