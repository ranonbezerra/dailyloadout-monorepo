import 'package:app/features/play_session/bloc/play_session_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// WrapUp page shown when ending a playSession.
///
/// Receives [playSessionPublicId] as a route parameter.
class PlaySessionWrapUpPage extends StatefulWidget {
  const PlaySessionWrapUpPage({required this.playSessionPublicId, super.key});

  final String playSessionPublicId;

  @override
  State<PlaySessionWrapUpPage> createState() => _PlaySessionWrapUpPageState();
}

class _PlaySessionWrapUpPageState extends State<PlaySessionWrapUpPage> {
  final _wrapUpController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    // Load the active playSession to display the game title.
    context.read<PlaySessionBloc>().add(const LoadActivePlaySession());
  }

  @override
  void dispose() {
    _wrapUpController.dispose();
    super.dispose();
  }

  void _onSubmitWrapUp() {
    if (!_formKey.currentState!.validate()) return;

    context.read<PlaySessionBloc>().add(
      SubmitWrapUp(
        publicId: widget.playSessionPublicId,
        wrapUpText: _wrapUpController.text.trim(),
      ),
    );
  }

  void _onSkipWrapUp() {
    context.read<PlaySessionBloc>().add(
      EndPlaySession(publicId: widget.playSessionPublicId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Wrap up')),
      body: BlocConsumer<PlaySessionBloc, PlaySessionState>(
        listener: (context, state) {
          if (state is PlaySessionEnded) {
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
          // Show loading indicator while the active session is being fetched.
          if (state is PlaySessionLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          // Determine the game title from the active playSession state.
          String? gameTitle;
          if (state is ActivePlaySessionLoaded && state.playSession != null) {
            gameTitle = state.playSession!.libraryEntry.game.title;
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (gameTitle != null) ...[
                    Text(
                      gameTitle,
                      style: theme.textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  Text(
                    'What happened this session?',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Describe what you did, where you are, or anything '
                    'notable from this play session.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // WrapUp text field
                  TextFormField(
                    controller: _wrapUpController,
                    maxLines: 4,
                    minLines: 3,
                    decoration: const InputDecoration(
                      hintText:
                          'e.g. Beat the first boss, explored the '
                          'forest area, found a hidden cave...',
                      border: OutlineInputBorder(),
                      alignLabelWithHint: true,
                    ),
                    validator: (value) {
                      if (value == null || value.trim().length < 3) {
                        return 'Please enter at least 3 characters';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 24),

                  // Submit button
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: FilledButton(
                      onPressed: _onSubmitWrapUp,
                      child: const Text('Save wrap-up'),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Skip button
                  SizedBox(
                    width: double.infinity,
                    child: TextButton(
                      onPressed: _onSkipWrapUp,
                      child: const Text('Skip wrap-up'),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
