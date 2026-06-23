import 'package:app/app/routes.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/analytics/bloc/analytics_bloc.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

class App extends StatefulWidget {
  const App({
    required this.authBloc,
    required this.libraryBloc,
    required this.captureBloc,
    required this.missionBloc,
    required this.loadoutBloc,
    required this.analyticsBloc,
    required this.libraryRepository,
    super.key,
  });

  final AuthBloc authBloc;
  final LibraryBloc libraryBloc;
  final CaptureBloc captureBloc;
  final MissionBloc missionBloc;
  final LoadoutBloc loadoutBloc;
  final AnalyticsBloc analyticsBloc;
  final LibraryRepository libraryRepository;

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
        BlocProvider<MissionBloc>.value(value: widget.missionBloc),
        BlocProvider<LoadoutBloc>.value(value: widget.loadoutBloc),
        BlocProvider<AnalyticsBloc>.value(value: widget.analyticsBloc),
      ],
      child: MaterialApp.router(
        title: 'DailyLoadout',
        theme: DailyLoadoutTheme.dark,
        darkTheme: DailyLoadoutTheme.dark,
        themeMode: ThemeMode.dark,
        routerConfig: _router,
      ),
    );
  }
}
