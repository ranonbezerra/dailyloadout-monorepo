import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Shell scaffold that wraps the main authenticated pages with a
/// [BottomNavigationBar] for tab-based navigation between Library and Missions.
class ShellPage extends StatelessWidget {
  const ShellPage({required this.child, super.key});

  /// The current page rendered by [GoRouter] inside the shell.
  final Widget child;

  /// Returns the tab index that matches the current route location.
  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/loadout')) return 1;
    if (location.startsWith('/missions')) return 2;
    if (location.startsWith('/analytics')) return 3;
    return 0; // /library is the default
  }

  void _onTap(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/library');
      case 1:
        context.go('/loadout');
      case 2:
        context.go('/missions');
      case 3:
        context.go('/analytics');
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _currentIndex(context);

    return Scaffold(
      body: child,
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: currentIndex,
        onTap: (index) => _onTap(context, index),
        type: BottomNavigationBarType.fixed,
        backgroundColor: DLColors.bg,
        selectedItemColor: DLColors.coral,
        unselectedItemColor: DLColors.textDim,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.videogame_asset),
            label: 'Library',
          ),
          BottomNavigationBarItem(icon: Icon(Icons.casino), label: 'Loadout'),
          BottomNavigationBarItem(icon: Icon(Icons.flag), label: 'Missions'),
          BottomNavigationBarItem(icon: Icon(Icons.bar_chart), label: 'Stats'),
        ],
      ),
    );
  }
}
