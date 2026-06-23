import 'package:app/features/capture/view/capture_choice_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Widget buildSubject() {
    return const MaterialApp(home: CaptureChoicePage());
  }

  group('CaptureChoicePage', () {
    testWidgets('renders AppBar with "Quick Add" title', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Quick Add'),
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows "How do you want to add games?" heading', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      expect(find.text('How do you want to add games?'), findsOneWidget);
    });

    testWidgets('shows subtitle text about telling us', (tester) async {
      await tester.pumpWidget(buildSubject());

      expect(
        find.text(
          'Tell us about your games in your own words and '
          "we'll find them for you.",
        ),
        findsOneWidget,
      );
    });

    testWidgets('shows 3 capture option cards', (tester) async {
      await tester.pumpWidget(buildSubject());

      // Each card is wrapped in a Card widget.
      expect(find.byType(Card), findsNWidgets(3));
    });

    group('Text option card', () {
      testWidgets('shows text_fields icon', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.byIcon(Icons.text_fields), findsOneWidget);
      });

      testWidgets('shows "Text" title', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.text('Text'), findsOneWidget);
      });

      testWidgets(
        'shows "Type or paste a description of your games" subtitle',
        (tester) async {
          await tester.pumpWidget(buildSubject());

          expect(
            find.text('Type or paste a description of your games'),
            findsOneWidget,
          );
        },
      );

      testWidgets('shows chevron_right icon', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.byIcon(Icons.chevron_right), findsNWidgets(3));
      });
    });

    group('Voice option card', () {
      testWidgets('shows mic_outlined icon', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.byIcon(Icons.mic_outlined), findsOneWidget);
      });

      testWidgets('shows "Voice" title', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.text('Voice'), findsOneWidget);
      });

      testWidgets('shows "Speak about your games" subtitle', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.text('Speak about your games'), findsOneWidget);
      });
    });

    group('Photo option card', () {
      testWidgets('shows camera_alt_outlined icon', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.byIcon(Icons.camera_alt_outlined), findsOneWidget);
      });

      testWidgets('shows "Photo" title', (tester) async {
        await tester.pumpWidget(buildSubject());

        expect(find.text('Photo'), findsOneWidget);
      });

      testWidgets('shows "Take a photo of your game shelf" subtitle', (
        tester,
      ) async {
        await tester.pumpWidget(buildSubject());

        expect(find.text('Take a photo of your game shelf'), findsOneWidget);
      });
    });

    testWidgets('all 3 options show as enabled (no "Soon" badge)', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());

      // When enabled=false, the card shows a "Soon" text. Since all 3 are
      // enabled, no "Soon" badges should appear.
      expect(find.text('Soon'), findsNothing);
    });

    testWidgets('each card shows a chevron_right icon', (tester) async {
      await tester.pumpWidget(buildSubject());

      // All three cards get a chevron icon.
      expect(find.byIcon(Icons.chevron_right), findsNWidgets(3));
    });
  });
}
