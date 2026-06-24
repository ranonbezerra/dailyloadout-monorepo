import 'package:app/core/capture/capture_models.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

final _now = DateTime.utc(2025, 6);

final _capture = Capture(
  publicId: 'cap-001',
  inputType: 'text',
  rawText: 'I just finished Elden Ring',
  status: 'review',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-001',
      title: 'Elden Ring',
      status: 'pending',
    ),
  ],
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  group('CaptureEvent', () {
    test('LoadCaptures supports value equality and props', () {
      const a = LoadCaptures(status: 'review');
      const b = LoadCaptures(status: 'review');
      expect(a, b);
      expect(a.props, ['review']);
      expect(const LoadCaptures().props, [null]);
    });

    test('SubmitTextCapture supports value equality and props', () {
      const a = SubmitTextCapture(rawText: 'hello');
      const b = SubmitTextCapture(rawText: 'hello');
      expect(a, b);
      expect(a.props, ['hello']);
      expect(a, isNot(const SubmitTextCapture(rawText: 'bye')));
    });

    test('SubmitVoiceCapture supports value equality and props', () {
      const a = SubmitVoiceCapture(rawText: 'hello');
      const b = SubmitVoiceCapture(rawText: 'hello');
      expect(a, b);
      expect(a.props, ['hello']);
    });

    test('TranscribeAudio supports value equality and props', () {
      const a = TranscribeAudio(filePath: '/tmp/a.m4a');
      const b = TranscribeAudio(filePath: '/tmp/a.m4a');
      expect(a, b);
      expect(a.props, ['/tmp/a.m4a']);
    });

    test('SubmitPhotoCapture supports value equality and props', () {
      const a = SubmitPhotoCapture(imagePath: '/tmp/a.jpg');
      const b = SubmitPhotoCapture(imagePath: '/tmp/a.jpg');
      expect(a, b);
      expect(a.props, ['/tmp/a.jpg']);
    });

    test('ConfirmCandidate supports value equality and props', () {
      const a = ConfirmCandidate(
        captureId: 'cap-1',
        candidateId: 'cand-1',
        platformId: 1,
        status: 'playing',
      );
      const b = ConfirmCandidate(
        captureId: 'cap-1',
        candidateId: 'cand-1',
        platformId: 1,
        status: 'playing',
      );
      expect(a, b);
      expect(a.props, ['cap-1', 'cand-1', 1, 'playing']);
    });

    test('ConfirmCandidate uses default status', () {
      const a = ConfirmCandidate(
        captureId: 'cap-1',
        candidateId: 'cand-1',
        platformId: 1,
      );
      expect(a.status, 'backlog');
      expect(a.props, ['cap-1', 'cand-1', 1, 'backlog']);
    });

    test('RejectCandidate supports value equality and props', () {
      const a = RejectCandidate(captureId: 'cap-1', candidateId: 'cand-1');
      const b = RejectCandidate(captureId: 'cap-1', candidateId: 'cand-1');
      expect(a, b);
      expect(a.props, ['cap-1', 'cand-1']);
    });
  });

  group('CaptureState', () {
    test('CaptureInitial supports value equality', () {
      expect(const CaptureInitial(), const CaptureInitial());
      expect(const CaptureInitial().props, isEmpty);
    });

    test('CaptureLoading supports value equality', () {
      expect(const CaptureLoading(), const CaptureLoading());
      expect(const CaptureLoading().props, isEmpty);
    });

    test('CaptureLoaded supports value equality and props', () {
      final a = CaptureLoaded(captures: [_capture], total: 1);
      final b = CaptureLoaded(captures: [_capture], total: 1);
      expect(a, b);
      expect(a.props, [
        [_capture],
        1,
      ]);
    });

    test('CaptureSubmitting supports value equality', () {
      expect(const CaptureSubmitting(), const CaptureSubmitting());
      expect(const CaptureSubmitting().props, isEmpty);
    });

    test('CaptureSubmitted supports value equality and props', () {
      final a = CaptureSubmitted(capture: _capture);
      final b = CaptureSubmitted(capture: _capture);
      expect(a, b);
      expect(a.props, [_capture]);
    });

    test('CaptureTranscribing supports value equality', () {
      expect(const CaptureTranscribing(), const CaptureTranscribing());
      expect(const CaptureTranscribing().props, isEmpty);
    });

    test('CaptureTranscribed supports value equality and props', () {
      const a = CaptureTranscribed(text: 'hi');
      const b = CaptureTranscribed(text: 'hi');
      expect(a, b);
      expect(a.props, ['hi']);
      expect(a, isNot(const CaptureTranscribed(text: 'bye')));
    });

    test('CaptureError supports value equality and props', () {
      const a = CaptureError(message: 'boom');
      const b = CaptureError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
    });
  });
}
