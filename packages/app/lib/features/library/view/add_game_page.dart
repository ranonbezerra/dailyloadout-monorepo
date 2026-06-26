import 'dart:async';

import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Status options for adding a new library entry.
const _statusOptions = ['backlog', 'playing', 'paused', 'completed', 'dropped'];

class AddGamePage extends StatefulWidget {
  const AddGamePage({required this.libraryRepository, super.key});

  final LibraryRepository libraryRepository;

  @override
  State<AddGamePage> createState() => _AddGamePageState();
}

class _AddGamePageState extends State<AddGamePage> {
  // Search state
  final _searchController = TextEditingController();
  Timer? _debounce;
  List<Game> _searchResults = [];
  bool _isSearching = false;

  // Selection state
  Game? _selectedGame;
  bool _isManualCreation = false;
  final _manualTitleController = TextEditingController();

  // Entry details
  List<Platform> _platforms = [];
  final Set<int> _selectedPlatformIds = {};
  String _selectedStatus = 'backlog';
  final _notesController = TextEditingController();

  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _loadPlatforms();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _debounce?.cancel();
    _manualTitleController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _loadPlatforms() async {
    try {
      final platforms = await widget.libraryRepository.listPlatforms();
      if (mounted) {
        setState(() {
          _platforms = platforms;
          if (platforms.isNotEmpty) {
            _selectedPlatformIds.add(platforms.first.id);
          }
        });
      }
    } on Exception catch (_) {
      // Platforms will remain empty; user can still try later.
    }
  }

  void _onSearchChanged(String query) {
    _debounce?.cancel();

    if (query.trim().isEmpty) {
      setState(() {
        _searchResults = [];
        _isSearching = false;
      });
      return;
    }

    _debounce = Timer(const Duration(milliseconds: 400), () async {
      if (!mounted) return;
      setState(() => _isSearching = true);

      try {
        final results = await widget.libraryRepository.searchGames(
          query.trim(),
        );
        if (mounted) {
          setState(() {
            _searchResults = results;
            _isSearching = false;
          });
        }
      } on Exception catch (_) {
        if (mounted) {
          setState(() => _isSearching = false);
        }
      }
    });
  }

  void _onGameSelected(Game game) {
    setState(() {
      _selectedGame = game;
      _isManualCreation = false;
    });
  }

  void _onManualCreation() {
    setState(() {
      _selectedGame = null;
      _isManualCreation = true;
    });
  }

  void _onBack() {
    if (_selectedGame != null || _isManualCreation) {
      setState(() {
        _selectedGame = null;
        _isManualCreation = false;
      });
    } else {
      context.go('/library');
    }
  }

  String _slugFromTitle(String title) {
    return title
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9\s-]'), '')
        .replaceAll(RegExp(r'\s+'), '-')
        .replaceAll(RegExp('-+'), '-');
  }

  Future<void> _onSubmit() async {
    if (_selectedPlatformIds.isEmpty) return;

    setState(() => _isSubmitting = true);

    try {
      String gamePublicId;

      if (_isManualCreation) {
        final title = _manualTitleController.text.trim();
        if (title.isEmpty) {
          setState(() => _isSubmitting = false);
          return;
        }

        final game = await widget.libraryRepository.createGame(
          slug: _slugFromTitle(title),
          title: title,
        );
        gamePublicId = game.publicId;
      } else {
        gamePublicId = _selectedGame!.publicId;
      }

      if (!mounted) return;

      context.read<LibraryBloc>().add(
        AddEntry(
          gamePublicId: gamePublicId,
          platformIds: _selectedPlatformIds.toList()..sort(),
          status: _selectedStatus,
          notes: _notesController.text.trim().isEmpty
              ? null
              : _notesController.text.trim(),
        ),
      );

      context.go('/library');
    } on Exception catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            SnackBar(
              content: Text('Failed to add game: $e'),
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
          );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final showDetails = _selectedGame != null || _isManualCreation;

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _onBack,
        ),
        title: Text(showDetails ? 'Add to Library' : 'Search Games'),
      ),
      body: showDetails ? _buildDetailsStep() : _buildSearchStep(),
    );
  }

  Widget _buildSearchStep() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: TextField(
            controller: _searchController,
            decoration: const InputDecoration(
              labelText: 'Search games',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.search),
            ),
            onChanged: _onSearchChanged,
          ),
        ),
        if (_isSearching) const LinearProgressIndicator(),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [
              ..._searchResults.map(
                (game) => ListTile(
                  leading: SizedBox(
                    width: 40,
                    height: 52,
                    child: game.coverUrl != null
                        ? ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: Image.network(
                              game.coverUrl!,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) =>
                                  const Icon(Icons.videogame_asset),
                            ),
                          )
                        : const Icon(Icons.videogame_asset),
                  ),
                  title: Text(game.title),
                  subtitle: game.genres != null && game.genres!.isNotEmpty
                      ? Text(game.genres!.join(', '))
                      : null,
                  onTap: () => _onGameSelected(game),
                ),
              ),
              if (_searchController.text.trim().isNotEmpty) ...[
                const Divider(),
                ListTile(
                  leading: const Icon(Icons.add_circle_outline),
                  title: const Text('Create manually'),
                  subtitle: const Text('Add a game not in the database'),
                  onTap: _onManualCreation,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildDetailsStep() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Selected game title or manual title input
          if (_isManualCreation) ...[
            TextFormField(
              controller: _manualTitleController,
              decoration: const InputDecoration(
                labelText: 'Game title',
                border: OutlineInputBorder(),
              ),
            ),
          ] else ...[
            Text(
              _selectedGame!.title,
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            if (_selectedGame!.summary != null) ...[
              const SizedBox(height: 8),
              Text(
                _selectedGame!.summary!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ],
          const SizedBox(height: 16),

          // Platform multi-select — a game can be owned on several platforms.
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Platforms',
              style: Theme.of(context).textTheme.titleSmall,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: _platforms.map((p) {
              final selected = _selectedPlatformIds.contains(p.id);
              return FilterChip(
                label: Text(p.label),
                selected: selected,
                onSelected: (value) {
                  setState(() {
                    if (value) {
                      _selectedPlatformIds.add(p.id);
                    } else {
                      _selectedPlatformIds.remove(p.id);
                    }
                  });
                },
              );
            }).toList(),
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
                    child: Text(s[0].toUpperCase() + s.substring(1)),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) {
                setState(() => _selectedStatus = value);
              }
            },
          ),
          const SizedBox(height: 16),

          // Notes
          TextFormField(
            controller: _notesController,
            decoration: const InputDecoration(
              labelText: 'Notes (optional)',
              border: OutlineInputBorder(),
              alignLabelWithHint: true,
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 24),

          // Submit button
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: _isSubmitting || _selectedPlatformIds.isEmpty
                  ? null
                  : _onSubmit,
              child: _isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Add to Library'),
            ),
          ),
        ],
      ),
    );
  }
}
