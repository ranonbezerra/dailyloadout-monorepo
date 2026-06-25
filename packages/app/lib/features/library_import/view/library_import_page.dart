import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

/// Describes one importable storefront / platform option.
class ImportPlatform {
  const ImportPlatform({
    required this.label,
    required this.icon,
    required this.hint,
    required this.matchToken,
  });

  /// Display name shown on the picker card.
  final String label;

  /// Leading icon for the picker card.
  final IconData icon;

  /// Verbatim instruction text shown on the hint step.
  final String hint;

  /// Lowercased token used to default-match a [Platform] by slug/label.
  final String matchToken;
}

/// The fixed set of supported import sources, in display order.
const List<ImportPlatform> kImportPlatforms = [
  ImportPlatform(
    label: 'Steam',
    icon: Icons.computer,
    matchToken: 'steam',
    hint:
        'Open your Steam Library and switch to List view (the left rail '
        'shows titles as text). Screenshot that list.',
  ),
  ImportPlatform(
    label: 'Xbox',
    icon: Icons.sports_esports,
    matchToken: 'xbox',
    hint:
        'Open My games & apps → Full library and switch to List / Details '
        'view so titles render as text rows.',
  ),
  ImportPlatform(
    label: 'GOG',
    icon: Icons.videogame_asset,
    matchToken: 'gog',
    hint: 'In GOG Galaxy, switch to List view, or use your web library list.',
  ),
  ImportPlatform(
    label: 'PlayStation',
    icon: Icons.gamepad,
    matchToken: 'ps',
    hint:
        'Open your Game Library, or the PS App list on your phone (the '
        'web/app account list is cleanest).',
  ),
  ImportPlatform(
    label: 'Epic',
    icon: Icons.storefront,
    matchToken: 'epic',
    hint:
        'The Epic launcher is grid-only — open Account → Transactions on the '
        'web for a clean text list.',
  ),
  ImportPlatform(
    label: 'Nintendo Switch',
    icon: Icons.videogame_asset_outlined,
    matchToken: 'switch',
    hint:
        'The console is an icon grid — open Nintendo Account → Purchase '
        'history on the web for text.',
  ),
];

/// Library entry statuses offered after import.
const _statusOptions = ['backlog', 'playing', 'paused', 'completed', 'dropped'];

/// Which step of the import wizard is visible.
enum _ImportStep { pickPlatform, hint, confirm }

/// Stepped full-screen flow for importing a library from storefront
/// screenshots: pick a platform, follow the per-platform hint and pick
/// screenshots, then review and bulk-confirm the extracted titles.
class LibraryImportPage extends StatefulWidget {
  const LibraryImportPage({required this.libraryRepository, super.key});

  final LibraryRepository libraryRepository;

  @override
  State<LibraryImportPage> createState() => _LibraryImportPageState();
}

class _LibraryImportPageState extends State<LibraryImportPage> {
  final _picker = ImagePicker();

  _ImportStep _step = _ImportStep.pickPlatform;
  late ImportPlatform _platform;
  final List<String> _imagePaths = [];

  List<Platform> _platforms = [];

  // Confirmation step selections.
  final Set<String> _checkedIds = {};
  int? _selectedPlatformId;
  String _selectedStatus = 'backlog';

  @override
  void initState() {
    super.initState();
    _loadPlatforms();
  }

  Future<void> _loadPlatforms() async {
    try {
      final platforms = await widget.libraryRepository.listPlatforms();
      if (mounted) {
        setState(() => _platforms = platforms);
      }
    } on Exception catch (_) {
      // Platforms remain empty; the dropdown will simply have no options.
    }
  }

  /// Finds the platform whose slug or label contains the picker token.
  int? _defaultPlatformId(ImportPlatform option) {
    for (final p in _platforms) {
      if (p.slug.toLowerCase().contains(option.matchToken) ||
          p.label.toLowerCase().contains(option.matchToken)) {
        return p.id;
      }
    }
    return _platforms.isNotEmpty ? _platforms.first.id : null;
  }

  void _onPlatformSelected(ImportPlatform option) {
    setState(() {
      _platform = option;
      _selectedPlatformId = _defaultPlatformId(option);
      _step = _ImportStep.hint;
    });
  }

  Future<void> _pickScreenshots() async {
    final images = await _picker.pickMultiImage(imageQuality: 85);
    if (images.isNotEmpty) {
      setState(() {
        _imagePaths
          ..clear()
          ..addAll(images.map((x) => x.path));
      });
    }
  }

  void _onImport() {
    if (_imagePaths.isEmpty) return;
    context.read<LibraryImportBloc>().add(
      SubmitLibraryImport(imagePaths: _imagePaths),
    );
  }

  void _onReviewReady(Capture capture) {
    // Default every extracted candidate to checked.
    _checkedIds
      ..clear()
      ..addAll(capture.candidates.map((c) => c.publicId));
    _selectedPlatformId ??= _platforms.isNotEmpty ? _platforms.first.id : null;
    _step = _ImportStep.confirm;
  }

