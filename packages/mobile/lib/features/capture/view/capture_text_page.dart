import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

/// Page for entering free text that describes the user's games.
class CaptureTextPage extends StatefulWidget {
  const CaptureTextPage({super.key});

  @override
  State<CaptureTextPage> createState() => _CaptureTextPageState();
}

class _CaptureTextPageState extends State<CaptureTextPage> {
  final _formKey = GlobalKey<FormState>();
  final _textController = TextEditingController();

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  void _onSubmit() {
    if (!_formKey.currentState!.validate()) return;

    context.read<CaptureBloc>().add(
      SubmitTextCapture(rawText: _textController.text.trim()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Text Capture')),
      body: BlocListener<CaptureBloc, CaptureState>(
        listener: (context, state) {
          if (state is CaptureSubmitted) {
            context.go('/capture/review/${state.capture.publicId}');
          }

          if (state is CaptureError) {
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
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Tell us about your games',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'Describe the games you own, recently bought, or '
                  'want to track. We will extract the titles and match '
                  'them for you.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 24),
                TextFormField(
                  controller: _textController,
                  maxLines: 8,
                  minLines: 5,
                  maxLength: 2000,
                  decoration: const InputDecoration(
                    hintText:
                        'E.g., "I just bought Hollow Knight and Hades '
                        'for the Switch, and I have God of War on PS5"',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter some text about your games';
                    }
                    if (value.trim().length < 3) {
                      return 'Please enter at least 3 characters';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 24),
                BlocBuilder<CaptureBloc, CaptureState>(
                  builder: (context, state) {
                    final isSubmitting = state is CaptureSubmitting;
                    return SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: FilledButton(
                        onPressed: isSubmitting ? null : _onSubmit,
                        child: isSubmitting
                            ? const Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  SizedBox(
                                    height: 20,
                                    width: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  ),
                                  SizedBox(width: 12),
                                  Text('Processing...'),
                                ],
                              )
                            : const Text('Submit'),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
