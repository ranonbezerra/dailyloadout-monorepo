import 'dart:async';

import 'package:app/app/shell_page.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/analytics/view/analytics_page.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/auth/view/login_page.dart';
import 'package:app/features/auth/view/register_page.dart';
import 'package:app/features/auth/view/splash_page.dart';
import 'package:app/features/capture/view/capture_choice_page.dart';
import 'package:app/features/capture/view/capture_photo_page.dart';
import 'package:app/features/capture/view/capture_review_page.dart';
import 'package:app/features/capture/view/capture_text_page.dart';
import 'package:app/features/capture/view/capture_voice_page.dart';
import 'package:app/features/library/view/add_game_page.dart';
import 'package:app/features/library/view/library_detail_page.dart';
import 'package:app/features/library/view/library_list_page.dart';
import 'package:app/features/loadout/view/loadout_page.dart';
import 'package:app/features/mission/view/mission_briefing_page.dart';
import 'package:app/features/mission/view/mission_debrief_page.dart';
import 'package:app/features/mission/view/missions_list_page.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

GoRouter createRouter(
  AuthBloc authBloc, {
  required LibraryRepository libraryRepository,
}) {
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
      if (isOnAuthPage || isOnSplash) return '/library';
      return null;
    },
    routes: [
      // ---- Auth / splash (no bottom nav) ----
      GoRoute(path: '/splash', builder: (context, state) => const SplashPage()),
      GoRoute(path: '/login', builder: (context, state) => const LoginPage()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),
      GoRoute(path: '/', redirect: (context, state) => '/library'),

      // ---- Shell: bottom-nav tabs (Library + Missions) ----
      ShellRoute(
        builder: (context, state, child) => ShellPage(child: child),
        routes: [
          GoRoute(
            path: '/library',
            builder: (context, state) => const LibraryListPage(),
          ),
          GoRoute(
            path: '/missions',
            builder: (context, state) => const MissionsListPage(),
          ),
          GoRoute(
            path: '/loadout',
            builder: (context, state) => const LoadoutPage(),
          ),
          GoRoute(
            path: '/analytics',
            builder: (context, state) => const AnalyticsPage(),
          ),
        ],
      ),

      // ---- Full-screen routes (no bottom nav) ----
      GoRoute(
        path: '/library/add',
        builder: (context, state) =>
            AddGamePage(libraryRepository: libraryRepository),
      ),
      GoRoute(
        path: '/library/:id',
        builder: (context, state) =>
            LibraryDetailPage(entryPublicId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/capture',
        builder: (context, state) => const CaptureChoicePage(),
      ),
      GoRoute(
        path: '/capture/text',
        builder: (context, state) => const CaptureTextPage(),
      ),
      GoRoute(
        path: '/capture/voice',
        builder: (context, state) => const CaptureVoicePage(),
      ),
      GoRoute(
        path: '/capture/photo',
        builder: (context, state) => const CapturePhotoPage(),
      ),
      GoRoute(
        path: '/capture/review/:id',
        builder: (context, state) => CaptureReviewPage(
          capturePublicId: state.pathParameters['id']!,
          libraryRepository: libraryRepository,
        ),
      ),
      GoRoute(
        path: '/missions/briefing',
        builder: (context, state) {
          final entryId = state.uri.queryParameters['entry'];
          return MissionBriefingPage(libraryEntryPublicId: entryId);
        },
      ),
      GoRoute(
        path: '/missions/:id/briefing',
        builder: (context, state) =>
            MissionBriefingPage(missionPublicId: state.pathParameters['id']),
      ),
      GoRoute(
        path: '/missions/:id/debrief',
        builder: (context, state) =>
            MissionDebriefPage(missionPublicId: state.pathParameters['id']!),
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
