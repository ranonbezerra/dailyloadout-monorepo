import 'package:app/core/play_session/play_session_models.dart';
import 'package:app/core/theme/slate_theme.dart';
import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// The Play hub: the landing surface for everything related to deciding what
/// to play. It surfaces the active session front-and-centre and offers three
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
    context.read<PlaySessionBloc>().add(const LoadActivePlaySession());
  }

  Future<void> _onRefresh() async {
    context.read<PlaySessionBloc>().add(const LoadActivePlaySession());
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
            BlocBuilder<PlaySessionBloc, PlaySessionState>(
              builder: (context, state) {
                final hasActivePlaySession =
                    state is ActivePlaySessionLoaded &&
                    state.playSession != null;
                final hasError = state is PlaySessionError;

                // While the session state is unknown (loading or errored) we
                // can't safely confirm there is no active playSession, so the
                // start-doors stay locked to avoid double-starting.
                final doorsDisabledHint = hasActivePlaySession
                    ? 'Finish your active session first'
                    : hasError
                    ? 'Could not check your active session'
                    : null;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (hasActivePlaySession)
                      _ActivePlaySessionCard(playSession: state.playSession!)
                    else if (state is PlaySessionLoading)
                      const _ActivePlaySessionPlaceholder()
                    else if (hasError)
                      _ActivePlaySessionError(
                        message: state.message,
                        onRetry: _onRefresh,
                      )
                    else
                      const _NoActivePlaySessionCard(),
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
                      // Starting a new session is blocked while one is active
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
                      // playSession — it does not start anything.
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

/// Prominent card surfacing the currently active playSession.
class _ActivePlaySessionCard extends StatelessWidget {
  const _ActivePlaySessionCard({required this.playSession});

  final PlaySession playSession;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final recap = playSession.recapText?.trim();

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
                  'Active session',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: DLColors.coral,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              playSession.libraryEntry.game.title,
              style: theme.textTheme.titleLarge,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              playSession.libraryEntry.platform.label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            if (recap != null && recap.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                recap,
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
                    onPressed: () => context.push(
                      '/play-sessions/${playSession.publicId}/recap',
                    ),
                    icon: const Icon(Icons.article_outlined),
                    label: const Text('Recap'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => context.push(
                      '/play-sessions/${playSession.publicId}/wrap-up',
                    ),
                    child: const Text('Wrap up'),
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

/// Loading placeholder shown while the active playSession is being fetched.
class _ActivePlaySessionPlaceholder extends StatelessWidget {
  const _ActivePlaySessionPlaceholder();

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

/// Friendly empty state shown when there is no active playSession.
class _NoActivePlaySessionCard extends StatelessWidget {
  const _NoActivePlaySessionCard();

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
            Text('No session running', style: theme.textTheme.titleMedium),
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

/// Error card shown when the active playSession could not be loaded.
class _ActivePlaySessionError extends StatelessWidget {
  const _ActivePlaySessionError({required this.message, required this.onRetry});

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
              "Couldn't load your session",
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
