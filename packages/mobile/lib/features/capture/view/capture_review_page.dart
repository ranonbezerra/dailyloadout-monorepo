import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Status options for the library entry.
const _statusOptions = ['backlog', 'playing', 'paused', 'completed', 'dropped'];

/// Page for reviewing and confirming/rejecting candidates from a capture.
class CaptureReviewPage extends StatefulWidget {
  const CaptureReviewPage({
    required this.capturePublicId,
    required this.libraryRepository,
    super.key,
  });

  final String capturePublicId;
  final LibraryRepository libraryRepository;

  @override
  State<CaptureReviewPage> createState() => _CaptureReviewPageState();
}

class _CaptureReviewPageState extends State<CaptureReviewPage> {
  List<Platform> _platforms = [];

  @override
  void initState() {
    super.initState();
    _loadPlatforms();
    _ensureCaptureLoaded();
  }

  Future<void> _loadPlatforms() async {
    try {
      final platforms = await widget.libraryRepository.listPlatforms();
      if (mounted) {
        setState(() => _platforms = platforms);
      }
    } on Exception catch (_) {
      // Platforms will remain empty; confirmation will fail gracefully.
    }
  }

  void _ensureCaptureLoaded() {
    final state = context.read<CaptureBloc>().state;
    // If we already have the capture in state (e.g., came from the text page),
    // there is nothing to do. Otherwise, we need to fetch it.
    if (state is CaptureSubmitted &&
        state.capture.publicId == widget.capturePublicId) {
      return;
    }
    // No dedicated "load single capture" event; re-submit is not desired.
    // We could add a LoadCapture event, but the spec doesn't require it.
    // For now we rely on the state already being present from navigation.
  }

  void _onConfirm(
    BuildContext context,
    String captureId,
    CaptureCandidate candidate,
  ) {
    _showConfirmSheet(context, captureId, candidate);
  }

  void _onReject(
    BuildContext context,
    String captureId,
    CaptureCandidate candidate,
  ) {
    context.read<CaptureBloc>().add(
      RejectCandidate(captureId: captureId, candidateId: candidate.publicId),
    );
  }

  void _showConfirmSheet(
    BuildContext context,
    String captureId,
    CaptureCandidate candidate,
  ) {
    var selectedPlatformId = _platforms.isNotEmpty ? _platforms.first.id : null;
    var selectedStatus = 'backlog';

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            return Padding(
              padding: EdgeInsets.fromLTRB(
                24,
                24,
                24,
                24 + MediaQuery.of(sheetContext).viewInsets.bottom,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Confirm: ${candidate.igdbTitle ?? candidate.title}',
                    style: Theme.of(sheetContext).textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),

                  // Platform dropdown
                  DropdownButtonFormField<int>(
                    initialValue: selectedPlatformId,
                    decoration: const InputDecoration(
                      labelText: 'Platform',
                      border: OutlineInputBorder(),
                    ),
                    items: _platforms
                        .map(
                          (p) => DropdownMenuItem(
                            value: p.id,
                            child: Text(p.label),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        setSheetState(() => selectedPlatformId = value);
                      }
                    },
                  ),
                  const SizedBox(height: 16),

                  // Status dropdown
                  DropdownButtonFormField<String>(
                    initialValue: selectedStatus,
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
                        setSheetState(() => selectedStatus = value);
                      }
                    },
                  ),
                  const SizedBox(height: 24),

                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: FilledButton(
                      onPressed: selectedPlatformId == null
                          ? null
                          : () {
                              Navigator.of(sheetContext).pop();
                              context.read<CaptureBloc>().add(
                                ConfirmCandidate(
                                  captureId: captureId,
                                  candidateId: candidate.publicId,
                                  platformId: selectedPlatformId!,
                                  status: selectedStatus,
                                ),
                              );
                            },
                      child: const Text('Add to Library'),
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  bool _allCandidatesResolved(Capture capture) {
    if (capture.candidates.isEmpty) return false;
    return capture.candidates.every(
      (c) => c.status == 'confirmed' || c.status == 'rejected',
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Review Captures')),
      body: BlocBuilder<CaptureBloc, CaptureState>(
        builder: (context, state) {
          if (state is CaptureSubmitting || state is CaptureLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (state is CaptureError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      state.message,
                      textAlign: TextAlign.center,
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: () => context.go('/capture'),
                      child: const Text('Try Again'),
                    ),
                  ],
                ),
              ),
            );
          }

          if (state is CaptureSubmitted) {
            final capture = state.capture;
            return _buildReviewContent(context, capture);
          }

          // Initial or unexpected state — go back to capture.
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'No capture data available.',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: () => context.go('/capture'),
                  child: const Text('Start Capture'),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildReviewContent(BuildContext context, Capture capture) {
    final theme = Theme.of(context);
    final allResolved = _allCandidatesResolved(capture);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Capture status header
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  _captureStatusIcon(capture.status),
                  color: _captureStatusColor(capture.status, theme),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Capture Status',
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      Text(
                        _captureStatusLabel(capture.status),
                        style: theme.textTheme.titleSmall,
                      ),
                    ],
                  ),
                ),
                _CaptureStatusBadge(status: capture.status),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Candidates header
        Text(
          'Extracted Games (${capture.candidates.length})',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 12),

        // Candidate cards
        if (capture.candidates.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Text(
                'No games were extracted from your text. '
                'Try being more specific about game titles.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          )
        else
          ...capture.candidates.map(
            (candidate) => _CandidateCard(
              candidate: candidate,
              onConfirm: candidate.status == 'pending'
                  ? () => _onConfirm(context, capture.publicId, candidate)
                  : null,
              onReject: candidate.status == 'pending'
                  ? () => _onReject(context, capture.publicId, candidate)
                  : null,
            ),
          ),

        const SizedBox(height: 24),

        // Done button
        if (allResolved)
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton.icon(
              onPressed: () => context.go('/library'),
              icon: const Icon(Icons.check),
              label: const Text('Done — View Library'),
            ),
          ),

        // Back to capture button
        if (!allResolved)
          Center(
            child: TextButton(
              onPressed: () => context.go('/capture'),
              child: const Text('Back to Capture'),
            ),
          ),
      ],
    );
  }

  IconData _captureStatusIcon(String status) {
    return switch (status) {
      'queued' => Icons.hourglass_empty,
      'processing' => Icons.sync,
      'review' => Icons.rate_review_outlined,
      'committed' => Icons.check_circle_outline,
      'partially_committed' => Icons.check_circle_outline,
      'failed' => Icons.error_outline,
      'cancelled' => Icons.cancel_outlined,
      _ => Icons.info_outline,
    };
  }

  Color _captureStatusColor(String status, ThemeData theme) {
    return switch (status) {
      'queued' || 'processing' => theme.colorScheme.secondary,
      'review' => theme.colorScheme.primary,
      'committed' || 'partially_committed' => theme.colorScheme.tertiary,
      'failed' || 'cancelled' => theme.colorScheme.error,
      _ => theme.colorScheme.onSurfaceVariant,
    };
  }

  String _captureStatusLabel(String status) {
    return switch (status) {
      'queued' => 'Queued for processing',
      'processing' => 'Processing your text...',
      'review' => 'Ready for review',
      'committed' => 'All games added to library',
      'partially_committed' => 'Some games added to library',
      'failed' => 'Processing failed',
      'cancelled' => 'Cancelled',
      _ => status[0].toUpperCase() + status.substring(1),
    };
  }
}

