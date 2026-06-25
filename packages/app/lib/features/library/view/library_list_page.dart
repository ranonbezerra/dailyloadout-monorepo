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
                  if (state.entries.isEmpty) {
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
                      itemCount: state.entries.length,
                      itemBuilder: (context, index) {
                        final entry = state.entries[index];
                        return _LibraryEntryCard(
                          entry: entry,
                          onTap: () =>
                              context.push('/library/${entry.publicId}'),
                          onStartMission: entry.status == 'playing'
                              ? () => context.push(
                                  '/missions/briefing?entry=${entry.publicId}',
                                )
                              : null,
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

class _LibraryEntryCard extends StatelessWidget {
  const _LibraryEntryCard({
    required this.entry,
    required this.onTap,
    this.onStartMission,
  });

  final LibraryEntry entry;
  final VoidCallback onTap;
  final VoidCallback? onStartMission;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              // Cover image or placeholder
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  width: 56,
                  height: 72,
                  child: entry.game.coverUrl != null
                      ? Image.network(
                          entry.game.coverUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) =>
                              const _CoverPlaceholder(),
                        )
                      : const _CoverPlaceholder(),
                ),
              ),
              const SizedBox(width: 12),
              // Game info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      entry.game.title,
                      style: theme.textTheme.titleSmall,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      entry.platform.label,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _StatusChip(status: entry.status),
                  ],
                ),
              ),
              if (entry.status == 'playing' && onStartMission != null)
                IconButton(
                  icon: const Icon(Icons.play_arrow),
                  onPressed: onStartMission,
                  tooltip: 'Start Mission',
                  iconSize: 20,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(
                    minWidth: 32,
                    minHeight: 32,
                  ),
                ),
              const Icon(Icons.chevron_right),
            ],
          ),
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
