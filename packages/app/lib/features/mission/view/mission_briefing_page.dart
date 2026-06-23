import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Step enum that controls which section of the briefing page is shown.
enum _BriefingStep { briefing, correct, retroactive }

/// Briefing preview / view page.
///
/// **Preview mode** — receives [libraryEntryPublicId] (before starting a
/// mission). Shows the generated briefing and allows corrections, retroactive
/// debrief, or starting the mission.
///
/// **View mode** — receives [missionPublicId] (for an active mission). Shows
/// the briefing and allows corrections via regeneration.
class MissionBriefingPage extends StatefulWidget {
  const MissionBriefingPage({
    this.libraryEntryPublicId,
    this.missionPublicId,
    super.key,
  }) : assert(
         libraryEntryPublicId != null || missionPublicId != null,
         'Either libraryEntryPublicId or missionPublicId must be provided.',
       );

  /// Non-null in preview mode.
  final String? libraryEntryPublicId;

  /// Non-null in view mode.
  final String? missionPublicId;

  @override
  State<MissionBriefingPage> createState() => _MissionBriefingPageState();
}

class _MissionBriefingPageState extends State<MissionBriefingPage> {
  _BriefingStep _step = _BriefingStep.briefing;
  final _correctionController = TextEditingController();
  final _retroactiveController = TextEditingController();

  bool get _isPreview => widget.libraryEntryPublicId != null;

  @override
  void initState() {
    super.initState();
    if (_isPreview) {
      context.read<MissionBloc>().add(
        PreviewBriefing(libraryEntryPublicId: widget.libraryEntryPublicId!),
      );
    } else {
      context.read<MissionBloc>().add(const LoadActiveMission());
    }
  }

  @override
  void dispose() {
    _correctionController.dispose();
    _retroactiveController.dispose();
    super.dispose();
  }

  void _onCorrect() {
    final text = _correctionController.text.trim();
    if (text.isEmpty) return;

    if (_isPreview) {
      context.read<MissionBloc>().add(
        PreviewBriefing(
          libraryEntryPublicId: widget.libraryEntryPublicId!,
          positionOverride: text,
        ),
      );
    } else {
      context.read<MissionBloc>().add(
        RegenerateBriefing(
          publicId: widget.missionPublicId!,
          currentPosition: text,
        ),
      );
    }
    _correctionController.clear();
    setState(() => _step = _BriefingStep.briefing);
  }

  void _onRetroactive() {
    final text = _retroactiveController.text.trim();
    if (text.isEmpty) return;

    context.read<MissionBloc>().add(
      SubmitRetroactiveDebrief(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        debriefText: text,
      ),
    );
    _retroactiveController.clear();
    setState(() => _step = _BriefingStep.briefing);
  }

  void _onStartMission(String? briefingText) {
    context.read<MissionBloc>().add(
      StartMission(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        briefingText: briefingText,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Mission Briefing')),
      body: SafeArea(
        child: BlocConsumer<MissionBloc, MissionState>(
          listener: (context, state) {
            if (state is MissionStarted) {
              context.go('/missions');
            }
            if (state is MissionError) {
              ScaffoldMessenger.of(context)
                ..hideCurrentSnackBar()
                ..showSnackBar(
                  SnackBar(
                    content: Text(state.message),
                    backgroundColor: theme.colorScheme.error,
                  ),
                );
            }
          },
          builder: (context, state) {
            if (state is MissionLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            // Preview mode: briefing preview loaded.
            if (state is BriefingPreviewLoaded) {
              return _buildBriefingContent(
                context,
                briefingText: state.preview.briefingText,
                gameTitle: state.preview.libraryEntry.game.title,
                platformLabel: state.preview.libraryEntry.platform.label,
              );
            }

            // View mode: active mission loaded.
            if (state is ActiveMissionLoaded && state.mission != null) {
              return _buildBriefingContent(
                context,
                briefingText: state.mission!.briefingText,
                gameTitle: state.mission!.libraryEntry.game.title,
                platformLabel: state.mission!.libraryEntry.platform.label,
              );
            }

            // View mode: mission regenerated.
            if (state is MissionStarted) {
              return _buildBriefingContent(
                context,
                briefingText: state.mission.briefingText,
                gameTitle: state.mission.libraryEntry.game.title,
                platformLabel: state.mission.libraryEntry.platform.label,
              );
            }

            if (state is MissionError) {
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
                        onPressed: () => context.pop(),
                        child: const Text('Go Back'),
                      ),
                    ],
                  ),
                ),
              );
            }

            return const SizedBox.shrink();
          },
        ),
      ),
    );
  }

  Widget _buildBriefingContent(
    BuildContext context, {
    required String? briefingText,
    required String gameTitle,
    required String platformLabel,
  }) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Game header
          Text(
            gameTitle,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            platformLabel,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 24),

          // Step content
          if (_step == _BriefingStep.briefing)
            _buildBriefingStep(context, briefingText),
          if (_step == _BriefingStep.correct) _buildCorrectStep(context),
          if (_step == _BriefingStep.retroactive)
            _buildRetroactiveStep(context),
        ],
      ),
    );
  }

  Widget _buildBriefingStep(BuildContext context, String? briefingText) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Briefing text
        if (briefingText != null && briefingText.isNotEmpty)
          Text(briefingText, style: theme.textTheme.bodyLarge)
        else
          Text(
            'No briefing available -- this is your first mission for this '
            'game. Enjoy the adventure!',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
        const SizedBox(height: 32),

        // Action buttons
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (_isPreview)
              TextButton(
                onPressed: () =>
                    setState(() => _step = _BriefingStep.retroactive),
                child: const Text('I played without registering'),
              ),
            TextButton(
              onPressed: () => setState(() => _step = _BriefingStep.correct),
              child: const Text("That's not right"),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Primary actions
        if (_isPreview) ...[
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => context.pop(),
                  child: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: () => _onStartMission(briefingText),
                  child: const Text("Got it, let's go"),
                ),
              ),
            ],
          ),
        ] else ...[
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => context.pop(),
              child: const Text('Got it'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildCorrectStep(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tell us where you actually are so we can adjust the briefing:',
          style: theme.textTheme.bodyMedium,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _correctionController,
          maxLines: 4,
          minLines: 2,
          decoration: const InputDecoration(
            hintText:
                "e.g. I'm actually in City of Tears now, working on "
                'the Soul Master fight',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => setState(() => _step = _BriefingStep.briefing),
              child: const Text('Back'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _onCorrect,
              child: const Text('Update & regenerate'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRetroactiveStep(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Tell us what happened in that unregistered session so we can '
          'update your briefing:',
          style: theme.textTheme.bodyMedium,
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _retroactiveController,
          maxLines: 6,
          minLines: 3,
          decoration: const InputDecoration(
            hintText:
                'e.g. I played for a couple hours, beat the Soul '
                'Master and explored the City of Tears. Got the Elegant Key.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            TextButton(
              onPressed: () => setState(() => _step = _BriefingStep.briefing),
              child: const Text('Back'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _onRetroactive,
              child: const Text('Record session'),
            ),
          ],
        ),
      ],
    );
  }
}