class _CaptureStatusBadge extends StatelessWidget {
  const _CaptureStatusBadge({required this.status});

  final String status;

  Color _badgeColor(ColorScheme colors) {
    return switch (status) {
      'review' => colors.primary,
      'committed' || 'partially_committed' => colors.tertiary,
      'failed' || 'cancelled' => colors.error,
      _ => colors.surfaceContainerHighest,
    };
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final bgColor = _badgeColor(colors);
    final isOnDark =
        ThemeData.estimateBrightnessForColor(bgColor) == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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

class _CandidateCard extends StatelessWidget {
  const _CandidateCard({
    required this.candidate,
    this.onConfirm,
    this.onReject,
  });

  final CaptureCandidate candidate;
  final VoidCallback? onConfirm;
  final VoidCallback? onReject;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;
    final displayTitle = candidate.igdbTitle ?? candidate.title;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cover image or placeholder
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                width: 64,
                height: 84,
                child: candidate.igdbCoverUrl != null
                    ? Image.network(
                        candidate.igdbCoverUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            const _CandidateCoverPlaceholder(),
                      )
                    : const _CandidateCoverPlaceholder(),
              ),
            ),
            const SizedBox(width: 12),

            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title and status badge row
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          displayTitle,
                          style: theme.textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const SizedBox(width: 8),
                      _CandidateStatusBadge(status: candidate.status),
                    ],
                  ),

                  // Platform hint
                  if (candidate.platformHint != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      'Platform hint: ${candidate.platformHint}',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ],

                  // Confidence
                  if (candidate.confidence != null) ...[
                    const SizedBox(height: 4),
                    _ConfidenceIndicator(confidence: candidate.confidence!),
                  ],

                  // Genres
                  if (candidate.igdbGenres != null &&
                      candidate.igdbGenres!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      candidate.igdbGenres!.join(', '),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],

                  // Action buttons
                  if (candidate.status == 'pending') ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: onReject,
                            style: OutlinedButton.styleFrom(
                              foregroundColor: colors.error,
                            ),
                            child: const Text('Reject'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: FilledButton(
                            onPressed: onConfirm,
                            child: const Text('Confirm'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CandidateCoverPlaceholder extends StatelessWidget {
  const _CandidateCoverPlaceholder();

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

class _CandidateStatusBadge extends StatelessWidget {
  const _CandidateStatusBadge({required this.status});

  final String status;

  Color _badgeColor(ColorScheme colors) {
    return switch (status) {
      'confirmed' => colors.tertiary,
      'rejected' => colors.error,
      _ => colors.surfaceContainerHighest,
    };
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final bgColor = _badgeColor(colors);
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

class _ConfidenceIndicator extends StatelessWidget {
  const _ConfidenceIndicator({required this.confidence});

  final double confidence;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final percentage = (confidence * 100).round();
    final color = confidence >= 0.8
        ? theme.colorScheme.tertiary
        : confidence >= 0.5
        ? theme.colorScheme.secondary
        : theme.colorScheme.error;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 60,
          height: 4,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: confidence,
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              color: color,
            ),
          ),
        ),
        const SizedBox(width: 6),
        Text(
          '$percentage% match',
          style: theme.textTheme.labelSmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}
