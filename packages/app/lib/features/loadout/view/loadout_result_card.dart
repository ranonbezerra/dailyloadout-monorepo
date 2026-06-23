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
    required this.isActioning,
    super.key,
  });

  final Loadout loadout;
  final int rank;
  final int totalResults;
  final VoidCallback onAccept;
  final VoidCallback onReject;
  final bool isActioning;

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

    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: isActioning ? null : onReject,
            style: OutlinedButton.styleFrom(
              foregroundColor: DLColors.red,
              side: const BorderSide(color: DLColors.red),
            ),
            child: const Text('Reject'),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          flex: 2,
          child: FilledButton.icon(
            onPressed: isActioning ? null : onAccept,
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
            label: Text(isActioning ? 'Starting...' : 'Accept & Start Mission'),
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
