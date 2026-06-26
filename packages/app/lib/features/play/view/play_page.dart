import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// The Play hub: the landing surface for everything related to deciding what
/// to play. It surfaces the active mission front-and-centre and offers three
/// "doors" — let us pick, pick yourself, or ask the concierge.
class PlayPage extends StatefulWidget {
  const PlayPage({this.conciergeEnabled = false, super.key});

  /// Whether to surface the Backlog Concierge door (gated by a feature flag).
  final bool conciergeEnabled;

  @override
  State<PlayPage> createState() => _PlayPageState();
}

class _PlayPageState extends State<PlayPage> {
  @override
  void initState() {
    super.initState();
    context.read<MissionBloc>().add(const LoadActiveMission());
  }

  Future<void> _onRefresh() async {
    context.read<MissionBloc>().add(const LoadActiveMission());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Play')),
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          children: [
            BlocBuilder<MissionBloc, MissionState>(
              builder: (context, state) {
                final hasActiveMission =
                    state is ActiveMissionLoaded && state.mission != null;
                final hasError = state is MissionError;

                // While the mission state is unknown (loading or errored) we
                // can't safely confirm there is no active mission, so the
                // start-doors stay locked to avoid double-starting.
                final doorsDisabledHint = hasActiveMission
                    ? 'Finish your active mission first'
                    : hasError
                    ? 'Could not check your active mission'
                    : null;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (hasActiveMission)
                      _ActiveMissionCard(mission: state.mission!)
                    else if (state is MissionLoading)
                      const _ActiveMissionPlaceholder()
                    else if (hasError)
                      _ActiveMissionError(
                        message: state.message,
                        onRetry: _onRefresh,
                      )
                    else
                      const _NoActiveMissionCard(),
                    const SizedBox(height: 24),
                    Text(
                      "What's next?",
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    _DoorCard(
                      icon: Icons.casino,
                      title: "What's the move?",
                      subtitle: 'One tap — we pick, you play.',
                      accent: DLColors.coral,
                      // Starting a new mission is blocked while one is active
                      // or while we couldn't confirm there isn't one.
                      disabledHint: doorsDisabledHint,
                      onTap: () => context.go('/play/loadout'),
                    ),
                    const SizedBox(height: 12),
                    _DoorCard(
                      icon: Icons.videogame_asset,
                      title: "I'll choose",
                      subtitle: 'Pick a game yourself.',
                      accent: DLColors.violet,
                      disabledHint: doorsDisabledHint,
                      onTap: () => context.go('/library'),
                    ),
                    if (widget.conciergeEnabled) ...[
                      const SizedBox(height: 12),
                      // The Ask door stays enabled even during an active
                      // mission — it does not start anything.
                      _DoorCard(
                        icon: Icons.auto_awesome,
                        title: 'Ask',
                        subtitle: 'Chat about what to play.',
                        accent: DLColors.green,
                        onTap: () => context.go('/play/concierge'),
                      ),
                    ],
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

/// Prominent card surfacing the currently active mission.
class _ActiveMissionCard extends StatelessWidget {
  const _ActiveMissionCard({required this.mission});

  final Mission mission;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final briefing = mission.briefingText?.trim();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.flag, color: DLColors.coral, size: 18),
                const SizedBox(width: 6),
                Text(
                  'Active mission',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: DLColors.coral,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              mission.libraryEntry.game.title,
              style: theme.textTheme.titleLarge,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              mission.libraryEntry.platform.label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            if (briefing != null && briefing.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                briefing,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () =>
                        context.push('/missions/${mission.publicId}/briefing'),
                    icon: const Icon(Icons.article_outlined),
                    label: const Text('Briefing'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () =>
                        context.push('/missions/${mission.publicId}/debrief'),
                    child: const Text('End / Debrief'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Loading placeholder shown while the active mission is being fetched.
class _ActiveMissionPlaceholder extends StatelessWidget {
  const _ActiveMissionPlaceholder();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: SizedBox(
        height: 140,
        child: Center(child: CircularProgressIndicator()),
      ),
    );
  }
}

/// Friendly empty state shown when there is no active mission.
class _NoActiveMissionCard extends StatelessWidget {
  const _NoActiveMissionCard();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.rocket_launch_outlined,
              size: 40,
              color: colors.onSurfaceVariant,
            ),
            const SizedBox(height: 12),
            Text('No mission running', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'Pick something below and start playing.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Error card shown when the active mission could not be loaded.
class _ActiveMissionError extends StatelessWidget {
  const _ActiveMissionError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.error_outline, size: 40, color: colors.error),
            const SizedBox(height: 12),
            Text(
              "Couldn't load your mission",
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

/// A tappable "door" leading into one of the three play paths.
///
/// When [disabledHint] is non-null the door is greyed out and non-tappable,
/// and the hint replaces the subtitle to explain why.
class _DoorCard extends StatelessWidget {
  const _DoorCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.onTap,
    this.disabledHint,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final Color accent;
  final VoidCallback onTap;
  final String? disabledHint;

  bool get _isDisabled => disabledHint != null;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final effectiveAccent = _isDisabled ? colors.onSurfaceVariant : accent;

    return Opacity(
      opacity: _isDisabled ? 0.5 : 1,
      child: Card(
        child: InkWell(
          onTap: _isDisabled ? null : onTap,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: effectiveAccent.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, color: effectiveAccent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: theme.textTheme.titleMedium),
                      const SizedBox(height: 2),
                      Text(
                        disabledHint ?? subtitle,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: colors.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(_isDisabled ? Icons.lock_outline : Icons.chevron_right),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
