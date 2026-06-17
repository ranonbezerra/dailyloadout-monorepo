import 'package:app/app/routes.dart';
import 'package:app/features/auth/bloc/auth_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

class App extends StatefulWidget {
  const App({required this.authBloc, super.key});

  final AuthBloc authBloc;

  @override
  State<App> createState() => _AppState();
}

class _AppState extends State<App> {
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = createRouter(widget.authBloc);
    widget.authBloc.add(const AppStarted());
  }

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider<AuthBloc>.value(
      value: widget.authBloc,
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
