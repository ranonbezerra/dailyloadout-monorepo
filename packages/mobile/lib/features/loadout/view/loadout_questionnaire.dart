import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:flutter/material.dart';

/// Questionnaire form for choosing loadout parameters:
/// mood, available time, mental energy, context, and
/// multi-mode toggle.
class LoadoutQuestionnaire extends StatelessWidget {
  const LoadoutQuestionnaire({
    required this.mood,
    required this.minutes,
    required this.mentalEnergy,
    required this.multiMode,
    required this.contextController,
    required this.isLoading,
    required this.onMoodChanged,
    required this.onMinutesChanged,
    required this.onEnergyChanged,
    required this.onMultiModeChanged,
    required this.onRoll,
    this.error,
    super.key,
  });

  final String mood;
  final double minutes;
  final String mentalEnergy;
  final bool multiMode;
  final TextEditingController contextController;
  final bool isLoading;
  final String? error;
  final ValueChanged<String> onMoodChanged;
  final ValueChanged<double> onMinutesChanged;
  final ValueChanged<String> onEnergyChanged;
  final ValueChanged<bool> onMultiModeChanged;
  final VoidCallback onRoll;

  static const _moods = <String, String>{
    'chill': 'Chill',
    'focused': 'Focused',
    'energetic': 'Energetic',
    'adventurous': 'Adventurous',
  };

  static const _energyLevels = <String, String>{
    'low': 'Low',
    'medium': 'Medium',
    'high': 'High',
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Mood picker
        Text('Mood', style: theme.textTheme.titleSmall),
        const SizedBox(height: 8),
        _buildChoiceRow(
          options: _moods,
          selected: mood,
          onChanged: onMoodChanged,
        ),
        const SizedBox(height: 24),

        // Time slider
        Text('Available time', style: theme.textTheme.titleSmall),
        const SizedBox(height: 4),
        Text(
          formatMinutes(minutes.round()),
          style: theme.textTheme.headlineSmall?.copyWith(color: DLColors.coral),
        ),
        Slider(
          value: minutes,
          min: 10,
          max: 480,
          divisions: 47,
          label: formatMinutes(minutes.round()),
          onChanged: onMinutesChanged,
        ),
        const SizedBox(height: 16),

        // Mental energy picker
        Text('Mental energy', style: theme.textTheme.titleSmall),
        const SizedBox(height: 8),
        _buildChoiceRow(
          options: _energyLevels,
          selected: mentalEnergy,
          onChanged: onEnergyChanged,
        ),
        const SizedBox(height: 24),

        // Context input
        TextFormField(
          controller: contextController,
          maxLength: 120,
          decoration: const InputDecoration(
            labelText: 'Context (optional)',
            hintText:
                'e.g. feeling nostalgic, '
                'want something story-driven...',
          ),
        ),
        const SizedBox(height: 16),

        // Multi-mode switch
        SwitchListTile(
          title: const Text('Show multiple suggestions (up to 3)'),
          value: multiMode,
          onChanged: onMultiModeChanged,
          contentPadding: EdgeInsets.zero,
          activeTrackColor: DLColors.coral,
        ),
        const SizedBox(height: 24),

        // Error text
        if (error != null) ...[
          Text(
            error!,
            style: theme.textTheme.bodyMedium?.copyWith(color: DLColors.red),
          ),
          const SizedBox(height: 12),
        ],

        // Roll button
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: isLoading ? null : onRoll,
            icon: isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: DLColors.bg,
                    ),
                  )
                : const Icon(Icons.casino),
            label: Text(isLoading ? 'Picking...' : 'Roll the dice'),
          ),
        ),
      ],
    );
  }

  Widget _buildChoiceRow({
    required Map<String, String> options,
    required String selected,
    required ValueChanged<String> onChanged,
  }) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: options.entries.map((e) {
        final isSelected = e.key == selected;
        return ChoiceChip(
          label: Text(e.value),
          selected: isSelected,
          onSelected: (_) => onChanged(e.key),
          selectedColor: DLColors.coral,
          labelStyle: TextStyle(
            color: isSelected ? DLColors.bg : DLColors.text,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
          ),
        );
      }).toList(),
    );
  }
}

/// Formats minutes into a human-readable duration
/// string such as "1h 30m" or "45m".
String formatMinutes(int minutes) {
  if (minutes >= 60) {
    final h = minutes ~/ 60;
    final m = minutes % 60;
    return m > 0 ? '${h}h ${m}m' : '${h}h';
  }
  return '${minutes}m';
}
