import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/capture/view/capture_text_page.dart';
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
        child: const CaptureTextPage(),
      ),
    );
  }

  group('CaptureTextPage', () {
    testWidgets('renders AppBar with "Text Capture" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Text Capture'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows "Tell us about your games" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Tell us about your games'), findsOneWidget);
    });

    testWidgets('shows description text', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.text(
          'Describe the games you own, recently bought, or '
          'want to track. We will extract the titles and match '
          'them for you.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows TextFormField with hint about Hollow Knight/Hades', (
      tester,
    ) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(TextFormField), findsOneWidget);
      expect(
        find.text(
          'E.g., "I just bought Hollow Knight and Hades '
          'for the Switch, and I have God of War on PS5"',
        ),
        findsOneWidget,
      );
    });

    testWidgets('TextFormField has maxLength 2000', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      // The maxLength is set on the TextField inside TextFormField.
      final textFieldWidget = tester.widget<TextField>(find.byType(TextField));
      expect(textFieldWidget.maxLength, equals(2000));
    });

    testWidgets('shows Submit FilledButton', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(FilledButton, 'Submit'), findsOneWidget);
    });

    group('validation', () {
      testWidgets(
        'empty text shows "Please enter some text about your games"',
        (tester) async {
          when(() => mockBloc.state).thenReturn(const CaptureInitial());

          await tester.pumpWidget(buildSubject());

          // Tap submit without entering text.
          await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
          await tester.pumpAndSettle();

          expect(
            find.text('Please enter some text about your games'),
            findsOneWidget,
          );
        },
      );

      testWidgets(
        'less than 3 chars shows "Please enter at least 3 characters"',
        (tester) async {
          when(() => mockBloc.state).thenReturn(const CaptureInitial());

          await tester.pumpWidget(buildSubject());

          // Enter 2 characters (after trim).
          await tester.enterText(find.byType(TextFormField), 'ab');
          await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
          await tester.pumpAndSettle();

          expect(
            find.text('Please enter at least 3 characters'),
            findsOneWidget,
          );
        },
      );

      testWidgets('whitespace-only text shows '
          '"Please enter some text about your games"', (tester) async {
        when(() => mockBloc.state).thenReturn(const CaptureInitial());

        await tester.pumpWidget(buildSubject());

        await tester.enterText(find.byType(TextFormField), '   ');
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(
          find.text('Please enter some text about your games'),
          findsOneWidget,
        );
      });
    });

    testWidgets('submit dispatches SubmitTextCapture event with trimmed text', (
      tester,
    ) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      const inputText = '  Hollow Knight and Hades  ';
      await tester.enterText(find.byType(TextFormField), inputText);
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      verify(
        () => mockBloc.add(
          const SubmitTextCapture(rawText: 'Hollow Knight and Hades'),
        ),
      ).called(1);
    });

    testWidgets('shows "Processing..." and CircularProgressIndicator '
        'when CaptureSubmitting', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureSubmitting());
      whenListen(
        mockBloc,
        const Stream<CaptureState>.empty(),
        initialState: const CaptureSubmitting(),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Processing...'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('submit button is disabled when CaptureSubmitting', (
      tester,
    ) async {
      when(() => mockBloc.state).thenReturn(const CaptureSubmitting());
      whenListen(
        mockBloc,
        const Stream<CaptureState>.empty(),
        initialState: const CaptureSubmitting(),
      );

      await tester.pumpWidget(buildSubject());

      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      expect(button.onPressed, isNull);
    });

    testWidgets('shows SnackBar on CaptureError state', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());
      whenListen(
        mockBloc,
        Stream.fromIterable([
          const CaptureError(message: 'Something went wrong'),
        ]),
        initialState: const CaptureInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });
  });
}
