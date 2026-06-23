import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/capture/view/capture_voice_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockCaptureBloc extends MockBloc<CaptureEvent, CaptureState>
    implements CaptureBloc {}

void main() {
  late MockCaptureBloc mockBloc;

  setUp(() {
    mockBloc = MockCaptureBloc();
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<CaptureBloc>.value(
        value: mockBloc,
        child: const CaptureVoicePage(),
      ),
    );
  }

  group('CaptureVoicePage', () {
    testWidgets('renders AppBar with "Voice Capture" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Voice Capture'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows "Speak about your games" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Speak about your games'), findsOneWidget);
    });

    testWidgets('shows timer display "00:00" initially', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('00:00'), findsOneWidget);
    });

    testWidgets('shows "Tap the mic to start" initial text', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Tap the mic to start'), findsOneWidget);
    });

    testWidgets('shows mic GestureDetector button', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(GestureDetector), findsWidgets);
      // The mic icon is present inside the circular button.
      expect(find.byIcon(Icons.mic), findsOneWidget);
    });

    testWidgets('shows "Tap to record" label', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Tap to record'), findsOneWidget);
    });

    testWidgets(
      'when CaptureTranscribing state shows CircularProgressIndicator '
      'and "Transcribing your audio..."',
      (tester) async {
        when(() => mockBloc.state).thenReturn(const CaptureTranscribing());
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: const CaptureTranscribing(),
        );

        await tester.pumpWidget(buildSubject());

        expect(find.byType(CircularProgressIndicator), findsOneWidget);
        expect(find.text('Transcribing your audio...'), findsOneWidget);
      },
    );

    testWidgets('when transcription is ready (CaptureTranscribed) the form '
        'appears with Submit and Record Again buttons', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());
      whenListen(
        mockBloc,
        Stream.fromIterable([
          const CaptureTranscribed(text: 'I have Hollow Knight'),
        ]),
        initialState: const CaptureInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // The transcription review section should appear.
      expect(find.text('Transcription ready'), findsOneWidget);
      expect(
        find.text(
          'Review and edit the text below, then submit '
          'to extract your games.',
        ),
        findsOneWidget,
      );

      // The transcribed text should be populated in a TextFormField.
      expect(find.byType(TextFormField), findsOneWidget);

      // The Submit button (plain FilledButton, not .icon variant).
      expect(find.widgetWithText(FilledButton, 'Submit'), findsOneWidget);
      // The Record Again button uses OutlinedButton.icon factory, so use
      // find.bySubtype to match the internal _OutlinedButtonWithIcon type.
      expect(find.text('Record Again'), findsOneWidget);
      final recordAgainButton = find.ancestor(
        of: find.text('Record Again'),
        matching: find.bySubtype<OutlinedButton>(),
      );
      expect(recordAgainButton, findsOneWidget);
    });

    testWidgets('shows SnackBar on CaptureError', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());
      whenListen(
        mockBloc,
        Stream.fromIterable([
          const CaptureError(message: 'Transcription failed'),
        ]),
        initialState: const CaptureInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Transcription failed'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('shows description text below title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.text(
          'Record yourself describing the games you own or '
          "recently bought. We'll transcribe it and let you "
          'review before processing.',
        ),
        findsOneWidget,
      );
    });
  });
}
