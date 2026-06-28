import 'package:app/core/library/library_models.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/features/loadout/view/loadout_result_card.dart';
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

final _loadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  createdAt: _now,
  updatedAt: _now,
);

final _acceptedLoadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'accepted',
  createdAt: _now,
  updatedAt: _now,
);

final _rejectedLoadout = Loadout(
  publicId: 'loadout-001',
  libraryEntry: _entry,
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'Great for a relaxed session',
  action: 'rejected',
  createdAt: _now,
  updatedAt: _now,
);

final _loadoutNoEntry = Loadout(
  publicId: 'loadout-003',
  mood: 'energetic',
  availableMinutes: 30,
  mentalEnergy: 'low',
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  Widget buildSubject({
    required Loadout loadout,
    int rank = 0,
    int totalResults = 1,
    bool isActioning = false,
    bool isGeneratingBriefing = false,
    String? briefingText,
    VoidCallback? onAccept,
    VoidCallback? onReject,
    void Function(String mode)? onGetBriefing,
    VoidCallback? onStartWithBriefing,
  }) {
    return MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(
          child: LoadoutResultCard(
            loadout: loadout,
            rank: rank,
            totalResults: totalResults,
            isActioning: isActioning,
            isGeneratingBriefing: isGeneratingBriefing,
            briefingText: briefingText,
            onAccept: onAccept ?? () {},
            onReject: onReject ?? () {},
            onGetBriefing: onGetBriefing ?? (_) {},
            onStartWithBriefing: onStartWithBriefing ?? () {},
          ),
        ),
      ),
    );
  }

  group('LoadoutResultCard', () {
    testWidgets('shows game title from loadout.libraryEntry', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Hollow Knight'), findsOneWidget);
    });

    testWidgets('shows "Unknown game" when '
        'libraryEntry is null', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadoutNoEntry));

      expect(find.text('Unknown game'), findsOneWidget);
    });

    testWidgets('shows platform label badge', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('PS5'), findsOneWidget);
    });

    testWidgets('shows status badge', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      // Status "playing" capitalized to "Playing"
      expect(find.text('Playing'), findsOneWidget);
    });

    testWidgets('shows reasoning text', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Great for a relaxed session'), findsOneWidget);
    });

    testWidgets('shows genre chips when genres present', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Metroidvania'), findsOneWidget);
      expect(find.text('Action'), findsOneWidget);
    });

    testWidgets('shows "Just play" and '
        '"Reject" buttons when action is null', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Just play'), findsOneWidget);
      expect(find.widgetWithText(OutlinedButton, 'Reject'), findsOneWidget);
    });

    testWidgets('shows "Mission started!" text '
        'when action is accepted', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _acceptedLoadout));

      expect(find.text('Mission started!'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
      // No action buttons visible
      expect(find.text('Just play'), findsNothing);
      expect(find.text('Reject'), findsNothing);
    });

    testWidgets('shows "Rejected" text '
        'when action is rejected', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _rejectedLoadout));

      expect(find.text('Rejected'), findsOneWidget);
      // No action buttons visible
      expect(find.text('Just play'), findsNothing);
      expect(find.text('Reject'), findsNothing);
    });

    testWidgets('shows rank badge "Best Match" '
        'when rank=0 and totalResults > 1', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout, totalResults: 3));

      expect(find.text('Best Match'), findsOneWidget);
    });

    testWidgets('shows rank badge "Great Alternative" '
        'when rank=1 and totalResults > 1', (tester) async {
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, rank: 1, totalResults: 3),
      );

      expect(find.text('Great Alternative'), findsOneWidget);
    });

    testWidgets('shows rank badge "Worth Considering" '
        'when rank=2 and totalResults > 1', (tester) async {
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, rank: 2, totalResults: 3),
      );

      expect(find.text('Worth Considering'), findsOneWidget);
    });

    testWidgets('does NOT show rank badge '
        'when totalResults is 1', (tester) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Best Match'), findsNothing);
      expect(find.text('Great Alternative'), findsNothing);
      expect(find.text('Worth Considering'), findsNothing);
    });

    testWidgets('shows loading state when '
        'isActioning is true', (tester) async {
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, isActioning: true),
      );

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
        buildSubject(loadout: _loadout, onAccept: () => accepted = true),
      );

      await tester.tap(find.text('Just play'));

      expect(accepted, isTrue);
    });

    testWidgets('reject button calls onReject callback', (tester) async {
      var rejected = false;
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, onReject: () => rejected = true),
      );

      await tester.tap(find.widgetWithText(OutlinedButton, 'Reject'));

      expect(rejected, isTrue);
    });

    testWidgets('shows Quick/Deep briefing + Just play when no briefing yet', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject(loadout: _loadout));

      expect(find.text('Quick briefing'), findsOneWidget);
      expect(find.text('Deep briefing'), findsOneWidget);
      expect(find.text('Just play'), findsOneWidget);
    });

    testWidgets('Quick briefing calls onGetBriefing with quick mode', (
      tester,
    ) async {
      String? mode;
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, onGetBriefing: (m) => mode = m),
      );

      await tester.tap(find.text('Quick briefing'));

      expect(mode, 'quick');
    });

    testWidgets('Deep briefing calls onGetBriefing with deep mode', (
      tester,
    ) async {
      String? mode;
      await tester.pumpWidget(
        buildSubject(loadout: _loadout, onGetBriefing: (m) => mode = m),
      );

      await tester.tap(find.text('Deep briefing'));

      expect(mode, 'deep');
    });

    testWidgets('shows a spinner and disables briefing while generating', (
      tester,
    ) async {
      var requested = false;
      await tester.pumpWidget(
        buildSubject(
          loadout: _loadout,
          isGeneratingBriefing: true,
          onGetBriefing: (_) => requested = true,
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      // The briefing buttons are disabled mid-generation: tapping is a no-op.
      await tester.tap(find.text('Quick briefing'));
      expect(requested, isFalse);
    });

    testWidgets('shows briefing text and "Start with briefing" '
        'once a briefing is present', (tester) async {
      await tester.pumpWidget(
        buildSubject(
          loadout: _loadout,
          briefingText: 'Continue toward the Erdtree.',
        ),
      );

      expect(find.text('Continue toward the Erdtree.'), findsOneWidget);
      expect(find.text('Start with briefing'), findsOneWidget);
      // Briefing options are hidden once a briefing has been produced.
      expect(find.text('Quick briefing'), findsNothing);
      expect(find.text('Deep briefing'), findsNothing);
      expect(find.text('Just play'), findsNothing);
    });

    testWidgets('"Start with briefing" calls onStartWithBriefing callback', (
      tester,
    ) async {
      var started = false;
      await tester.pumpWidget(
        buildSubject(
          loadout: _loadout,
          briefingText: 'Continue toward the Erdtree.',
          onStartWithBriefing: () => started = true,
        ),
      );

      await tester.tap(find.text('Start with briefing'));

      expect(started, isTrue);
    });
  });
}
