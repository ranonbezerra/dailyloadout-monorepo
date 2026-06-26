import 'package:app/core/mission/mission_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// Read-only history of all missions.
///
/// Active-mission management (briefing / debrief) now lives on the Play page;
/// this surface only lists past and ongoing missions.
class MissionsListPage extends StatefulWidget {
  const MissionsListPage({super.key});

  @override
  State<MissionsListPage> createState() => _MissionsListPageState();
}

class _MissionsListPageState extends State<MissionsListPage> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    context.read<MissionBloc>().add(const LoadMissions());
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController
      ..removeListener(_onScroll)
      ..dispose();
    super.dispose();
  }

  void _onScroll() {
    _maybeLoadMore();
  }

  /// Loads more missions when the user is near the bottom
  /// or when the content doesn't fill the viewport.
  void _maybeLoadMore() {
    if (!_scrollController.hasClients) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.offset;
    if (currentScroll >= maxScroll - 200) {
      context.read<MissionBloc>().add(const LoadMoreMissions());
    }
  }

  Future<void> _onRefresh() async {
    context.read<MissionBloc>().add(const LoadMissions());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mission History')),
      body: BlocConsumer<MissionBloc, MissionState>(
        listenWhen: (previous, current) =>
            current is MissionListLoaded && current.loadMoreError != null,
        listener: (context, state) {
          if (state is! MissionListLoaded) return;
          final message = state.loadMoreError;
          if (message == null) return;
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(
              SnackBar(
                content: Text('Could not load more: $message'),
                action: SnackBarAction(
                  label: 'Retry',
                  onPressed: () =>
                      context.read<MissionBloc>().add(const LoadMoreMissions()),
                ),
              ),
            );
        },
        builder: (context, state) {
          if (state is MissionLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (state is MissionError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      state.message,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _onRefresh,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          if (state is MissionListLoaded) {
            if (state.missions.isEmpty) {
              return const _EmptyState();
            }

            // After the frame renders, check if the list
            // doesn't fill the viewport and load more. Skip auto-loading
            // when the last page failed so we don't spin on the error.
            if (state.hasMore &&
                !state.isLoadingMore &&
                state.loadMoreError == null) {
              SchedulerBinding.instance.addPostFrameCallback((_) {
                _maybeLoadMore();
              });
            }

            // +1 for the loading indicator at the bottom
            // when there are more pages.
            final itemCount = state.missions.length + (state.hasMore ? 1 : 0);

            return RefreshIndicator(
              onRefresh: _onRefresh,
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                itemCount: itemCount,
                itemBuilder: (context, index) {
                  if (index >= state.missions.length) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: Center(
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    );
                  }
                  final mission = state.missions[index];
                  return _MissionCard(mission: mission);
                },
              ),
            );
          }

          // MissionInitial — show nothing while waiting for first load.
          return const SizedBox.shrink();
        },
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.rocket_launch_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              'No missions yet.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Start one from the Play tab.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MissionCard extends StatelessWidget {
  const _MissionCard({required this.mission});

  final MissionListItem mission;

  /// Whether this mission is currently active (no endedAt).
  bool get _isActive => mission.endedAt == null;

  /// Human-readable status label derived from the mission state.
  String get _statusLabel {
    if (_isActive) return 'Active';
    return switch (mission.endedVia) {
      'debrief' => 'Debriefed',
      'paused_app' => 'Paused',
      'auto_clamp' => 'Auto-closed',
      'retroactive' => 'Retroactive',
      _ => 'Ended',
    };
  }

  /// Status badge color matching the spec.
  Color _statusColor(ColorScheme colors) {
    if (_isActive) return colors.primary; // blue/coral
    return switch (mission.endedVia) {
      'debrief' => DLColors.green,
      'paused_app' => DLColors.violet,
      'auto_clamp' => DLColors.textDim,
      'retroactive' => DLColors.violetDeep,
      _ => colors.surfaceContainerHighest,
    };
  }

  /// Formatted duration string.
  String get _durationLabel {
    if (_isActive) return 'Ongoing';

    final duration = mission.endedAt!.difference(mission.startedAt);
    if (duration.inHours > 0) {
      final hours = duration.inHours;
      final minutes = duration.inMinutes.remainder(60);
      return '${hours}h ${minutes}m';
    }
    return '${duration.inMinutes}m';
  }

  /// Nicely formatted date.
  String get _startedLabel {
    final d = mission.startedAt;
    final months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', //
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    return '${months[d.month - 1]} ${d.day}, ${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row: title + status badge
            Row(
              children: [
                Expanded(
                  child: Text(
                    mission.libraryEntry.game.title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                _StatusBadge(label: _statusLabel, color: _statusColor(colors)),
              ],
            ),
            const SizedBox(height: 4),

            // Platform label
            Text(
              mission.libraryEntry.platform.label,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),

            // Duration and started date
            Row(
              children: [
                Icon(
                  Icons.timer_outlined,
                  size: 14,
                  color: colors.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  _durationLabel,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
                  ),
                ),
                const SizedBox(width: 16),
                Icon(
                  Icons.calendar_today_outlined,
                  size: 14,
                  color: colors.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Text(
                  _startedLabel,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
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

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final isOnDark =
        ThemeData.estimateBrightnessForColor(color) == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: isOnDark ? Colors.white : Colors.black,
        ),
      ),
    );
  }
}
