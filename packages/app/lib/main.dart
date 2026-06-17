import 'package:app/app/app.dart';
import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_repository.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env.example');

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

  final authBloc = AuthBloc(authRepository: authRepository);

  runApp(App(authBloc: authBloc));
}
