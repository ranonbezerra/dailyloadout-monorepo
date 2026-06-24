import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library/view/library_detail_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockLibraryBloc extends MockBloc<LibraryEvent, LibraryState>
    implements LibraryBloc {}

final _entryWithSummary = LibraryEntry(
  publicId: 'entry-1',
  game: Game(
    publicId: 'game-1',
    slug: 'elden-ring',
    title: 'Elden Ring',
    metadataSource: 'igdb',
    createdAt: DateTime(2024),
    summary: 'An action RPG by FromSoftware.',
  ),
  platform: const Platform(
    id: 1,
    slug: 'ps5',
    label: 'PlayStation 5',
    family: 'playstation',
  ),
  status: 'playing',
  notes: 'Beat Margit!',
  createdAt: DateTime(2024),
  updatedAt: DateTime(2024),
);

final _entryWithoutSummary = LibraryEntry(
  publicId: 'entry-2',
  game: Game(
    publicId: 'game-2',
    slug: 'zelda-totk',
    title: 'Zelda: TotK',
    metadataSource: 'igdb',
    createdAt: DateTime(2024),
  ),
  platform: const Platform(
    id: 2,
    slug: 'switch',
    label: 'Nintendo Switch',
    family: 'nintendo',
  ),
  status: 'backlog',
  createdAt: DateTime(2024),
  updatedAt: DateTime(2024),
);

void main() {
  setUpAll(() {
    registerFallbackValue(const UpdateEntry(publicId: 'x'));
    registerFallbackValue(const DeleteEntry(publicId: 'x'));
  });

  late MockLibraryBloc libraryBloc;

  setUp(() {
    libraryBloc = MockLibraryBloc();
  });

  tearDown(() {
    libraryBloc.close();
  });

  Widget buildSubject({String entryPublicId = 'entry-1'}) {
    return BlocProvider<LibraryBloc>.value(
      value: libraryBloc,
      child: MaterialApp(home: LibraryDetailPage(entryPublicId: entryPublicId)),
    );
  }

  /// Wrapper with a GoRouter so `context.go()` works after delete.
  Widget buildRoutedSubject({String entryPublicId = 'entry-1'}) {
    final router = GoRouter(
      initialLocation: '/library/$entryPublicId',
      routes: [
        GoRoute(
          path: '/library/:id',
          builder: (_, __) => LibraryDetailPage(entryPublicId: entryPublicId),
        ),
        GoRoute(
          path: '/library',
          builder: (_, __) => const Scaffold(body: Text('Library stub')),
        ),
      ],
    );

    return BlocProvider<LibraryBloc>.value(
      value: libraryBloc,
      child: MaterialApp.router(routerConfig: router),
    );
  }

  group('LibraryDetailPage', () {
    testWidgets('shows loading when entry not found in state', (tester) async {
      // LibraryLoaded but with an entry that does not match our ID.
      when(
        () => libraryBloc.state,
      ).thenReturn(const LibraryLoaded(entries: [], total: 0, hasMore: false));

      await tester.pumpWidget(buildSubject(entryPublicId: 'nonexistent'));

      expect(find.text('Details'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows game title in AppBar when entry found', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      // The AppBar should contain the game title.
      final appBarFinder = find.byType(AppBar);
      expect(appBarFinder, findsOneWidget);
      expect(
        find.descendant(of: appBarFinder, matching: find.text('Elden Ring')),
        findsOneWidget,
      );
    });

    testWidgets('shows platform label', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('PlayStation 5'), findsOneWidget);
    });

    testWidgets('shows status dropdown with current status', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.byType(DropdownButtonFormField<String>), findsOneWidget);

      // The dropdown should display the capitalized current status.
      expect(find.text('Playing'), findsOneWidget);
    });

    testWidgets('shows notes TextFormField', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.widgetWithText(TextFormField, 'Notes'), findsOneWidget);
    });

    testWidgets('shows summary when game has summary', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.text('Summary'), findsOneWidget);
      expect(find.text('An action RPG by FromSoftware.'), findsOneWidget);
    });

    testWidgets('does not show summary section when game has no summary', (
      tester,
    ) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(
          entries: [_entryWithoutSummary],
          total: 1,
          hasMore: false,
        ),
      );

      await tester.pumpWidget(buildSubject(entryPublicId: 'entry-2'));

      expect(find.text('Summary'), findsNothing);
    });

    testWidgets('shows save IconButton', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      expect(find.byIcon(Icons.save), findsOneWidget);
      expect(find.widgetWithIcon(IconButton, Icons.save), findsOneWidget);
    });

    testWidgets('shows Remove from Library OutlinedButton', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      // The button may be off-screen in the SingleChildScrollView,
      // so scroll until it is visible.
      await tester.scrollUntilVisible(
        find.text('Remove from Library'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      expect(find.text('Remove from Library'), findsOneWidget);
      expect(find.byIcon(Icons.delete_outline), findsOneWidget);
    });

    testWidgets('delete button shows confirmation dialog', (tester) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      // Scroll until the delete button is visible.
      await tester.scrollUntilVisible(
        find.text('Remove from Library'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      // Tap the delete button by finding the text.
      await tester.tap(find.text('Remove from Library'));
      await tester.pumpAndSettle();

      // Verify the confirmation dialog appears.
      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Delete entry'), findsOneWidget);
      expect(
        find.text(
          'Are you sure you want to remove this game from your library?',
        ),
        findsOneWidget,
      );
      expect(find.text('Cancel'), findsOneWidget);
      expect(find.text('Delete'), findsOneWidget);
    });

    testWidgets('save button dispatches UpdateEntry and shows SnackBar', (
      tester,
    ) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Notes'),
        'New notes',
      );
      await tester.tap(find.byIcon(Icons.save));
      await tester.pump();

      verify(
        () => libraryBloc.add(
          const UpdateEntry(
            publicId: 'entry-1',
            status: 'playing',
            notes: 'New notes',
          ),
        ),
      ).called(1);
      expect(find.text('Entry updated'), findsOneWidget);
    });

    testWidgets('cancelling delete dialog does not dispatch DeleteEntry', (
      tester,
    ) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildSubject());

      await tester.scrollUntilVisible(
        find.text('Remove from Library'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Remove from Library'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();

      verifyNever(() => libraryBloc.add(any(that: isA<DeleteEntry>())));
    });

    testWidgets('confirming delete dispatches DeleteEntry and navigates', (
      tester,
    ) async {
      when(() => libraryBloc.state).thenReturn(
        LibraryLoaded(entries: [_entryWithSummary], total: 1, hasMore: false),
      );

      await tester.pumpWidget(buildRoutedSubject());
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(
        find.text('Remove from Library'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Remove from Library'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();

      verify(
        () => libraryBloc.add(const DeleteEntry(publicId: 'entry-1')),
      ).called(1);
      expect(find.text('Library stub'), findsOneWidget);
    });
  });
}
