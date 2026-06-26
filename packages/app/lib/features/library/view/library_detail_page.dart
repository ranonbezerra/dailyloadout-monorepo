import 'package:app/core/library/library_models.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Status options for the dropdown.
const _statusOptions = ['backlog', 'playing', 'paused', 'completed', 'dropped'];

class LibraryDetailPage extends StatefulWidget {
  const LibraryDetailPage({required this.entryPublicId, super.key});

  final String entryPublicId;

  @override
  State<LibraryDetailPage> createState() => _LibraryDetailPageState();
}

class _LibraryDetailPageState extends State<LibraryDetailPage> {
  final _notesController = TextEditingController();
  late String _selectedStatus;
  bool _isDirty = false;
  LibraryPlatformState? _entry;

  @override
  void initState() {
    super.initState();
    _selectedStatus = 'backlog';
  }

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  void _initFromEntry(LibraryPlatformState entry) {
    if (_entry?.publicId == entry.publicId && _isDirty) return;

    _entry = entry;
    _selectedStatus = entry.status;
    _notesController.text = entry.notes ?? '';
    _isDirty = false;
  }

  void _onSave() {
    if (_entry == null) return;

    context.read<LibraryBloc>().add(
      UpdateEntry(
        publicId: _entry!.publicId,
        status: _selectedStatus,
        notes: _notesController.text.trim().isEmpty
            ? null
            : _notesController.text.trim(),
      ),
    );

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text('Entry updated')));
  }

  Future<void> _onDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove platform'),
        content: const Text(
          'Are you sure you want to remove this platform from your library? '
          'Other platforms for this game stay.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && mounted) {
      context.read<LibraryBloc>().add(
        DeleteEntry(publicId: widget.entryPublicId),
      );
      context.go('/library');
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<LibraryBloc, LibraryState>(
      builder: (context, state) {
        // Find the platform entry (and its parent game) from the loaded state.
        LibraryPlatformState? entry;
        Game? game;
        if (state is LibraryLoaded) {
          for (final group in state.groups) {
            final matches = group.platforms.where(
              (e) => e.publicId == widget.entryPublicId,
            );
            if (matches.isNotEmpty) {
              entry = matches.first;
              game = group.game;
              _initFromEntry(entry);
              break;
            }
          }
        }

        if (entry == null || game == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Details')),
            body: const Center(child: CircularProgressIndicator()),
          );
        }

        final resolvedEntry = entry;
        final resolvedGame = game;
        final genres = resolvedGame.genres;

        return Scaffold(
          appBar: AppBar(
            title: Text(resolvedGame.title),
            actions: [
              IconButton(
                icon: const Icon(Icons.save),
                onPressed: _onSave,
                tooltip: 'Save changes',
              ),
            ],
          ),
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Cover image
                if (resolvedGame.coverUrl != null)
                  Center(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        resolvedGame.coverUrl!,
                        height: 200,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                      ),
                    ),
                  ),
                const SizedBox(height: 16),

                // Title
                Text(
                  resolvedGame.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),

                // Platform (this entry's platform)
                Text(
                  resolvedEntry.platform.label,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 8),

                // Genres (read-only — games are immutable)
                if (genres != null && genres.isNotEmpty) ...[
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      for (final genre in genres)
                        Chip(
                          label: Text(genre),
                          visualDensity: VisualDensity.compact,
                          materialTapTargetSize:
                              MaterialTapTargetSize.shrinkWrap,
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                ] else
                  const SizedBox(height: 8),

                // Status dropdown
                DropdownButtonFormField<String>(
                  initialValue: _selectedStatus,
                  decoration: const InputDecoration(
                    labelText: 'Status',
                    border: OutlineInputBorder(),
                  ),
                  items: _statusOptions
                      .map(
                        (s) => DropdownMenuItem(
                          value: s,
                          child: Text(s[0].toUpperCase() + s.substring(1)),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) {
                      setState(() {
                        _selectedStatus = value;
                        _isDirty = true;
                      });
                    }
                  },
                ),
                const SizedBox(height: 16),

                // Summary
                if (resolvedGame.summary != null) ...[
                  Text(
                    'Summary',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    resolvedGame.summary!,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                ],

                // Notes
                TextFormField(
                  controller: _notesController,
                  decoration: const InputDecoration(
                    labelText: 'Notes',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 4,
                  onChanged: (_) => setState(() => _isDirty = true),
                ),
                const SizedBox(height: 24),

                // Start Mission for this platform entry (only when playing).
                if (resolvedEntry.status == 'playing') ...[
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () => context.push(
                        '/missions/briefing?entry=${resolvedEntry.publicId}',
                      ),
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start Mission'),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],

                // Delete button (removes just this platform).
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _onDelete,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Remove this platform'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
