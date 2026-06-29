import 'package:app/app/app.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:app/core/config/feature_flags.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/pick/pick_repository.dart';
import 'package:app/core/play_session/play_session_repository.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final assetManifest = await AssetManifest.loadFromAssetBundle(rootBundle);
  final envFile = assetManifest.listAssets().contains('.env')
      ? '.env'
      : '.env.example';
  await dotenv.load(fileName: envFile);
  const apiUrlOverride = String.fromEnvironment('API_URL');
  final featureFlags = FeatureFlags.fromEnv();

  // Core dependencies
  final tokenStore = AuthTokenStore();

  final apiClient = ApiClient(
    tokenStore: tokenStore,
    baseUrl: apiUrlOverride.isNotEmpty
        ? apiUrlOverride
        : dotenv.get('API_URL', fallback: 'http://localhost:8100'),
  );

  final authRepository = AuthRepository(
    apiClient: apiClient,
    tokenStore: tokenStore,
  );

  final libraryRepository = LibraryRepository(apiClient: apiClient);
  final captureRepository = CaptureRepository(apiClient: apiClient);
  final playSessionRepository = PlaySessionRepository(apiClient: apiClient);
  final pickRepository = PickRepository(apiClient: apiClient);
  final analyticsRepository = AnalyticsRepository(apiClient: apiClient);
  final conciergeRepository = ConciergeRepository(apiClient: apiClient);

  final authBloc = AuthBloc(authRepository: authRepository);

  // Wire token-refresh failure to a forced logout. The auth interceptor
  // clears tokens and invokes this when a refresh token is expired/revoked,
  // so the router's refreshListenable can redirect to /login.
  apiClient.onForceLogout = () => authBloc.add(const LogoutRequested());
  final libraryBloc = LibraryBloc(libraryRepository: libraryRepository);
  final captureBloc = CaptureBloc(captureRepository: captureRepository);
  final libraryImportBloc = LibraryImportBloc(
    captureRepository: captureRepository,
  );
  final playSessionBloc = PlaySessionBloc(
    playSessionRepository: playSessionRepository,
  );
  final pickBloc = PickBloc(
    pickRepository: pickRepository,
    playSessionRepository: playSessionRepository,
  );
  final analyticsBloc = AnalyticsBloc(analyticsRepository: analyticsRepository);
  final conciergeBloc = ConciergeBloc(conciergeRepository: conciergeRepository);

  runApp(
    App(
      authBloc: authBloc,
      libraryBloc: libraryBloc,
      captureBloc: captureBloc,
      libraryImportBloc: libraryImportBloc,
      playSessionBloc: playSessionBloc,
      pickBloc: pickBloc,
      analyticsBloc: analyticsBloc,
      conciergeBloc: conciergeBloc,
      libraryRepository: libraryRepository,
      featureFlags: featureFlags,
    ),
  );
}
