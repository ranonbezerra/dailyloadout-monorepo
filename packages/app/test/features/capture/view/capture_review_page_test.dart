import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/capture/bloc/capture_bloc.dart';
import 'package:app/features/capture/view/capture_review_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockCaptureBloc extends MockBloc<CaptureEvent, CaptureState>
    implements CaptureBloc {}

class MockLibraryRepository extends Mock implements LibraryRepository {}

// --- Test fixtures ---

const _pendingCandidate = CaptureCandidate(
  publicId: 'cand-1',
  title: 'Hollow Knight',
  igdbTitle: 'Hollow Knight',
  igdbSummary: 'A metroidvania game',
  igdbGenres: ['Action', 'Adventure'],
  confidence: 0.95,
  status: 'pending',
);

const _confirmedCandidate = CaptureCandidate(
  publicId: 'cand-2',
  title: 'Hades',
  igdbTitle: 'Hades',
  igdbSummary: 'A roguelike game',
  igdbGenres: ['Action', 'RPG'],
  confidence: 0.88,
  status: 'confirmed',
);

const _rejectedCandidate = CaptureCandidate(
  publicId: 'cand-3',
  title: 'Celeste',
  igdbTitle: 'Celeste',
  igdbSummary: 'A platformer',
  igdbGenres: ['Platformer'],
  confidence: 0.72,
  status: 'rejected',
);

const _candidateWithPlatformHint = CaptureCandidate(
  publicId: 'cand-4',
  title: 'God of War',
  igdbTitle: 'God of War',
  platformHint: 'PS5',
  status: 'pending',
);

Capture _buildCapture({
  String status = 'review',
  List<CaptureCandidate> candidates = const [],
}) {
  return Capture(
    publicId: 'cap-1',
    inputType: 'text',
    rawText: 'Some text',
    status: status,
    candidates: candidates,
    createdAt: DateTime(2024),
    updatedAt: DateTime(2024),
  );
}

