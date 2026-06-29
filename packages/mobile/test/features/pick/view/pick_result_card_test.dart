import 'package:app/core/library/library_models.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/features/pick/view/pick_result_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'Sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'hollow-knight',
  title: 'Hollow Knight',
  metadataSource: 'igdb',
  createdAt: _now,
  genres: const ['Metroidvania', 'Action'],
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

final _pick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  createdAt: _now,
  updatedAt: _now,
);

final _acceptedPick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'accepted',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedPick = Pick(
  publicId: 'pick-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'rejected',
  createdAt: _now,
  updatedAt: _now,
);

final _pickNoEntry = Pick(
  publicId: 'pick-003',
  mood: 'energetic',
  availableMinutes: 30,
  mentalEnergy: 'low',
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  Widget buildSubject({
    required Pick pick,
    int rank = 0,
    int totalResults = 1,
    bool isActioning = false,
    bool isGeneratingRecap = false,
    String? recapText,
    VoidCallback? onAccept,
    VoidCallback? onReject,
    void Function(String mode)? onGetRecap,
    VoidCallback? onStartWithRecap,
  }) {
    return MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: PickResultCard(
            pick: pick,
            rank: rank,
            totalResults: totalResults,
            isActioning: isActioning,
            isGeneratingRecap: isGeneratingRecap,
            recapText: recapText,
            onAccept: onAccept ?? () {},
            onReject: onReject ?? () {},
            onGetRecap: onGetRecap ?? (_) {},
            onStartWithRecap: onStartWithRecap ?? () {},
          ),
        ),
      ),
    );
  }

  group('PickResultCard', () {
    testWidgets('shows game title from pick.libraryEntry', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Hollow Knight'), findsOneWidget);
    });

    testWidgets('shows "Unknown game" when '
        'libraryEntry is null', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pickNoEntry));

      expect(find.text('Unknown game'), findsOneWidget);
    });

    testWidgets('shows platform label badge', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('PS5'), findsOneWidget);
    });

    testWidgets('shows status badge', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      // Status "playing" capitalized to "Playing"
      expect(find.text('Playing'), findsOneWidget);
    });

    testWidgets('shows reasoning text', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Great for a relaxed session'), findsOneWidget);
    });

    testWidgets('shows genre chips when genres present', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Metroidvania'), findsOneWidget);
      expect(find.text('Action'), findsOneWidget);
    });

    testWidgets('shows "Just play" and '
        '"Reject" buttons when action is null', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Just play'), findsOneWidget);
      expect(find.widgetWithText(OutlinedButton, 'Reject'), findsOneWidget);
    });

    testWidgets('shows "Session started!" text '
        'when action is accepted', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _acceptedPick));

      expect(find.text('Session started!'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
      // No action buttons visible
      expect(find.text('Just play'), findsNothing);
      expect(find.text('Reject'), findsNothing);
    });

    testWidgets('shows "Rejected" text '
        'when action is rejected', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _rejectedPick));

      expect(find.text('Rejected'), findsOneWidget);
      // No action buttons visible
      expect(find.text('Just play'), findsNothing);
      expect(find.text('Reject'), findsNothing);
    });

    testWidgets('shows rank badge "Best Match" '
        'when rank=0 and totalResults > 1', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick, totalResults: 3));

      expect(find.text('Best Match'), findsOneWidget);
    });

    testWidgets('shows rank badge "Great Alternative" '
        'when rank=1 and totalResults > 1', (tester) async {
      await tester.pumpWidget(
        buildSubject(pick: _pick, rank: 1, totalResults: 3),
      );

      expect(find.text('Great Alternative'), findsOneWidget);
    });

    testWidgets('shows rank badge "Worth Considering" '
        'when rank=2 and totalResults > 1', (tester) async {
      await tester.pumpWidget(
        buildSubject(pick: _pick, rank: 2, totalResults: 3),
      );

      expect(find.text('Worth Considering'), findsOneWidget);
    });

    testWidgets('does NOT show rank badge '
        'when totalResults is 1', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Best Match'), findsNothing);
      expect(find.text('Great Alternative'), findsNothing);
      expect(find.text('Worth Considering'), findsNothing);
    });

    testWidgets('shows loading state when '
        'isActioning is true', (tester) async {
      await tester.pumpWidget(buildSubject(pick: _pick, isActioning: true));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Starting...'), findsOneWidget);
      // Reject button should be disabled
      final rejectBtn = tester.widget<OutlinedButton>(
        find.widgetWithText(OutlinedButton, 'Reject'),
      );
      expect(rejectBtn.onPressed, isNull);
    });

    testWidgets('accept button calls onAccept callback', (tester) async {
      var accepted = false;
      await tester.pumpWidget(
        buildSubject(pick: _pick, onAccept: () => accepted = true),
      );

      await tester.tap(find.text('Just play'));

      expect(accepted, isTrue);
    });

    testWidgets('reject button calls onReject callback', (tester) async {
      var rejected = false;
      await tester.pumpWidget(
        buildSubject(pick: _pick, onReject: () => rejected = true),
      );

      await tester.tap(find.widgetWithText(OutlinedButton, 'Reject'));

      expect(rejected, isTrue);
    });

    testWidgets('shows Quick/Deep recap + Just play when no recap yet', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject(pick: _pick));

      expect(find.text('Quick recap'), findsOneWidget);
      expect(find.text('Deep recap'), findsOneWidget);
      expect(find.text('Just play'), findsOneWidget);
    });

    testWidgets('Quick recap calls onGetRecap with quick mode', (tester) async {
      String? mode;
      await tester.pumpWidget(
        buildSubject(pick: _pick, onGetRecap: (m) => mode = m),
      );

      await tester.tap(find.text('Quick recap'));

      expect(mode, 'quick');
    });

    testWidgets('Deep recap calls onGetRecap with deep mode', (tester) async {
      String? mode;
      await tester.pumpWidget(
        buildSubject(pick: _pick, onGetRecap: (m) => mode = m),
      );

      await tester.tap(find.text('Deep recap'));

      expect(mode, 'deep');
    });

    testWidgets('shows a spinner and disables recap while generating', (
      tester,
    ) async {
      var requested = false;
      await tester.pumpWidget(
        buildSubject(
          pick: _pick,
          isGeneratingRecap: true,
          onGetRecap: (_) => requested = true,
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      // The recap buttons are disabled mid-generation: tapping is a no-op.
      await tester.tap(find.text('Quick recap'));
      expect(requested, isFalse);
    });

    testWidgets('shows recap text and "Start with recap" '
        'once a recap is present', (tester) async {
      await tester.pumpWidget(
        buildSubject(pick: _pick, recapText: 'Continue toward the Erdtree.'),
      );

      expect(find.text('Continue toward the Erdtree.'), findsOneWidget);
      expect(find.text('Start with recap'), findsOneWidget);
      // Recap options are hidden once a recap has been produced.
      expect(find.text('Quick recap'), findsNothing);
      expect(find.text('Deep recap'), findsNothing);
      expect(find.text('Just play'), findsNothing);
    });

    testWidgets('"Start with recap" calls onStartWithRecap callback', (
      tester,
    ) async {
      var started = false;
      await tester.pumpWidget(
        buildSubject(
          pick: _pick,
          recapText: 'Continue toward the Erdtree.',
          onStartWithRecap: () => started = true,
        ),
      );

      await tester.tap(find.text('Start with recap'));

      expect(started, isTrue);
    });
  });
}
