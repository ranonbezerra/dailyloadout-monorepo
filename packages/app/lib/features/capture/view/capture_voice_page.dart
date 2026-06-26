import 'dart:async';

import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:record/record.dart';

/// Page for recording audio, reviewing the transcription, and submitting.
///
/// Flow: Record → Transcribe → Show editable text → Submit as voice capture.
class CaptureVoicePage extends StatefulWidget {
  const CaptureVoicePage({super.key});

  @override
  State<CaptureVoicePage> createState() => _CaptureVoicePageState();
}

class _CaptureVoicePageState extends State<CaptureVoicePage> {
  final _recorder = AudioRecorder();
  final _textController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  bool _isRecording = false;
  int _secondsElapsed = 0;
  Timer? _timer;
  String? _audioPath;
  bool _hasTranscription = false;

  static const _maxDurationSeconds = 60;

  @override
  void dispose() {
    _timer?.cancel();
    _recorder.dispose();
    _textController.dispose();
    super.dispose();
  }

  Future<void> _startRecording() async {
    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      if (mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            const SnackBar(content: Text('Microphone permission is required.')),
          );
      }
      return;
    }

    await _recorder.start(
      const RecordConfig(encoder: AudioEncoder.wav),
      path: '',
    );

    setState(() {
      _isRecording = true;
      _secondsElapsed = 0;
      _hasTranscription = false;
      _audioPath = null;
      _textController.clear();
    });

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() => _secondsElapsed++);
      if (_secondsElapsed >= _maxDurationSeconds) {
        _stopRecording();
      }
    });
  }

  Future<void> _stopRecording() async {
    _timer?.cancel();
    _timer = null;

    final path = await _recorder.stop();
    if (path == null) return;

    setState(() {
      _isRecording = false;
      _audioPath = path;
    });

    // Send for transcription.
    if (mounted) {
      context.read<CaptureBloc>().add(TranscribeAudio(filePath: path));
    }
  }

  void _onSubmit() {
    if (!_formKey.currentState!.validate()) return;

    context.read<CaptureBloc>().add(
      SubmitVoiceCapture(rawText: _textController.text.trim()),
    );
  }

  void _onRecordAgain() {
    setState(() {
      _hasTranscription = false;
      _audioPath = null;
      _textController.clear();
    });
  }

  String _formatDuration(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Voice Capture')),
      body: BlocListener<CaptureBloc, CaptureState>(
        listener: (context, state) {
          if (state is CaptureTranscribed) {
            setState(() {
              _hasTranscription = true;
              _textController.text = state.text;
            });
          }

          if (state is CaptureSubmitted) {
            context.go('/capture/review/${state.capture.publicId}');
          }

          if (state is CaptureError) {
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                SnackBar(
                  content: Text(state.message),
                  backgroundColor: colors.error,
                ),
              );
          }
        },
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Speak about your games',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Record yourself describing the games you own or '
                "recently bought. We'll transcribe it and let you "
                'review before processing.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 32),

              // Recording section (hidden after transcription).
              if (!_hasTranscription) ...[
                _buildRecordingSection(theme, colors),
                const SizedBox(height: 24),
                // Transcribing indicator.
                BlocBuilder<CaptureBloc, CaptureState>(
                  builder: (context, state) {
                    if (state is CaptureTranscribing) {
                      return const Column(
                        children: [
                          SizedBox(height: 16),
                          Center(child: CircularProgressIndicator()),
                          SizedBox(height: 12),
                          Center(child: Text('Transcribing your audio...')),
                        ],
                      );
                    }
                    return const SizedBox.shrink();
                  },
                ),
              ],

              // Transcription review section.
              if (_hasTranscription) ...[
                _buildTranscriptionReview(theme, colors),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRecordingSection(ThemeData theme, ColorScheme colors) {
    return Center(
      child: Column(
        children: [
          // Timer display.
          Text(
            _formatDuration(_secondsElapsed),
            style: theme.textTheme.displaySmall?.copyWith(
              fontFeatures: [const FontFeature.tabularFigures()],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _isRecording
                ? 'Recording... (max ${_maxDurationSeconds}s)'
                : _audioPath != null
                ? 'Recording complete'
                : 'Tap the mic to start',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 24),
          // Mic button.
          Semantics(
            button: true,
            label: _isRecording ? 'Stop recording' : 'Start recording',
            child: GestureDetector(
              onTap: _isRecording ? _stopRecording : _startRecording,
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _isRecording ? colors.error : colors.primary,
                ),
                child: Icon(
                  _isRecording ? Icons.stop : Icons.mic,
                  color: _isRecording ? colors.onError : colors.onPrimary,
                  size: 40,
                ),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            _isRecording ? 'Tap to stop' : 'Tap to record',
            style: theme.textTheme.labelMedium?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          // Progress bar.
          if (_isRecording) ...[
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48),
              child: LinearProgressIndicator(
                value: _secondsElapsed / _maxDurationSeconds,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTranscriptionReview(ThemeData theme, ColorScheme colors) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.check_circle, color: colors.primary, size: 20),
              const SizedBox(width: 8),
              Text(
                'Transcription ready',
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Review and edit the text below, then submit '
            'to extract your games.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colors.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 16),
          TextFormField(
            controller: _textController,
            maxLines: 8,
            minLines: 4,
            maxLength: 2000,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              hintText: 'Edit the transcribed text if needed...',
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
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _onRecordAgain,
                  icon: const Icon(Icons.mic),
                  label: const Text('Record Again'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: BlocBuilder<CaptureBloc, CaptureState>(
                  builder: (context, state) {
                    final isSubmitting = state is CaptureSubmitting;
                    return FilledButton(
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
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
