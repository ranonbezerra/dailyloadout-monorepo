import 'dart:io';

import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

/// Page for capturing a photo of a game cover or shelf.
///
/// The user can take a photo with the camera or choose one from
/// the gallery. After selection, a preview is shown with options
/// to re-select or submit for vision-based game extraction.
class CapturePhotoPage extends StatefulWidget {
  const CapturePhotoPage({super.key});

  @override
  State<CapturePhotoPage> createState() => _CapturePhotoPageState();
}

class _CapturePhotoPageState extends State<CapturePhotoPage> {
  final _picker = ImagePicker();
  String? _imagePath;

  Future<void> _pickFromCamera() async {
    final image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
    );
    if (image != null) {
      setState(() => _imagePath = image.path);
    }
  }

  Future<void> _pickFromGallery() async {
    final image = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
    );
    if (image != null) {
      setState(() => _imagePath = image.path);
    }
  }

  void _clearImage() {
    setState(() => _imagePath = null);
  }

  void _onSubmit() {
    if (_imagePath == null) return;

    context.read<CaptureBloc>().add(SubmitPhotoCapture(imagePath: _imagePath!));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Photo Capture')),
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
                'Snap your games',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Take a photo of a game cover, case, or '
                'your shelf. We will identify the games '
                'for you.',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 32),
              if (_imagePath == null)
                _buildPickerSection(theme, colors)
              else
                _buildPreviewSection(theme, colors),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPickerSection(ThemeData theme, ColorScheme colors) {
    return Column(
      children: [
        // Camera button.
        SizedBox(
          width: double.infinity,
          height: 48,
          child: FilledButton.icon(
            onPressed: _pickFromCamera,
            icon: const Icon(Icons.camera_alt),
            label: const Text('Take Photo'),
          ),
        ),
        const SizedBox(height: 12),
        // Gallery button.
        SizedBox(
          width: double.infinity,
          height: 48,
          child: OutlinedButton.icon(
            onPressed: _pickFromGallery,
            icon: const Icon(Icons.photo_library),
            label: const Text('Choose from Gallery'),
          ),
        ),
        const SizedBox(height: 32),
        // Hint section.
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: colors.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.lightbulb_outline,
                    size: 18,
                    color: colors.onSurfaceVariant,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Tips for best results',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Make sure game titles are clearly '
                'visible and well-lit. Avoid blurry or '
                'angled shots for more accurate '
                'detection.',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colors.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPreviewSection(ThemeData theme, ColorScheme colors) {
    return Column(
      children: [
        // Image preview.
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Image.file(
            File(_imagePath!),
            width: double.infinity,
            height: 300,
            fit: BoxFit.cover,
          ),
        ),
        const SizedBox(height: 24),
        // Action buttons.
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _clearImage,
                icon: const Icon(Icons.refresh),
                label: const Text('Use Different Photo'),
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
    );
  }
}
