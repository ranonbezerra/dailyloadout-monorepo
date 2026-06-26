import 'package:app/core/library/library_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Status filter options displayed in the dropdown.
const _statusFilters = <String, String>{
  'all': 'All',
  'backlog': 'Backlog',
  'playing': 'Playing',
  'paused': 'Paused',
  'completed': 'Completed',
  'dropped': 'Dropped',
};

class LibraryListPage extends StatefulWidget {
  const LibraryListPage({super.key});

  @override
  State<LibraryListPage> createState() => _LibraryListPageState();
}

class _LibraryListPageState extends State<LibraryListPage> {
  String _selectedFilter = 'all';

  @override
  void initState() {
    super.initState();
    context.read<LibraryBloc>().add(const LoadLibrary());
  }

  void _onFilterChanged(String? value) {
    if (value == null) return;
    setState(() => _selectedFilter = value);

    final status = value == 'all' ? null : value;
    context.read<LibraryBloc>().add(LoadLibrary(status: status));
  }

  Future<void> _onRefresh() async {
    final status = _selectedFilter == 'all' ? null : _selectedFilter;
    context.read<LibraryBloc>().add(LoadLibrary(status: status));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Library'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: DropdownButton<String>(
              value: _selectedFilter,
              underline: const SizedBox.shrink(),
              items: _statusFilters.entries
                  .map(
                    (e) => DropdownMenuItem(value: e.key, child: Text(e.value)),
                  )
                  .toList(),
              onChanged: _onFilterChanged,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: BlocBuilder<LibraryBloc, LibraryState>(
              builder: (context, state) {
                if (state is LibraryLoading) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (state is LibraryError) {
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

                if (state is LibraryLoaded) {
                  if (state.groups.isEmpty) {
                    return _EmptyState(
                      onAdd: () => context.push('/library/add'),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: _onRefresh,
                    child: ListView.builder(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      itemCount: state.groups.length,
                      itemBuilder: (context, index) {
                        final group = state.groups[index];
                        return _LibraryGameCard(
                          group: group,
                          onStartMission: (entryPublicId) => context.push(
                            '/missions/briefing?entry=$entryPublicId',
                          ),
                        );
                      },
                    ),
                  );
                }

                // LibraryInitial — show nothing while waiting for first load.
                return const SizedBox.shrink();
              },
            ),
          ),
          const _IgdbAttribution(),
        ],
      ),
      floatingActionButton: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FloatingActionButton.small(
            heroTag: 'capture_fab',
            onPressed: () => context.push('/capture'),
            tooltip: 'Quick Add',
            child: const Icon(Icons.auto_awesome),
          ),
          const SizedBox(height: 8),
          FloatingActionButton.small(
            heroTag: 'import_fab',
            onPressed: () => context.push('/library/import'),
            tooltip: 'Import from screenshots',
            child: const Icon(Icons.collections),
          ),
          const SizedBox(height: 8),
          FloatingActionButton(
            heroTag: 'add_fab',
            onPressed: () => context.push('/library/add'),
            child: const Icon(Icons.add),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onAdd});

  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.videogame_asset_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              'Your backlog is empty.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Add your first game!',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add),
              label: const Text('Add Game'),
            ),
          ],
        ),
      ),
    );
  }
}

/// One card per owned GAME, listing each platform the user owns it on.
///
/// Renders the grouped response as-is — no client-side grouping.
class _LibraryGameCard extends StatelessWidget {
  const _LibraryGameCard({required this.group, required this.onStartMission});

  final LibraryGameGroup group;

  /// Called with the chosen platform's entry public_id.
  final void Function(String entryPublicId) onStartMission;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final genres = group.game.genres;
    // The game header opens the first platform's entry detail; per-platform
    // rows below open their own entry. Games themselves are immutable.
    final firstEntryId = group.platforms.isNotEmpty
        ? group.platforms.first.publicId
        : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Game header (cover + title + read-only genres).
            InkWell(
              onTap: firstEntryId != null
                  ? () => context.push('/library/$firstEntryId')
                  : null,
              borderRadius: BorderRadius.circular(8),
              child: Row(
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: SizedBox(
                      width: 56,
                      height: 72,
                      child: group.game.coverUrl != null
                          ? Image.network(
                              group.game.coverUrl!,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) =>
                                  const _CoverPlaceholder(),
                            )
                          : const _CoverPlaceholder(),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          group.game.title,
                          style: theme.textTheme.titleSmall,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (genres != null && genres.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            genres.join(', '),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right),
                ],
              ),
            ),
            const SizedBox(height: 8),
            const Divider(height: 1),
            const SizedBox(height: 4),
            // One row per owned platform.
            for (final state in group.platforms)
              _PlatformRow(
                state: state,
                onTap: () => context.push('/library/${state.publicId}'),
                onStartMission: state.status == 'playing'
                    ? () => onStartMission(state.publicId)
                    : null,
              ),
          ],
        ),
      ),
    );
  }
}

/// A single platform row inside a game card: platform chip + status + actions.
class _PlatformRow extends StatelessWidget {
  const _PlatformRow({
    required this.state,
    required this.onTap,
    this.onStartMission,
  });

  final LibraryPlatformState state;
  final VoidCallback onTap;
  final VoidCallback? onStartMission;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Chip(
              label: Text(state.platform.label),
              visualDensity: VisualDensity.compact,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              labelStyle: theme.textTheme.labelSmall,
            ),
            const SizedBox(width: 8),
            _StatusChip(status: state.status),
            const Spacer(),
            if (onStartMission != null)
              IconButton(
                icon: const Icon(Icons.play_arrow),
                onPressed: onStartMission,
                tooltip: 'Start Mission',
                iconSize: 20,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              ),
          ],
        ),
      ),
    );
  }
}

class _CoverPlaceholder extends StatelessWidget {
  const _CoverPlaceholder();

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Center(
        child: Icon(
          Icons.videogame_asset,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  Color _chipColor(ColorScheme colors) {
    return switch (status) {
      'playing' => colors.primary,
      'completed' => colors.tertiary,
      'paused' => colors.secondary,
      'dropped' => colors.error,
      _ => colors.surfaceContainerHighest,
    };
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final bgColor = _chipColor(colors);
    final isOnDark =
        ThemeData.estimateBrightnessForColor(bgColor) == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status[0].toUpperCase() + status.substring(1),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: isOnDark ? Colors.white : Colors.black,
        ),
      ),
    );
  }
}

/// IGDB requires visible, static attribution wherever its game data is used.
class _IgdbAttribution extends StatelessWidget {
  const _IgdbAttribution();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 8),
      child: Text(
        'Game data provided by IGDB.com',
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 11, color: DLColors.textDim),
      ),
    );
  }
}
