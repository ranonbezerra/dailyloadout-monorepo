import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Step enum that controls which section of the briefing page is shown.
///
/// In preview mode the user first picks quick vs deep ([chooseMode]); the
/// briefing is only fetched after that choice. [update] is a small menu that
/// merges the two "fix the briefing" actions.
enum _BriefingStep { chooseMode, briefing, update, correct, retroactive }

/// Briefing preview / view page.
///
/// **Preview mode** — receives [libraryEntryPublicId] (before starting a
/// mission). Lets the user choose a briefing mode, review it, correct it, log a
/// past session, or start the mission.
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
  late _BriefingStep _step;
  final _correctionController = TextEditingController();
  final _retroactiveController = TextEditingController();

  bool get _isPreview => widget.libraryEntryPublicId != null;

  @override
  void initState() {
    super.initState();
    if (_isPreview) {
      // Don't fetch anything yet — wait for the user to pick quick vs deep.
      _step = _BriefingStep.chooseMode;
    } else {
      _step = _BriefingStep.briefing;
      context.read<MissionBloc>().add(const LoadActiveMission());
    }
  }

  @override
  void dispose() {
    _correctionController.dispose();
    _retroactiveController.dispose();
    super.dispose();
  }

  void _onSelectMode(bool deep) {
    context.read<MissionBloc>().add(
      PreviewBriefing(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        mode: deep ? 'deep' : 'quick',
      ),
    );
    setState(() => _step = _BriefingStep.briefing);
  }

  void _onCancelDeep() {
    context.read<MissionBloc>().add(
      CancelDeepBriefing(libraryEntryPublicId: widget.libraryEntryPublicId!),
    );
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

  void _onSkipBriefing() {
    context.read<MissionBloc>().add(
      StartMission(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        skipBriefing: true,
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
            // Preview mode, before a briefing mode is chosen.
            if (_isPreview && state is MissionInitial) {
              return _buildChooseMode(context);
            }

            if (state is MissionLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            // Deep briefing in progress: show progress + cancel.
            if (state is DeepBriefingLoading) {
              return _buildDeepLoading(context);
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

  // -- Mode choice ----------------------------------------------------------

  Widget _buildChooseMode(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'How should we prepare your briefing?',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          _modeCard(
            context,
            icon: Icons.bolt,
            title: 'Quick briefing',
            subtitle:
                'Instant — built from your own past sessions. Recommended.',
            onTap: () => _onSelectMode(false),
          ),
          const SizedBox(height: 12),
          _modeCard(
            context,
            icon: Icons.travel_explore,
            title: 'Deep briefing (web)',
            subtitle:
                'Searches the web for spoiler-free next steps. Takes up to a '
                'minute.',
            onTap: () => _onSelectMode(true),
          ),
          const SizedBox(height: 12),
          _modeCard(
            context,
            icon: Icons.play_arrow,
            title: 'Just play',
            subtitle: 'Skip the briefing and start the mission right away.',
            onTap: _onSkipBriefing,
          ),
        ],
      ),
    );
  }

  Widget _modeCard(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(icon, size: 28, color: theme.colorScheme.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDeepLoading(BuildContext context) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 24),
            Text(
              'Researching the web for your briefing',
              style: theme.textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Searching for spoiler-free next steps. This can take up to a '
              'minute.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            OutlinedButton(
              onPressed: _onCancelDeep,
              child: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }

  // -- Briefing content -----------------------------------------------------

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

          // Step content (a loaded briefing defaults to the briefing step).
          if (_step == _BriefingStep.update)
            _buildUpdateStep(context)
          else if (_step == _BriefingStep.correct)
            _buildCorrectStep(context)
          else if (_step == _BriefingStep.retroactive)
            _buildRetroactiveStep(context)
          else
            _buildBriefingStep(context, briefingText),
        ],
      ),
    );
  }

  Widget _buildBriefingStep(BuildContext context, String? briefingText) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
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

        // Secondary action: one entry point for fixing the briefing.
        Align(
          alignment: Alignment.centerLeft,
          child: _isPreview
              ? TextButton(
                  onPressed: () => setState(() => _step = _BriefingStep.update),
                  child: const Text('Update this briefing'),
                )
              : TextButton(
                  onPressed: () =>
                      setState(() => _step = _BriefingStep.correct),
                  child: const Text("That's not right"),
                ),
        ),
        const SizedBox(height: 16),

        // Primary action
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _isPreview
                ? () => _onStartMission(briefingText)
                : () => context.pop(),
            child: Text(_isPreview ? "Got it, let's go" : 'Got it'),
          ),
        ),
      ],
    );
  }

  Widget _buildUpdateStep(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('What would you like to fix?', style: theme.textTheme.bodyMedium),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => setState(() => _step = _BriefingStep.correct),
            child: const Text('Correct my current position'),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => setState(() => _step = _BriefingStep.retroactive),
            child: const Text("Log a session I didn't register"),
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => setState(() => _step = _BriefingStep.briefing),
            child: const Text('Back'),
          ),
        ),
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
              onPressed: () => setState(
                () => _step = _isPreview
                    ? _BriefingStep.update
                    : _BriefingStep.briefing,
              ),
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
              onPressed: () => setState(() => _step = _BriefingStep.update),
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
