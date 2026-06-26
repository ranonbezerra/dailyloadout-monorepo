import 'dart:async';

import 'package:app/app/shell_page.dart';
import 'package:app/core/config/feature_flags.dart';
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
import 'package:app/features/concierge/view/concierge_page.dart';
import 'package:app/features/library/view/add_game_page.dart';
import 'package:app/features/library/view/library_detail_page.dart';
import 'package:app/features/library/view/library_list_page.dart';
import 'package:app/features/library_import/view/library_import_page.dart';
import 'package:app/features/loadout/view/loadout_page.dart';
import 'package:app/features/mission/view/mission_briefing_page.dart';
import 'package:app/features/mission/view/mission_debrief_page.dart';
import 'package:app/features/mission/view/missions_list_page.dart';
import 'package:app/features/play/view/play_page.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

GoRouter createRouter(
  AuthBloc authBloc, {
  required LibraryRepository libraryRepository,
  FeatureFlags featureFlags = const FeatureFlags(),
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

      final isAuthenticated = authState is AuthenticatedState;
      final isOnAuthPage =
          currentPath == '/login' || currentPath == '/register';
      final isOnSplash = currentPath == '/splash';

      if (!isAuthenticated) {
        // Redirect unauthenticated users to login.
        if (!isOnAuthPage) return '/login';
        return null;
      }

      // Redirect authenticated users away from auth/splash pages.
      if (isOnAuthPage || isOnSplash) return '/play';
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
      GoRoute(path: '/', redirect: (context, state) => '/play'),

      // ---- Legacy path redirects (keep old deep links working) ----
      GoRoute(path: '/loadout', redirect: (context, state) => '/play/loadout'),
      GoRoute(path: '/missions', redirect: (context, state) => '/history'),
      GoRoute(
        path: '/concierge',
        redirect: (context, state) => '/play/concierge',
      ),

      // ---- Shell: bottom-nav tabs (Play, Library, History, Stats) ----
      ShellRoute(
        builder: (context, state, child) => ShellPage(child: child),
        routes: [
          // Play hub and its nested surfaces.
          GoRoute(
            path: '/play',
            builder: (context, state) =>
                PlayPage(conciergeEnabled: featureFlags.backlogConcierge),
            routes: [
              GoRoute(
                path: 'loadout',
                builder: (context, state) => const LoadoutPage(),
              ),
              // Legacy nested path — the mission log now lives at /history.
              GoRoute(
                path: 'missions',
                redirect: (context, state) => '/history',
              ),
              // Backlog Concierge — hidden unless the feature flag is enabled.
              if (featureFlags.backlogConcierge)
                GoRoute(
                  path: 'concierge',
                  builder: (context, state) => const ConciergePage(),
                ),
            ],
          ),
          GoRoute(
            path: '/library',
            builder: (context, state) => const LibraryListPage(),
          ),
          GoRoute(
            path: '/history',
            builder: (context, state) => const MissionsListPage(),
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
        path: '/library/import',
        builder: (context, state) =>
            LibraryImportPage(libraryRepository: libraryRepository),
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
