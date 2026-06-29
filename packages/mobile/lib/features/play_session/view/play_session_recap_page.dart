import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Step enum that controls which section of the recap page is shown.
///
/// In preview mode the user first picks quick vs deep ([chooseMode]); the
/// recap is only fetched after that choice. [update] is a small menu that
/// merges the two "fix the recap" actions.
enum _RecapStep { chooseMode, recap, update, correct, retroactive }

/// Recap preview / view page.
///
/// **Preview mode** — receives [libraryEntryPublicId] (before starting a
/// session). Lets the user choose a recap mode, review it, correct it, log a
/// past session, or start the playSession.
///
/// **View mode** — receives [playSessionPublicId] (for an active session).
/// Shows the recap and allows corrections via regeneration.
class PlaySessionRecapPage extends StatefulWidget {
  const PlaySessionRecapPage({
    this.libraryEntryPublicId,
    this.playSessionPublicId,
    super.key,
  }) : assert(
         libraryEntryPublicId != null || playSessionPublicId != null,
         'Either libraryEntryPublicId or playSessionPublicId must be provided.',
       );

  /// Non-null in preview mode.
  final String? libraryEntryPublicId;

  /// Non-null in view mode.
  final String? playSessionPublicId;

  @override
  State<PlaySessionRecapPage> createState() => _PlaySessionRecapPageState();
}

class _PlaySessionRecapPageState extends State<PlaySessionRecapPage> {
  late _RecapStep _step;
  final _correctionController = TextEditingController();
  final _retroactiveController = TextEditingController();

  bool get _isPreview => widget.libraryEntryPublicId != null;

  @override
  void initState() {
    super.initState();
    if (_isPreview) {
      // Don't fetch anything yet — wait for the user to pick quick vs deep.
      _step = _RecapStep.chooseMode;
    } else {
      _step = _RecapStep.recap;
      context.read<PlaySessionBloc>().add(const LoadActivePlaySession());
    }
  }

  @override
  void dispose() {
    _correctionController.dispose();
    _retroactiveController.dispose();
    super.dispose();
  }

  void _onSelectMode(bool deep) {
    context.read<PlaySessionBloc>().add(
      PreviewRecap(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        mode: deep ? 'deep' : 'quick',
      ),
    );
    setState(() => _step = _RecapStep.recap);
  }

  void _onCancelDeep() {
    context.read<PlaySessionBloc>().add(
      CancelDeepRecap(libraryEntryPublicId: widget.libraryEntryPublicId!),
    );
  }

  void _onCorrect() {
    final text = _correctionController.text.trim();
    if (text.isEmpty) return;

    if (_isPreview) {
      context.read<PlaySessionBloc>().add(
        PreviewRecap(
          libraryEntryPublicId: widget.libraryEntryPublicId!,
          positionOverride: text,
        ),
      );
    } else {
      context.read<PlaySessionBloc>().add(
        RegenerateRecap(
          publicId: widget.playSessionPublicId!,
          currentPosition: text,
        ),
      );
    }
    _correctionController.clear();
    setState(() => _step = _RecapStep.recap);
  }

  void _onRetroactive() {
    final text = _retroactiveController.text.trim();
    if (text.isEmpty) return;

    context.read<PlaySessionBloc>().add(
      SubmitRetroactiveWrapUp(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        wrapUpText: text,
      ),
    );
    _retroactiveController.clear();
    setState(() => _step = _RecapStep.recap);
  }

  void _onStartPlaySession(String? recapText) {
    context.read<PlaySessionBloc>().add(
      StartPlaySession(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        recapText: recapText,
      ),
    );
  }

