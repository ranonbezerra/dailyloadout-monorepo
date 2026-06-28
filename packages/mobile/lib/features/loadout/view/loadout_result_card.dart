import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:flutter/material.dart';

/// Displays a single loadout suggestion with game info,
/// reasoning, and accept/reject actions.
class LoadoutResultCard extends StatelessWidget {
  const LoadoutResultCard({
    required this.loadout,
    required this.rank,
    required this.totalResults,
    required this.onAccept,
    required this.onReject,
    required this.onGetBriefing,
    required this.onStartWithBriefing,
    required this.isActioning,
    required this.isGeneratingBriefing,
    this.briefingText,
    super.key,
  });

  final Loadout loadout;
  final int rank;
  final int totalResults;
  final VoidCallback onAccept;
  final VoidCallback onReject;

  /// Requests a briefing for this game in the given mode ('quick' | 'deep').
  final void Function(String mode) onGetBriefing;

  /// Starts the mission carrying the generated [briefingText].
  final VoidCallback onStartWithBriefing;
  final bool isActioning;

  /// Whether a briefing is currently being generated for this card.
  final bool isGeneratingBriefing;

  /// The generated briefing text, if any has been produced yet.
  final String? briefingText;

  String? get _rankLabel {
    if (totalResults <= 1) return null;
    return switch (rank) {
      0 => 'Best Match',
      1 => 'Great Alternative',
      _ => 'Worth Considering',
    };
  }

  Color? get _rankColor {
    if (totalResults <= 1) return null;
    return switch (rank) {
      0 => DLColors.green,
      1 => DLColors.violet,
      _ => DLColors.textDim,
    };
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final entry = loadout.libraryEntry;
    final game = entry?.game;
    final platform = entry?.platform;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Rank badge
            if (_rankLabel != null) ...[
              _RankBadge(label: _rankLabel!, color: _rankColor!),
              const SizedBox(height: 12),
            ],

            // Game title
            Text(
              game?.title ?? 'Unknown game',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),

            // Platform + status row
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                if (platform != null) _InfoChip(label: platform.label),
                if (entry?.status != null)
                  _InfoChip(label: _capitalize(entry!.status)),
              ],
            ),

            // Genre chips
            if (game?.genres != null && game!.genres!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: game.genres!
                    .map((g) => _GenreChip(label: g))
                    .toList(),
              ),
            ],

            // Reasoning
            if (loadout.reasoning != null && loadout.reasoning!.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                loadout.reasoning!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontStyle: FontStyle.italic,
                  color: DLColors.textMuted,
                ),
              ),
            ],

            const SizedBox(height: 16),

            // Action area
            _buildActions(context),
          ],
        ),
      ),
    );
  }

  Widget _buildActions(BuildContext context) {
    final theme = Theme.of(context);

    if (loadout.action == 'accepted') {
      return Row(
        children: [
          const Icon(Icons.check_circle, color: DLColors.green, size: 20),
          const SizedBox(width: 8),
          Text(
            'Mission started!',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: DLColors.green,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
    }

    if (loadout.action == 'rejected') {
      return Text(
        'Rejected',
        style: theme.textTheme.bodyMedium?.copyWith(color: DLColors.textDim),
      );
    }

    final hasBriefing = briefingText != null && briefingText!.isNotEmpty;
    final busy = isActioning || isGeneratingBriefing;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Generated briefing preview.
        if (hasBriefing) ...[
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: DLColors.surface2,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.article_outlined,
                      size: 16,
                      color: DLColors.violet,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Briefing',
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: DLColors.violet,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(briefingText!, style: theme.textTheme.bodyMedium),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],

        // Briefing options (until one is generated): quick vs deep.
        if (!hasBriefing) ...[
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: busy ? null : () => onGetBriefing('quick'),
                  icon: const Icon(Icons.bolt, size: 18),
                  label: const Text('Quick briefing'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: busy ? null : () => onGetBriefing('deep'),
                  icon: isGeneratingBriefing
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.travel_explore, size: 18),
                  label: const Text('Deep briefing'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
        ],

        // Reject.
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: busy ? null : onReject,
            style: OutlinedButton.styleFrom(
              foregroundColor: DLColors.red,
              side: const BorderSide(color: DLColors.red),
            ),
            child: const Text('Reject'),
          ),
        ),
        const SizedBox(height: 12),

        // Primary action: start (with briefing when one is present).
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: busy
                ? null
                : (hasBriefing ? onStartWithBriefing : onAccept),
            style: FilledButton.styleFrom(
              backgroundColor: DLColors.green,
              foregroundColor: DLColors.bg,
            ),
            icon: isActioning
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: DLColors.bg,
                    ),
                  )
                : const Icon(Icons.play_arrow),
            label: Text(
              isActioning
                  ? 'Starting...'
                  : hasBriefing
                  ? 'Start with briefing'
                  : 'Just play',
            ),
          ),
        ),
      ],
    );
  }

  String _capitalize(String s) {
    if (s.isEmpty) return s;
    return s[0].toUpperCase() + s.substring(1);
  }
}

class _RankBadge extends StatelessWidget {
  const _RankBadge({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: DLColors.surface2,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: const TextStyle(color: DLColors.textMuted, fontSize: 12),
      ),
    );
  }
}

class _GenreChip extends StatelessWidget {
  const _GenreChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(label),
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
      labelPadding: const EdgeInsets.symmetric(horizontal: 6),
    );
  }
}
