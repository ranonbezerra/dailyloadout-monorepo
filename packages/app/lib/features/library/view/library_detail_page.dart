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
  LibraryEntry? _entry;

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

  void _initFromEntry(LibraryEntry entry) {
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
      ..showSnackBar(
        const SnackBar(content: Text('Entry updated')),
      );
  }

  Future<void> _onDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete entry'),
        content: const Text(
          'Are you sure you want to remove this game from your library?',
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
        // Find the entry from the loaded state.
        LibraryEntry? entry;
        if (state is LibraryLoaded) {
          final matches = state.entries.where(
            (e) => e.publicId == widget.entryPublicId,
          );
          if (matches.isNotEmpty) {
            entry = matches.first;
            _initFromEntry(entry);
          }
        }

        if (entry == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Details')),
            body: const Center(child: CircularProgressIndicator()),
          );
        }

        return Scaffold(
          appBar: AppBar(
            title: Text(entry.game.title),
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
                if (entry.game.coverUrl != null)
                  Center(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        entry.game.coverUrl!,
                        height: 200,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                      ),
                    ),
                  ),
                const SizedBox(height: 16),

                // Title
                Text(
                  entry.game.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 8),

                // Platform
                Text(
                  entry.platform.label,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
                const SizedBox(height: 16),

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
                          child: Text(
                            s[0].toUpperCase() + s.substring(1),
                          ),
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
                if (entry.game.summary != null) ...[
                  Text(
                    'Summary',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    entry.game.summary!,
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

                // Delete button
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _onDelete,
                    icon: const Icon(Icons.delete_outline),
                    label: const Text('Remove from Library'),
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