  void _onSkipRecap() {
    context.read<PlaySessionBloc>().add(
      StartPlaySession(
        libraryEntryPublicId: widget.libraryEntryPublicId!,
        skipRecap: true,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Recap')),
      body: SafeArea(
        child: BlocConsumer<PlaySessionBloc, PlaySessionState>(
          listener: (context, state) {
            if (state is PlaySessionStarted) {
              context.go('/play-sessions');
            }
            if (state is PlaySessionError) {
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
            // Preview mode, before a recap mode is chosen.
            if (_isPreview && state is PlaySessionInitial) {
              return _buildChooseMode(context);
            }

            if (state is PlaySessionLoading) {
              return const Center(child: CircularProgressIndicator());
            }

            // Deep recap in progress: show progress + cancel.
            if (state is DeepRecapLoading) {
              return _buildDeepLoading(context);
            }

            // Preview mode: recap preview loaded.
            if (state is RecapPreviewLoaded) {
              return _buildRecapContent(
                context,
                recapText: state.preview.recapText,
                gameTitle: state.preview.libraryEntry.game.title,
                platformLabel: state.preview.libraryEntry.platform.label,
              );
            }

            // View mode: active playSession loaded.
            if (state is ActivePlaySessionLoaded && state.playSession != null) {
              return _buildRecapContent(
                context,
                recapText: state.playSession!.recapText,
                gameTitle: state.playSession!.libraryEntry.game.title,
                platformLabel: state.playSession!.libraryEntry.platform.label,
              );
            }

            // View mode: playSession regenerated.
            if (state is PlaySessionStarted) {
              return _buildRecapContent(
                context,
                recapText: state.playSession.recapText,
                gameTitle: state.playSession.libraryEntry.game.title,
                platformLabel: state.playSession.libraryEntry.platform.label,
              );
            }

            if (state is PlaySessionError) {
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
            'How should we prepare your recap?',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          _modeCard(
            context,
            icon: Icons.bolt,
            title: 'Quick recap',
            subtitle:
                'Instant — built from your own past sessions. Recommended.',
            onTap: () => _onSelectMode(false),
          ),
          const SizedBox(height: 12),
          _modeCard(
            context,
            icon: Icons.travel_explore,
            title: 'Deep recap (web)',
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
            subtitle: 'Skip the recap and start your session right away.',
            onTap: _onSkipRecap,
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
              'Researching the web for your recap',
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

  // -- Recap content -----------------------------------------------------

  Widget _buildRecapContent(
    BuildContext context, {
    required String? recapText,
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

          // Step content (a loaded recap defaults to the recap step).
          if (_step == _RecapStep.update)
            _buildUpdateStep(context)
          else if (_step == _RecapStep.correct)
            _buildCorrectStep(context)
          else if (_step == _RecapStep.retroactive)
            _buildRetroactiveStep(context)
          else
            _buildRecapStep(context, recapText),
        ],
      ),
    );
  }

  Widget _buildRecapStep(BuildContext context, String? recapText) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (recapText != null && recapText.isNotEmpty)
          Text(recapText, style: theme.textTheme.bodyLarge)
        else
          Text(
            'No recap available -- this is your first session for this '
            'game. Enjoy the adventure!',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
        const SizedBox(height: 32),

        // Secondary action: one entry point for fixing the recap.
        Align(
          alignment: Alignment.centerLeft,
          child: _isPreview
              ? TextButton(
                  onPressed: () => setState(() => _step = _RecapStep.update),
                  child: const Text('Update this recap'),
                )
              : TextButton(
                  onPressed: () => setState(() => _step = _RecapStep.correct),
                  child: const Text("That's not right"),
                ),
        ),
        const SizedBox(height: 16),

        // Primary action
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _isPreview
                ? () => _onStartPlaySession(recapText)
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
            onPressed: () => setState(() => _step = _RecapStep.correct),
            child: const Text('Correct my current position'),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () => setState(() => _step = _RecapStep.retroactive),
            child: const Text("Log a session I didn't register"),
          ),
        ),
        const SizedBox(height: 16),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton(
            onPressed: () => setState(() => _step = _RecapStep.recap),
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
          'Tell us where you actually are so we can adjust the recap:',
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
                () => _step = _isPreview ? _RecapStep.update : _RecapStep.recap,
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
          'update your recap:',
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
              onPressed: () => setState(() => _step = _RecapStep.update),
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
