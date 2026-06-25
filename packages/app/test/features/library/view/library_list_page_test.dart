import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library/view/library_list_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockLibraryBloc extends MockBloc<LibraryEvent, LibraryState>
    implements LibraryBloc {}

/// Two sample entries used by tests that need loaded data.
final _sampleEntries = [
  LibraryEntry(
    publicId: 'entry-1',
    game: Game(
      publicId: 'game-1',
      slug: 'elden-ring',
      title: 'Elden Ring',
      metadataSource: 'igdb',
      createdAt: DateTime(2024),
      summary: 'An action RPG.',
    ),
    platform: const Platform(
      id: 1,
      slug: 'ps5',
      label: 'PlayStation 5',
      family: 'playstation',
    ),
    status: 'playing',
    createdAt: DateTime(2024),
    updatedAt: DateTime(2024),
  ),
  LibraryEntry(
    publicId: 'entry-2',
    game: Game(
      publicId: 'game-2',
      slug: 'zelda-totk',
      title: 'Zelda: Tears of the Kingdom',
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
  ),
];

void main() {
  late MockLibraryBloc libraryBloc;

  setUp(() {
    libraryBloc = MockLibraryBloc();
  });

  tearDown(() {
    libraryBloc.close();
  });

  Widget buildSubject() {
    return BlocProvider<LibraryBloc>.value(
      value: libraryBloc,
      child: const MaterialApp(home: LibraryListPage()),
    );
  }

  group('LibraryListPage', () {
    testWidgets('shows CircularProgressIndicator when LibraryLoading', (
      tester,
    ) async {
      when(() => libraryBloc.state).thenReturn(const LibraryLoading());

      await tester.pumpWidget(buildSubject());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows error message and Retry button when LibraryError', (
      tester,
    ) async {
      when(
        () => libraryBloc.state,
      ).thenReturn(const LibraryError(message: 'Failed to load library'));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Failed to load library'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Retry'), findsOneWidget);
    });

    testWidgets(
      'shows empty state with Your backlog is empty when LibraryLoaded '
      'with empty list',
      (tester) async {
        when(() => libraryBloc.state).thenReturn(
          const LibraryLoaded(entries: [], total: 0, hasMore: false),
        );

        await tester.pumpWidget(buildSubject());

        expect(find.text('Your backlog is empty.'), findsOneWidget);
        expect(find.text('Add your first game!'), findsOneWidget);
      },
    );

    testWidgets(
      'shows list of library entries when LibraryLoaded with entries',
      (tester) async {
        when(() => libraryBloc.state).thenReturn(
          LibraryLoaded(entries: _sampleEntries, total: 2, hasMore: false),
        );

        await tester.pumpWidget(buildSubject());

        expect(find.text('Elden Ring'), findsOneWidget);
        expect(find.text('Zelda: Tears of the Kingdom'), findsOneWidget);
      },
    );

    testWidgets('shows the IGDB attribution credit', (tester) async {
      when(
        () => libraryBloc.state,
      ).thenReturn(const LibraryLoaded(entries: [], total: 0, hasMore: false));

      await tester.pumpWidget(buildSubject());

      expect(find.text('Game data provided by IGDB.com'), findsOneWidget);
    });

    testWidgets(
      'each entry card shows game title, platform label, status chip',
      (tester) async {
        when(() => libraryBloc.state).thenReturn(
          LibraryLoaded(entries: _sampleEntries, total: 2, hasMore: false),
        );

        await tester.pumpWidget(buildSubject());

        // Game titles.
        expect(find.text('Elden Ring'), findsOneWidget);
        expect(find.text('Zelda: Tears of the Kingdom'), findsOneWidget);

        // Platform labels.
        expect(find.text('PlayStation 5'), findsOneWidget);
        expect(find.text('Nintendo Switch'), findsOneWidget);

        // Status chips (capitalized first letter).
        expect(find.text('Playing'), findsOneWidget);
        expect(find.text('Backlog'), findsOneWidget);
      },
    );

    testWidgets('FABs are present (capture, import, and add)', (tester) async {
      when(
        () => libraryBloc.state,
      ).thenReturn(const LibraryLoaded(entries: [], total: 0, hasMore: false));

      await tester.pumpWidget(buildSubject());

      expect(find.byType(FloatingActionButton), findsNWidgets(3));
      expect(find.byIcon(Icons.auto_awesome), findsOneWidget);
      expect(find.byIcon(Icons.collections), findsOneWidget);

      // The add icon exists both in the FAB and the empty state button,
      // so verify it specifically within a FloatingActionButton.
      expect(
        find.descendant(
          of: find.byType(FloatingActionButton),
          matching: find.byIcon(Icons.add),
        ),
        findsOneWidget,
      );
    });

    testWidgets('DropdownButton is present with filter options', (
      tester,
    ) async {
      when(
        () => libraryBloc.state,
      ).thenReturn(const LibraryLoaded(entries: [], total: 0, hasMore: false));

      await tester.pumpWidget(buildSubject());

      expect(find.byType(DropdownButton<String>), findsOneWidget);

      // Open the dropdown to verify the filter options exist.
      await tester.tap(find.byType(DropdownButton<String>));
      await tester.pumpAndSettle();

      // Each DropdownMenuItem text should be visible in the overlay.
      expect(find.text('All'), findsWidgets);
      expect(find.text('Backlog'), findsWidgets);
      expect(find.text('Playing'), findsWidgets);
      expect(find.text('Paused'), findsOneWidget);
      expect(find.text('Completed'), findsOneWidget);
      expect(find.text('Dropped'), findsOneWidget);
    });

    testWidgets('dispatches LoadLibrary on init', (tester) async {
      when(() => libraryBloc.state).thenReturn(const LibraryInitial());

      await tester.pumpWidget(buildSubject());

      verify(() => libraryBloc.add(const LoadLibrary())).called(1);
    });
  });
}
