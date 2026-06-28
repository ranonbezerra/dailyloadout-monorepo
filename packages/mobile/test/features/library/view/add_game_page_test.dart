import 'package:app/core/library/library_models.dart';
import 'package:app/core/library/library_repository.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:app/features/library/view/add_game_page.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

class MockLibraryRepository extends Mock implements LibraryRepository {}

class MockLibraryBloc extends MockBloc<LibraryEvent, LibraryState>
    implements LibraryBloc {}

final _now = DateTime.utc(2025, 6);

const _platforms = [
  Platform(id: 1, slug: 'ps5', label: 'PlayStation 5', family: 'playstation'),
  Platform(id: 2, slug: 'pc', label: 'PC', family: 'pc'),
];

final _searchGame = Game(
  publicId: 'game-1',
  slug: 'elden-ring',
  title: 'Elden Ring',
  metadataSource: 'igdb',
  createdAt: _now,
  summary: 'An action RPG by FromSoftware.',
  genres: const ['Action', 'RPG'],
);

void main() {
  setUpAll(() {
    registerFallbackValue(const AddEntry(gamePublicId: 'x', platformIds: []));
  });

  late MockLibraryRepository repository;
  late MockLibraryBloc libraryBloc;

  setUp(() {
    repository = MockLibraryRepository();
    libraryBloc = MockLibraryBloc();
    // Default platform load succeeds.
    when(() => repository.listPlatforms()).thenAnswer((_) async => _platforms);
    when(() => libraryBloc.state).thenReturn(const LibraryInitial());
  });

  tearDown(() {
    libraryBloc.close();
  });

  Widget buildSubject() {
    final router = GoRouter(
      initialLocation: '/library/add',
      routes: [
        GoRoute(
          path: '/library/add',
          builder: (_, __) => AddGamePage(libraryRepository: repository),
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

  group('AddGamePage — search step', () {
    testWidgets('renders search step initially with AppBar title', (
      tester,
    ) async {
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Search Games'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'Search games'), findsOneWidget);
      expect(find.byIcon(Icons.search), findsOneWidget);
    });

    testWidgets('loads platforms on init', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      verify(() => repository.listPlatforms()).called(1);
    });

    testWidgets('still renders search step when platform load fails', (
      tester,
    ) async {
      when(() => repository.listPlatforms()).thenThrow(Exception('boom'));

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      expect(find.text('Search Games'), findsOneWidget);
    });

    testWidgets('empty query does not trigger a search', (tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), '   ');
      await tester.pump(const Duration(milliseconds: 500));

      verifyNever(() => repository.searchGames(any()));
    });

    testWidgets('typing a query searches and shows results after debounce', (
      tester,
    ) async {
      when(
        () => repository.searchGames('elden'),
      ).thenAnswer((_) async => [_searchGame]);

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'elden');
      // Wait past the 400ms debounce.
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();

      verify(() => repository.searchGames('elden')).called(1);
      expect(find.text('Elden Ring'), findsOneWidget);
      expect(find.text('Action, RPG'), findsOneWidget);
      // The "Create manually" affordance is shown when query is non-empty.
      expect(find.text('Create manually'), findsOneWidget);
    });

    testWidgets('search failure leaves results empty without crashing', (
      tester,
    ) async {
      when(
        () => repository.searchGames('zelda'),
      ).thenThrow(Exception('network'));

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'zelda');
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();

      expect(find.text('Elden Ring'), findsNothing);
      // Create manually still available since query is non-empty.
      expect(find.text('Create manually'), findsOneWidget);
    });
  });

  group('AddGamePage — details step (selected game)', () {
    Future<void> selectGame(WidgetTester tester) async {
      when(
        () => repository.searchGames('elden'),
      ).thenAnswer((_) async => [_searchGame]);

      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'elden');
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Elden Ring'));
      await tester.pumpAndSettle();
    }

    testWidgets('selecting a game shows the details step', (tester) async {
      await selectGame(tester);

      expect(find.text('Add to Library'), findsWidgets);
      expect(find.text('An action RPG by FromSoftware.'), findsOneWidget);
      // Platforms are now a multi-select of FilterChips.
      expect(find.byType(FilterChip), findsNWidgets(2));
      expect(find.byType(DropdownButtonFormField<String>), findsOneWidget);
      expect(
        find.widgetWithText(TextFormField, 'Notes (optional)'),
        findsOneWidget,
      );
    });

    testWidgets('details step shows platform options from repository', (
      tester,
    ) async {
      await selectGame(tester);

      // Each platform from the repository is rendered as a FilterChip.
      expect(find.widgetWithText(FilterChip, 'PlayStation 5'), findsOneWidget);
      expect(find.widgetWithText(FilterChip, 'PC'), findsOneWidget);
    });

    testWidgets('can select multiple platforms', (tester) async {
      await selectGame(tester);

      // The first platform (PlayStation 5) is selected by default; also
      // select PC so two platforms are submitted.
      await tester.tap(find.widgetWithText(FilterChip, 'PC'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pumpAndSettle();

      verify(
        () => libraryBloc.add(
          const AddEntry(gamePublicId: 'game-1', platformIds: [1, 2]),
        ),
      ).called(1);
    });

    testWidgets('details step shows status options', (tester) async {
      await selectGame(tester);

      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();

      expect(find.text('Backlog'), findsWidgets);
      expect(find.text('Playing'), findsWidgets);
      expect(find.text('Completed'), findsWidgets);
    });

    testWidgets('back from details step returns to search step', (
      tester,
    ) async {
      await selectGame(tester);

      expect(find.text('Add to Library'), findsWidgets);

      await tester.tap(find.byIcon(Icons.arrow_back));
      await tester.pumpAndSettle();

      expect(find.text('Search Games'), findsOneWidget);
    });

    testWidgets('submit dispatches AddEntry and navigates to /library', (
      tester,
    ) async {
      await selectGame(tester);

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Notes (optional)'),
        'Loving it',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pumpAndSettle();

      verify(
        () => libraryBloc.add(
          const AddEntry(
            gamePublicId: 'game-1',
            platformIds: [1],
            notes: 'Loving it',
          ),
        ),
      ).called(1);
      expect(find.text('Library stub'), findsOneWidget);
    });

    testWidgets('submit with empty notes passes null notes', (tester) async {
      await selectGame(tester);

      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pumpAndSettle();

      verify(
        () => libraryBloc.add(
          const AddEntry(gamePublicId: 'game-1', platformIds: [1]),
        ),
      ).called(1);
    });
  });

  group('AddGamePage — manual creation', () {
    Future<void> openManual(WidgetTester tester) async {
      await tester.pumpWidget(buildSubject());
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'My Indie Game');
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Create manually'));
      await tester.pumpAndSettle();
    }

    testWidgets('manual creation shows a title TextFormField', (tester) async {
      when(() => repository.searchGames(any())).thenAnswer((_) async => []);

      await openManual(tester);

      expect(find.widgetWithText(TextFormField, 'Game title'), findsOneWidget);
    });

    testWidgets('manual submit with empty title does nothing', (tester) async {
      when(() => repository.searchGames(any())).thenAnswer((_) async => []);

      await openManual(tester);

      // Leave the title empty.
      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pumpAndSettle();

      verifyNever(
        () => repository.createGame(
          slug: any(named: 'slug'),
          title: any(named: 'title'),
        ),
      );
      verifyNever(() => libraryBloc.add(any()));
    });

    testWidgets('manual submit creates game, dispatches AddEntry, navigates', (
      tester,
    ) async {
      when(() => repository.searchGames(any())).thenAnswer((_) async => []);
      when(
        () => repository.createGame(
          slug: 'my-indie-game',
          title: 'My Indie Game',
        ),
      ).thenAnswer(
        (_) async => Game(
          publicId: 'created-1',
          slug: 'my-indie-game',
          title: 'My Indie Game',
          metadataSource: 'manual',
          createdAt: _now,
        ),
      );

      await openManual(tester);

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Game title'),
        'My Indie Game',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pumpAndSettle();

      verify(
        () => repository.createGame(
          slug: 'my-indie-game',
          title: 'My Indie Game',
        ),
      ).called(1);
      verify(
        () => libraryBloc.add(
          const AddEntry(gamePublicId: 'created-1', platformIds: [1]),
        ),
      ).called(1);
      expect(find.text('Library stub'), findsOneWidget);
    });

    testWidgets('createGame failure shows an error SnackBar', (tester) async {
      when(() => repository.searchGames(any())).thenAnswer((_) async => []);
      when(
        () => repository.createGame(
          slug: any(named: 'slug'),
          title: any(named: 'title'),
        ),
      ).thenThrow(Exception('create failed'));

      await openManual(tester);

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Game title'),
        'My Indie Game',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Add to Library'));
      await tester.pump();
      await tester.pump();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.textContaining('Failed to add game'), findsOneWidget);
    });
  });
}