void main() {
  late MockCaptureBloc mockBloc;
  late MockLibraryRepository mockLibraryRepo;

  setUp(() {
    mockBloc = MockCaptureBloc();
    mockLibraryRepo = MockLibraryRepository();

    when(() => mockLibraryRepo.listPlatforms()).thenAnswer(
      (_) async => const [
        Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'PlayStation'),
        Platform(id: 2, slug: 'switch', label: 'Switch', family: 'Nintendo'),
      ],
    );
  });

  Widget buildSubject() {
    return MaterialApp(
      home: BlocProvider<CaptureBloc>.value(
        value: mockBloc,
        child: CaptureReviewPage(
          capturePublicId: 'cap-1',
          libraryRepository: mockLibraryRepo,
        ),
      ),
    );
  }

  group('CaptureReviewPage', () {
    testWidgets('renders AppBar with "Review Captures" title', (tester) async {
      when(() => mockBloc.state).thenReturn(const CaptureInitial());

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.text('Review Captures'),
        ),
        findsOneWidget,
      );
    });

    group('CaptureSubmitting / CaptureLoading state', () {
      testWidgets('shows CircularProgressIndicator for CaptureSubmitting', (
        tester,
      ) async {
        when(() => mockBloc.state).thenReturn(const CaptureSubmitting());
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: const CaptureSubmitting(),
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      });

      testWidgets('shows CircularProgressIndicator for CaptureLoading', (
        tester,
      ) async {
        when(() => mockBloc.state).thenReturn(const CaptureLoading());
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: const CaptureLoading(),
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.byType(CircularProgressIndicator), findsOneWidget);
      });
    });

    group('CaptureError state', () {
      testWidgets('shows error message and "Try Again" button', (tester) async {
        const errorState = CaptureError(message: 'Network error');
        when(() => mockBloc.state).thenReturn(errorState);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: errorState,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Network error'), findsOneWidget);
        expect(find.widgetWithText(FilledButton, 'Try Again'), findsOneWidget);
      });
    });

    group('CaptureInitial (unexpected) state', () {
      testWidgets(
        'shows "No capture data available." and "Start Capture" button',
        (tester) async {
          when(() => mockBloc.state).thenReturn(const CaptureInitial());

          await tester.pumpWidget(buildSubject());
          await tester.pump();

          expect(find.text('No capture data available.'), findsOneWidget);
          expect(
            find.widgetWithText(FilledButton, 'Start Capture'),
            findsOneWidget,
          );
        },
      );
    });

    group('CaptureSubmitted with empty candidates', () {
      testWidgets('shows "No games were extracted" message', (tester) async {
        final capture = _buildCapture();
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(
          find.textContaining('No games were extracted from your text'),
          findsOneWidget,
        );
      });
    });

    group('CaptureSubmitted with candidates', () {
      testWidgets('shows candidate card with game title (igdbTitle)', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Hollow Knight'), findsOneWidget);
      });

      testWidgets('shows candidate title (fallback) when igdbTitle is null', (
        tester,
      ) async {
        const candidateNoIgdb = CaptureCandidate(
          publicId: 'cand-x',
          title: 'Fallback Title',
          status: 'pending',
        );
        final capture = _buildCapture(candidates: [candidateNoIgdb]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Fallback Title'), findsOneWidget);
      });

      testWidgets('shows platform hint if present', (tester) async {
        final capture = _buildCapture(candidates: [_candidateWithPlatformHint]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Platform hint: PS5'), findsOneWidget);
      });

      testWidgets('shows confidence indicator if present', (tester) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        // Confidence of 0.95 -> "95% match"
        expect(find.text('95% match'), findsOneWidget);
        expect(find.byType(LinearProgressIndicator), findsOneWidget);
      });

      testWidgets('shows genres if present', (tester) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Action, Adventure'), findsOneWidget);
      });

      testWidgets('shows Pending status badge for pending candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Pending'), findsOneWidget);
      });

      testWidgets('shows Confirmed status badge for confirmed candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_confirmedCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Confirmed'), findsOneWidget);
      });

      testWidgets('shows Rejected status badge for rejected candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_rejectedCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Rejected'), findsOneWidget);
      });

      testWidgets('shows Confirm and Reject buttons for pending candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.widgetWithText(FilledButton, 'Confirm'), findsOneWidget);
        expect(find.widgetWithText(OutlinedButton, 'Reject'), findsOneWidget);
      });

      testWidgets('no Confirm/Reject buttons for confirmed candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_confirmedCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        // The "Confirm" button text from the candidate card action buttons
        // should not be present. Note: there might be a "Done" FilledButton.
        expect(find.widgetWithText(OutlinedButton, 'Reject'), findsNothing);
      });

      testWidgets('no Confirm/Reject buttons for rejected candidates', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_rejectedCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.widgetWithText(OutlinedButton, 'Reject'), findsNothing);
      });

      testWidgets('shows "Extracted Games (N)" header', (tester) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Extracted Games (1)'), findsOneWidget);
      });

      testWidgets('shows cover placeholder when igdbCoverUrl is null', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.byIcon(Icons.videogame_asset), findsOneWidget);
      });
    });

    group('all candidates resolved', () {
      testWidgets('shows "Done -- View Library" button when all resolved', (
        tester,
      ) async {
        final capture = _buildCapture(
          candidates: [_confirmedCandidate, _rejectedCandidate],
        );
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        // FilledButton.icon creates a subtype, so use find.bySubtype.
        expect(find.text('Done — View Library'), findsOneWidget);
        final doneButton = find.ancestor(
          of: find.text('Done — View Library'),
          matching: find.bySubtype<FilledButton>(),
        );
        expect(doneButton, findsOneWidget);
        // "Back to Capture" should not appear when all resolved.
        expect(find.text('Back to Capture'), findsNothing);
      });
    });

    group('not all candidates resolved', () {
      testWidgets('shows "Back to Capture" TextButton', (tester) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(
          find.widgetWithText(TextButton, 'Back to Capture'),
          findsOneWidget,
        );
        // "Done" button should not appear.
        expect(find.text('Done — View Library'), findsNothing);
      });
    });

    group('capture status header', () {
      for (final testCase in [
        (
          status: 'queued',
          icon: Icons.hourglass_empty,
          label: 'Queued for processing',
        ),
        (
          status: 'processing',
          icon: Icons.sync,
          label: 'Processing your text...',
        ),
        (
          status: 'review',
          icon: Icons.rate_review_outlined,
          label: 'Ready for review',
        ),
        (
          status: 'committed',
          icon: Icons.check_circle_outline,
          label: 'All games added to library',
        ),
        (
          status: 'partially_committed',
          icon: Icons.check_circle_outline,
          label: 'Some games added to library',
        ),
        (
          status: 'failed',
          icon: Icons.error_outline,
          label: 'Processing failed',
        ),
        (status: 'cancelled', icon: Icons.cancel_outlined, label: 'Cancelled'),
      ]) {
        testWidgets(
          'shows correct icon and label for "${testCase.status}" status',
          (tester) async {
            final capture = _buildCapture(
              status: testCase.status,
              candidates: [_pendingCandidate],
            );
            final state = CaptureSubmitted(capture: capture);
            when(() => mockBloc.state).thenReturn(state);
            whenListen(
              mockBloc,
              const Stream<CaptureState>.empty(),
              initialState: state,
            );

            await tester.pumpWidget(buildSubject());
            await tester.pump();

            expect(find.byIcon(testCase.icon), findsOneWidget);
            // For "cancelled" the label text matches the badge text too, so
            // use findsAtLeastNWidgets(1) to account for both.
            expect(find.text(testCase.label), findsAtLeastNWidgets(1));
            expect(find.text('Capture Status'), findsOneWidget);
          },
        );
      }

      testWidgets('shows status badge with capitalized status text', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        // The _CaptureStatusBadge capitalizes first letter: "Review"
        expect(find.text('Review'), findsOneWidget);
      });
    });

    group('reject candidate action', () {
      testWidgets('dispatches RejectCandidate when Reject is tapped', (
        tester,
      ) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        await tester.tap(find.widgetWithText(OutlinedButton, 'Reject'));
        await tester.pumpAndSettle();

        verify(
          () => mockBloc.add(
            const RejectCandidate(captureId: 'cap-1', candidateId: 'cand-1'),
          ),
        ).called(1);
      });
    });

    group('confirm candidate action', () {
      testWidgets('tapping Confirm opens bottom sheet', (tester) async {
        final capture = _buildCapture(candidates: [_pendingCandidate]);
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        await tester.tap(find.widgetWithText(FilledButton, 'Confirm'));
        await tester.pumpAndSettle();

        // The bottom sheet should show the candidate title.
        expect(find.text('Confirm: Hollow Knight'), findsOneWidget);
        // It should show "Platform" label and "Library Status" label.
        expect(find.text('Platform'), findsOneWidget);
        expect(find.text('Library Status'), findsOneWidget);
        // It should show "Add to Library" button.
        expect(
          find.widgetWithText(FilledButton, 'Add to Library'),
          findsOneWidget,
        );
      });
    });

    group('multiple candidates', () {
      testWidgets('renders multiple candidate cards', (tester) async {
        final capture = _buildCapture(
          candidates: [
            _pendingCandidate,
            _confirmedCandidate,
            _rejectedCandidate,
          ],
        );
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        expect(find.text('Extracted Games (3)'), findsOneWidget);
        expect(find.text('Hollow Knight'), findsOneWidget);
        expect(find.text('Hades'), findsOneWidget);
        expect(find.text('Celeste'), findsOneWidget);
      });

      testWidgets('only pending candidates show Confirm/Reject buttons', (
        tester,
      ) async {
        final capture = _buildCapture(
          candidates: [
            _pendingCandidate,
            _confirmedCandidate,
            _rejectedCandidate,
          ],
        );
        final state = CaptureSubmitted(capture: capture);
        when(() => mockBloc.state).thenReturn(state);
        whenListen(
          mockBloc,
          const Stream<CaptureState>.empty(),
          initialState: state,
        );

        await tester.pumpWidget(buildSubject());
        await tester.pump();

        // Only one Confirm and one Reject (for the pending candidate).
        expect(find.widgetWithText(FilledButton, 'Confirm'), findsOneWidget);
        expect(find.widgetWithText(OutlinedButton, 'Reject'), findsOneWidget);
      });
    });
  });
}
