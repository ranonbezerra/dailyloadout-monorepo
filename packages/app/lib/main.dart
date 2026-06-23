import 'package:app/app/app.dart';
import 'package:app/core/analytics/analytics_repository.dart';
import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
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
  final missionRepository = MissionRepository(apiClient: apiClient);
  final loadoutRepository = LoadoutRepository(apiClient: apiClient);
  final analyticsRepository = AnalyticsRepository(apiClient: apiClient);

  final authBloc = AuthBloc(authRepository: authRepository);
  final libraryBloc = LibraryBloc(libraryRepository: libraryRepository);
  final captureBloc = CaptureBloc(captureRepository: captureRepository);
  final missionBloc = MissionBloc(missionRepository: missionRepository);
  final loadoutBloc = LoadoutBloc(loadoutRepository: loadoutRepository);
  final analyticsBloc = AnalyticsBloc(analyticsRepository: analyticsRepository);

  runApp(
    App(
      authBloc: authBloc,
      libraryBloc: libraryBloc,
      captureBloc: captureBloc,
      missionBloc: missionBloc,
      loadoutBloc: loadoutBloc,
      analyticsBloc: analyticsBloc,
      libraryRepository: libraryRepository,
    ),
  );
}
