import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/capture/view/capture_photo_page.dart';
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
        child: const CapturePhotoPage(),
      ),
    );
  }

  group('CapturePhotoPage', () {
    testWidgets('renders AppBar with "Photo Capture" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Photo Capture'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows "Snap your games" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Snap your games'), findsOneWidget);
    });

    testWidgets('shows description text', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(
        find.text(
          'Take a photo of a game cover, case, or '
          'your shelf. We will identify the games '
          'for you.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows "Take Photo" FilledButton with camera icon', (
      tester,
    ) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      // FilledButton.icon renders as a ButtonStyleButton subtype.
      // Verify via text and icon presence.
      expect(find.text('Take Photo'), findsOneWidget);
      expect(find.byIcon(Icons.camera_alt), findsOneWidget);

      // Verify it is inside a FilledButton
      final buttonFinder = find.ancestor(
        of: find.text('Take Photo'),
        matching: find.bySubtype<FilledButton>(),
      );
      expect(buttonFinder, findsOneWidget);
    });

    testWidgets('shows "Choose from Gallery" OutlinedButton with icon', (
      tester,
    ) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Choose from Gallery'), findsOneWidget);
      expect(find.byIcon(Icons.photo_library), findsOneWidget);

      final buttonFinder = find.ancestor(
        of: find.text('Choose from Gallery'),
        matching: find.bySubtype<OutlinedButton>(),
      );
      expect(buttonFinder, findsOneWidget);
    });

    testWidgets('shows camera_alt icon on Take Photo button', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byIcon(Icons.camera_alt), findsOneWidget);
    });

    testWidgets('shows photo_library icon on Gallery button', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.byIcon(Icons.photo_library), findsOneWidget);
    });

    group('tips section', () {
      testWidgets('shows "Tips for best results" heading', (tester) async {
        when(() => mockBloc.state).thenReturn(const CaptureInitial());

        await tester.pumpWidget(buildSubject());

        expect(find.text('Tips for best results'), findsOneWidget);
      });

      testWidgets('shows lightbulb icon', (tester) async {
        when(() => mockBloc.state).thenReturn(const CaptureInitial());

        await tester.pumpWidget(buildSubject());

        expect(find.byIcon(Icons.lightbulb_outline), findsOneWidget);
      });

      testWidgets('shows tips description text', (tester) async {
        when(() => mockBloc.state).thenReturn(const CaptureInitial());

        await tester.pumpWidget(buildSubject());

        expect(
          find.text(
            'Make sure game titles are clearly '
            'visible and well-lit. Avoid blurry or '
            'angled shots for more accurate '
            'detection.',
          ),
          findsOneWidget,
        );
      });
    });

    testWidgets('shows SnackBar on CaptureError', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());
      whenListen(
        mockBloc,
        Stream.fromIterable([
          const CaptureError(message: 'Photo processing failed'),
        ]),
        initialState: const CaptureInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Photo processing failed'), findsOneWidget);
      expect(find.byType(SnackBar), findsOneWidget);
    });

    testWidgets('in picker section both action buttons are rendered', (
      tester,
    ) async {
      // The "Processing..." indicator only appears in the preview section
      // (after an image is selected via ImagePicker, which cannot be mocked
      // here since it is created inside State). We verify the picker section
      // renders correctly in the initial state instead.
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());

      expect(find.text('Take Photo'), findsOneWidget);
      expect(find.text('Choose from Gallery'), findsOneWidget);
    });
  });
}
