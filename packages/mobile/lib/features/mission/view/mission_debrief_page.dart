import 'package:app/features/mission/bloc/mission_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Debrief page shown when ending a mission.
///
/// Receives [missionPublicId] as a route parameter.
class MissionDebriefPage extends StatefulWidget {
  const MissionDebriefPage({required this.missionPublicId, super.key});

  final String missionPublicId;

  @override
  State<MissionDebriefPage> createState() => _MissionDebriefPageState();
}

class _MissionDebriefPageState extends State<MissionDebriefPage> {
  final _debriefController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    // Load the active mission to display the game title.
    context.read<MissionBloc>().add(const LoadActiveMission());
  }

  @override
  void dispose() {
    _debriefController.dispose();
    super.dispose();
  }

  void _onSubmitDebrief() {
    if (!_formKey.currentState!.validate()) return;

    context.read<MissionBloc>().add(
      SubmitDebrief(
        publicId: widget.missionPublicId,
        debriefText: _debriefController.text.trim(),
      ),
    );
  }

  void _onSkipDebrief() {
    context.read<MissionBloc>().add(
      EndMission(publicId: widget.missionPublicId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Mission Debrief')),
      body: BlocConsumer<MissionBloc, MissionState>(
        listener: (context, state) {
          if (state is MissionEnded) {
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
          // Show loading indicator while the active mission is being fetched.
          if (state is MissionLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          // Determine the game title from the active mission state.
          String? gameTitle;
          if (state is ActiveMissionLoaded && state.mission != null) {
            gameTitle = state.mission!.libraryEntry.game.title;
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

                  // Debrief text field
                  TextFormField(
                    controller: _debriefController,
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
                      onPressed: _onSubmitDebrief,
                      child: const Text('Submit debrief'),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Skip button
                  SizedBox(
                    width: double.infinity,
                    child: TextButton(
                      onPressed: _onSkipDebrief,
                      child: const Text('Skip debrief'),
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
