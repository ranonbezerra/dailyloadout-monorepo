import 'package:app/core/theme/slate_theme.dart';
import 'package:flutter/material.dart';

/// Brand devices (BRAND.md §9) — reusable elements that make any screen feel
/// like Slate.
///
/// **The one-coral rule:** use a SINGLE coral focal point per screen. A lit
/// [DLSlot], the lit slot in a [DLLineup], and a [DLSpotlight] glow all count
/// as the coral focus — don't stack them on the same screen.

/// The slot — the rounded-square brand cell. Lit (coral) marks the selected
/// pick / active session; outlined (muted) is a waiting slot.
class DLSlot extends StatelessWidget {
  const DLSlot({super.key, this.lit = false, this.size = 56, this.child});

  final bool lit;
  final double size;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: lit
            ? DLColors.coral.withValues(alpha: 0.13)
            : Colors.transparent,
        border: Border.all(
          color: lit ? DLColors.coral : DLColors.line,
          width: 2,
        ),
        boxShadow: lit
            ? [
                BoxShadow(
                  color: DLColors.coral.withValues(alpha: 0.45),
                  blurRadius: 16,
                ),
              ]
            : null,
      ),
      child: child,
    );
  }
}

/// The lineup — a row of slots, one lit: "one chosen from many". Use for empty
/// states, loading, and the loadout reveal. Exactly one slot is lit.
class DLLineup extends StatelessWidget {
  const DLLineup({
    super.key,
    this.count = 5,
    this.litIndex,
    this.size = 40,
    this.gap = 10,
  });

  final int count;
  final int? litIndex;
  final double size;
  final double gap;

  @override
  Widget build(BuildContext context) {
    final lit = litIndex ?? count ~/ 2;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < count; i++) ...[
          if (i > 0) SizedBox(width: gap),
          DLSlot(lit: i == lit, size: size),
        ],
      ],
    );
  }
}

/// The recap label — "▸ PREVIOUSLY ON". A play glyph plus an uppercase,
/// letter-spaced label in the display face. Editorial TV-recap, not a terminal.
class DLRecapLabel extends StatelessWidget {
  const DLRecapLabel(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(
      '▸ ${label.toUpperCase()}',
      style: const TextStyle(
        fontFamily: 'Outfit',
        fontWeight: FontWeight.w600,
        fontSize: 12,
        letterSpacing: 0.96,
        color: DLColors.violet,
      ),
    );
  }
}

/// The spotlight — a soft coral glow behind tonight's pick. Warmth and focus,
/// used ONCE per screen, on the thing that matters.
class DLSpotlight extends StatelessWidget {
  const DLSpotlight({required this.child, super.key, this.active = true});

  final Widget child;
  final bool active;

  @override
  Widget build(BuildContext context) {
    if (!active) return child;
    return DecoratedBox(
      decoration: BoxDecoration(
        boxShadow: [
          BoxShadow(
            color: DLColors.coral.withValues(alpha: 0.28),
            blurRadius: 48,
            spreadRadius: 4,
          ),
        ],
      ),
      child: child,
    );
  }
}