  void _onAddGames(String captureId) {
    final platformId = _selectedPlatformId;
    if (platformId == null || _checkedIds.isEmpty) return;
    context.read<LibraryImportBloc>().add(
      BulkConfirmImport(
        captureId: captureId,
        confirmIds: _checkedIds.toList(),
        platformId: platformId,
        status: _selectedStatus,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Import from screenshots')),
      body: BlocConsumer<LibraryImportBloc, LibraryImportState>(
        listener: (context, state) {
          if (state is LibraryImportReview) {
            setState(() => _onReviewReady(state.capture));
          }

          if (state is LibraryImportDone) {
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                SnackBar(content: Text('Imported ${state.confirmed} games')),
              );
            context.go('/library');
          }

          if (state is LibraryImportError) {
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                SnackBar(
                  content: Text(state.message),
                  backgroundColor: colors.error,
                ),
              );
          }
        },
        builder: (context, state) {
          if (state is LibraryImportSubmitting) {
            return const _BusyView(label: 'Reading your screenshots...');
          }

          if (state is LibraryImportConfirming) {
            return const _BusyView(label: 'Adding games...');
          }

          if (state is LibraryImportReview || _step == _ImportStep.confirm) {
            final capture = state is LibraryImportReview ? state.capture : null;
            if (capture != null) {
              return _buildConfirmStep(context, capture);
            }
          }

          return switch (_step) {
            _ImportStep.pickPlatform => _buildPickerStep(context),
            _ImportStep.hint => _buildHintStep(context),
            _ImportStep.confirm => _buildPickerStep(context),
          };
        },
      ),
    );
  }

  // --- Step 1: platform picker ---------------------------------------------

  Widget _buildPickerStep(BuildContext context) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          'Where is your library?',
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Pick a store, screenshot your list of games, and '
          "we'll add them for you.",
          style: theme.textTheme.bodyLarge?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 24),
        for (final option in kImportPlatforms) ...[
          _CaptureOptionCard(
            icon: option.icon,
            title: option.label,
            subtitle: 'Import your ${option.label} games',
            onTap: () => _onPlatformSelected(option),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }

  // --- Step 2: hint + pick screenshots -------------------------------------

  Widget _buildHintStep(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final option = _platform;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            option.label,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          // Per-platform instruction hint box.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: colors.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.lightbulb_outline,
                      size: 18,
                      color: colors.onSurfaceVariant,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'How to get a clean list',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  option.hint,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colors.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton.icon(
              onPressed: _pickScreenshots,
              icon: const Icon(Icons.photo_library),
              label: const Text('Pick screenshots'),
            ),
          ),
          if (_imagePaths.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              '${_imagePaths.length} screenshot'
              '${_imagePaths.length == 1 ? '' : 's'} selected',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: FilledButton(
                onPressed: _onImport,
                child: Text('Import ${_imagePaths.length} screenshots'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // --- Step 3: confirmation -------------------------------------------------

  Widget _buildConfirmStep(BuildContext context, Capture capture) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final candidates = capture.candidates;

    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text(
                'We found ${candidates.length} games',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Uncheck anything you do not want, then add them all '
                'in one go.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              if (candidates.isEmpty)
                Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text(
                    'No games were detected. Try clearer screenshots of a '
                    'text list.',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: colors.onSurfaceVariant,
                    ),
                  ),
                )
              else
                ...candidates.map(
                  (candidate) => _CandidateCheckTile(
                    candidate: candidate,
                    checked: _checkedIds.contains(candidate.publicId),
                    onChanged: (value) {
                      setState(() {
                        if (value ?? false) {
                          _checkedIds.add(candidate.publicId);
                        } else {
                          _checkedIds.remove(candidate.publicId);
                        }
                      });
                    },
                  ),
                ),
              const SizedBox(height: 16),
              // Platform dropdown.
              DropdownButtonFormField<int>(
                initialValue: _selectedPlatformId,
                decoration: const InputDecoration(
                  labelText: 'Platform',
                  border: OutlineInputBorder(),
                ),
                items: _platforms
                    .map(
                      (p) =>
                          DropdownMenuItem(value: p.id, child: Text(p.label)),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _selectedPlatformId = value);
                  }
                },
              ),
              const SizedBox(height: 16),
              // Status dropdown.
              DropdownButtonFormField<String>(
                initialValue: _selectedStatus,
                decoration: const InputDecoration(
                  labelText: 'Library Status',
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
            ],
          ),
        ),
        // Sticky add button.
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: SizedBox(
              width: double.infinity,
              height: 48,
              child: FilledButton(
                onPressed: _checkedIds.isEmpty || _selectedPlatformId == null
                    ? null
                    : () => _onAddGames(capture.publicId),
                child: Text('Add ${_checkedIds.length} games'),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _BusyView extends StatelessWidget {
  const _BusyView({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(label),
        ],
      ),
    );
  }
}

/// Checkbox row for one extracted candidate: cover thumb, title, and a
/// matched/IGDB badge.
class _CandidateCheckTile extends StatelessWidget {
  const _CandidateCheckTile({
    required this.candidate,
    required this.checked,
    required this.onChanged,
  });

  final CaptureCandidate candidate;
  final bool checked;
  final ValueChanged<bool?> onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final matched = candidate.igdbTitle != null;
    final displayTitle = candidate.igdbTitle ?? candidate.title;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () => onChanged(!checked),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Row(
            children: [
              Checkbox(value: checked, onChanged: onChanged),
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: SizedBox(
                  width: 40,
                  height: 52,
                  child: candidate.igdbCoverUrl != null
                      ? Image.network(
                          candidate.igdbCoverUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) =>
                              const _ThumbPlaceholder(),
                        )
                      : const _ThumbPlaceholder(),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  displayTitle,
                  style: theme.textTheme.titleSmall,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: matched
                      ? colors.tertiary
                      : colors.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  matched ? 'IGDB' : 'New',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: matched ? Colors.black : colors.onSurfaceVariant,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ThumbPlaceholder extends StatelessWidget {
  const _ThumbPlaceholder();

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Icon(
        Icons.videogame_asset,
        size: 20,
        color: Theme.of(context).colorScheme.onSurfaceVariant,
      ),
    );
  }
}

/// Selectable option card mirroring the capture-choice card style.
class _CaptureOptionCard extends StatelessWidget {
  const _CaptureOptionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 32, color: colors.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: theme.textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: colors.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}
