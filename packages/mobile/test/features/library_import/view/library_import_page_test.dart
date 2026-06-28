import 'package:app/core/capture/capture_models.dart';
import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library_import/bloc/library_import_bloc.dart';
import 'package:app/features/library_import/view/library_import_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryImportBloc
    extends MockBloc<LibraryImportEvent, LibraryImportState>
    implements LibraryImportBloc {}

class MockLibraryRepository extends Mock implements LibraryRepository {}

const _platforms = [
  Platform(id: 10, slug: 'steam', label: 'Steam (PC)', family: 'PC'),
  Platform(
    id: 20,
    slug: 'switch',
    label: 'Nintendo Switch',
    family: 'Nintendo',
  ),
];

Capture _review() => Capture(
  publicId: 'cap-1',
  inputType: 'library_import',
  status: 'review',
  candidates: const [
    CaptureCandidate(
      publicId: 'cand-1',
      title: 'Elden Ring',
      igdbTitle: 'Elden Ring',
      status: 'pending',
    ),
    CaptureCandidate(publicId: 'cand-2', title: 'Hades', status: 'pending'),
  ],
  createdAt: DateTime(2025),
  updatedAt: DateTime(2025),
);

void main() {
  late MockLibraryImportBloc bloc;
  late MockLibraryRepository repo;

  setUpAll(() {
    registerFallbackValue(const SubmitLibraryImport(imagePaths: <String>[]));
  });

  setUp(() {
    bloc = MockLibraryImportBloc();
    repo = MockLibraryRepository();
    when(() => repo.listPlatforms()).thenAnswer((_) async => _platforms);
  });

  Widget buildSubject() {
    return MaterialApp.router(
      routerConfig: GoRouter(
        initialLocation: '/import',
        routes: [
          GoRoute(
            path: '/import',
            builder: (context, state) => BlocProvider<LibraryImportBloc>.value(
              value: bloc,
              child: LibraryImportPage(libraryRepository: repo),
            ),
          ),
          GoRoute(
            path: '/library',
            builder: (context, state) => const Scaffold(body: Text('LIBRARY')),
          ),
        ],
      ),
    );
  }

  group('platform picker step', () {
    testWidgets('renders the six platform option cards', (tester) async {
      when(() => bloc.state).thenReturn(const LibraryImportInitial());

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      // Card titles render off-screen too; assert against the full list.
      for (final label in [
        'Steam',
        'Xbox',
        'GOG',
        'PlayStation',
        'Epic',
        'Nintendo Switch',
      ]) {
        expect(
          find.text(label, skipOffstage: false),
          findsWidgets,
          reason: 'missing $label card',
        );
      }
    });

    testWidgets('selecting a platform advances to its hint step', (
      tester,
    ) async {
      when(() => bloc.state).thenReturn(const LibraryImportInitial());

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      await tester.tap(find.text('Steam'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('switch to List view (the left rail'),
        findsOneWidget,
      );
      expect(find.text('Pick screenshots'), findsOneWidget);
    });
  });

  group('confirmation step (Review state)', () {
    testWidgets('renders a checkbox per candidate, all checked', (
      tester,
    ) async {
      whenListen(
        bloc,
        Stream.value(LibraryImportReview(capture: _review())),
        initialState: const LibraryImportInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      final checkboxes = tester
          .widgetList<Checkbox>(find.byType(Checkbox))
          .toList();
      expect(checkboxes, hasLength(2));
      expect(checkboxes.every((c) => c.value ?? false), isTrue);
      expect(find.text('Add 2 games'), findsOneWidget);
    });

    testWidgets('"Add" dispatches BulkConfirmImport with checked ids', (
      tester,
    ) async {
      whenListen(
        bloc,
        Stream.value(LibraryImportReview(capture: _review())),
        initialState: const LibraryImportInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Add 2 games'));
      await tester.pump();

      final captured = verify(() => bloc.add(captureAny())).captured;
      final event = captured.whereType<BulkConfirmImport>().single;
      expect(event.captureId, 'cap-1');
      expect(event.confirmIds, containsAll(['cand-1', 'cand-2']));
      // Default platform matched from the Steam token would be 10, but with no
      // prior picker selection it falls back to the first platform.
      expect(event.platformId, isNotNull);
      expect(event.status, 'backlog');
    });

    testWidgets('unchecking a candidate excludes it from the dispatch', (
      tester,
    ) async {
      whenListen(
        bloc,
        Stream.value(LibraryImportReview(capture: _review())),
        initialState: const LibraryImportInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      // Uncheck the second candidate (Hades).
      await tester.tap(find.byType(Checkbox).last);
      await tester.pumpAndSettle();

      expect(find.text('Add 1 games'), findsOneWidget);

      await tester.tap(find.text('Add 1 games'));
      await tester.pump();

      final captured = verify(() => bloc.add(captureAny())).captured;
      final event = captured.whereType<BulkConfirmImport>().single;
      expect(event.confirmIds, ['cand-1']);
    });
  });

  group('Done state', () {
    testWidgets('shows snackbar and navigates to /library', (tester) async {
      whenListen(
        bloc,
        Stream.value(const LibraryImportDone(confirmed: 3, rejected: 0)),
        initialState: const LibraryImportInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();
      await tester.pump();

      expect(find.text('Imported 3 games'), findsOneWidget);
      await tester.pumpAndSettle();
      expect(find.text('LIBRARY'), findsOneWidget);
    });
  });

  group('busy + error states', () {
    testWidgets('Submitting shows a progress view', (tester) async {
      when(() => bloc.state).thenReturn(const LibraryImportSubmitting());

      await tester.pumpWidget(buildSubject());
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('Error surfaces a snackbar', (tester) async {
      whenListen(
        bloc,
        Stream.value(const LibraryImportError(message: 'Daily cap reached')),
        initialState: const LibraryImportInitial(),
      );

      await tester.pumpWidget(buildSubject());
      await tester.pump();
      await tester.pump();

      expect(find.text('Daily cap reached'), findsOneWidget);
    });
  });
}
