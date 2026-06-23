import 'package:app/app/app.dart';
import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/core/capture/capture_repository.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/loadout/loadout_repository.dart';
import 'package:app/core/mission/mission_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load();

  // Core dependencies
  final tokenStore = AuthTokenStore();

  final apiClient = ApiClient(
    tokenStore: tokenStore,
    baseUrl: dotenv.get('API_URL', fallback: 'http://localhost:8100'),
  );

  final authRepository = AuthRepository(
    apiClient: apiClient,
    tokenStore: tokenStore,
  );

  final libraryRepository = LibraryRepository(apiClient: apiClient);
  final captureRepository = CaptureRepository(apiClient: apiClient);
  final missionRepository = MissionRepository(apiClient: apiClient);
  final loadoutRepository = LoadoutRepository(apiClient: apiClient);

  final authBloc = AuthBloc(authRepository: authRepository);
  final libraryBloc = LibraryBloc(libraryRepository: libraryRepository);
  final captureBloc = CaptureBloc(captureRepository: captureRepository);
  final missionBloc = MissionBloc(missionRepository: missionRepository);
  final loadoutBloc = LoadoutBloc(
    loadoutRepository: loadoutRepository,
  );

  runApp(
    App(
      authBloc: authBloc,
      libraryBloc: libraryBloc,
      captureBloc: captureBloc,
      missionBloc: missionBloc,
      loadoutBloc: loadoutBloc,
      libraryRepository: libraryRepository,
    ),
  );
}
