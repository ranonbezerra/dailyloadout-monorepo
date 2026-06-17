import 'package:app/app/routes.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

class App extends StatefulWidget {
  const App({
    required this.authBloc,
    required this.libraryBloc,
    required this.libraryRepository,
    super.key,
  });

  final AuthBloc authBloc;
  final LibraryBloc libraryBloc;
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
      ],
      child: MaterialApp.router(
        title: 'DailyLoadout',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        ),
        routerConfig: _router,
      ),
    );
  }
}
