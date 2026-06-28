import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/auth/view/verify_email_banner.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Shell scaffold that wraps the main authenticated pages with a
/// [BottomNavigationBar] for tab-based navigation. The nav has four tabs: Play,
/// Library, History, and Stats. The Loadout and Concierge surfaces live under
/// the Play hub at `/play/*`; History is the mission log at `/history`.
class ShellPage extends StatelessWidget {
  const ShellPage({required this.child, super.key});

  /// The current page rendered by [GoRouter] inside the shell.
  final Widget child;

  /// Ordered tab definitions: Play, Library, History, Stats.
  List<_Tab> _tabs() {
    return [
      const _Tab(path: '/play', icon: Icons.sports_esports, label: 'Play'),
      const _Tab(
        path: '/library',
        icon: Icons.videogame_asset,
        label: 'Library',
      ),
      const _Tab(path: '/history', icon: Icons.history, label: 'History'),
      const _Tab(path: '/analytics', icon: Icons.bar_chart, label: 'Stats'),
    ];
  }

  int _currentIndex(BuildContext context, List<_Tab> tabs) {
    final location = GoRouterState.of(context).matchedLocation;
    // Any `/play*` location maps to the Play tab.
    if (location.startsWith('/play')) {
      return tabs.indexWhere((t) => t.path == '/play');
    }
    final index = tabs.indexWhere((t) => location.startsWith(t.path));
    return index < 0 ? 0 : index;
  }

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs();

    return Scaffold(
      // A persistent "verify your email" banner sits above the active tab
      // whenever the user is unverified; it renders nothing otherwise.
      body: Column(
        children: [
          const VerifyEmailBanner(),
          Expanded(child: child),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex(context, tabs),
        onTap: (index) => context.go(tabs[index].path),
        type: BottomNavigationBarType.fixed,
        backgroundColor: DLColors.bg,
        selectedItemColor: DLColors.coral,
        unselectedItemColor: DLColors.textDim,
        items: [
          for (final tab in tabs)
            BottomNavigationBarItem(icon: Icon(tab.icon), label: tab.label),
        ],
      ),
    );
  }
}

class _Tab {
  const _Tab({required this.path, required this.icon, required this.label});

  final String path;
  final IconData icon;
  final String label;
}
