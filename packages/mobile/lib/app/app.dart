import 'package:app/app/routes.dart';
import 'package:app/core/config/feature_flags.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

class App extends StatefulWidget {
  const App({
    required this.authBloc,
    required this.libraryBloc,
    required this.captureBloc,
    required this.libraryImportBloc,
    required this.playSessionBloc,
    required this.pickBloc,
    required this.analyticsBloc,
    required this.conciergeBloc,
    required this.libraryRepository,
    required this.featureFlags,
    super.key,
  });

  final AuthBloc authBloc;
  final LibraryBloc libraryBloc;
  final CaptureBloc captureBloc;
  final LibraryImportBloc libraryImportBloc;
  final PlaySessionBloc playSessionBloc;
  final PickBloc pickBloc;
  final AnalyticsBloc analyticsBloc;
  final ConciergeBloc conciergeBloc;
  final LibraryRepository libraryRepository;
  final FeatureFlags featureFlags;

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = createRouter(
      widget.authBloc,
      libraryRepository: widget.libraryRepository,
      featureFlags: widget.featureFlags,
    );
    widget.authBloc.add(const AppStarted());
  }

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider<AuthBloc>.value(value: widget.authBloc),
        BlocProvider<LibraryBloc>.value(value: widget.libraryBloc),
        BlocProvider<CaptureBloc>.value(value: widget.captureBloc),
        BlocProvider<LibraryImportBloc>.value(value: widget.libraryImportBloc),
        BlocProvider<PlaySessionBloc>.value(value: widget.playSessionBloc),
        BlocProvider<PickBloc>.value(value: widget.pickBloc),
        BlocProvider<AnalyticsBloc>.value(value: widget.analyticsBloc),
        BlocProvider<ConciergeBloc>.value(value: widget.conciergeBloc),
      ],
      child: MaterialApp.router(
        title: 'Slate',
        theme: SlateTheme.dark,
        darkTheme: SlateTheme.dark,
        themeMode: ThemeMode.dark,
        routerConfig: _router,
      ),
    );
  }
}
