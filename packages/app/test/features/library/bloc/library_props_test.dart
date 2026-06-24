import 'package:app/core/library/library_models.dart';
import 'package:app/features/library/bloc/library_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

final _now = DateTime.utc(2025, 6);

const _platform = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'sony');

final _game = Game(
  publicId: 'game-001',
  slug: 'elden-ring',
  title: 'Elden Ring',
  metadataSource: 'igdb',
  createdAt: _now,
);

final _entry = LibraryEntry(
  publicId: 'lib-001',
  game: _game,
  platform: _platform,
  status: 'playing',
  createdAt: _now,
  updatedAt: _now,
);

void main() {
  group('LibraryEvent', () {
    test('LoadLibrary supports value equality and props', () {
      const a = LoadLibrary(status: 'backlog', limit: 10, offset: 0);
      const b = LoadLibrary(status: 'backlog', limit: 10, offset: 0);
      expect(a, b);
      expect(a.props, ['backlog', 10, 0]);
      expect(const LoadLibrary().props, [null, null, null]);
      expect(a, isNot(const LoadLibrary(status: 'playing')));
    });

    test('AddEntry supports value equality and props', () {
      const a = AddEntry(
        gamePublicId: 'g-1',
        platformId: 1,
        status: 'playing',
        notes: 'fun',
      );
      const b = AddEntry(
        gamePublicId: 'g-1',
        platformId: 1,
        status: 'playing',
        notes: 'fun',
      );
      expect(a, b);
      expect(a.props, ['g-1', 1, 'playing', 'fun']);
    });

    test('AddEntry uses default status and null notes', () {
      const a = AddEntry(gamePublicId: 'g-1', platformId: 2);
      expect(a.status, 'backlog');
      expect(a.notes, isNull);
      expect(a.props, ['g-1', 2, 'backlog', null]);
    });

    test('UpdateEntry supports value equality and props', () {
      const a = UpdateEntry(publicId: 'e-1', status: 'completed', notes: 'x');
      const b = UpdateEntry(publicId: 'e-1', status: 'completed', notes: 'x');
      expect(a, b);
      expect(a.props, ['e-1', 'completed', 'x']);
      expect(const UpdateEntry(publicId: 'e-1').props, ['e-1', null, null]);
    });

    test('DeleteEntry supports value equality and props', () {
      const a = DeleteEntry(publicId: 'e-1');
      const b = DeleteEntry(publicId: 'e-1');
      expect(a, b);
      expect(a.props, ['e-1']);
      expect(a, isNot(const DeleteEntry(publicId: 'e-2')));
    });

    test('SearchGames supports value equality and props', () {
      const a = SearchGames(query: 'elden');
      const b = SearchGames(query: 'elden');
      expect(a, b);
      expect(a.props, ['elden']);
      expect(a, isNot(const SearchGames(query: 'zelda')));
    });

    test('CreateGame supports value equality and props', () {
      const a = CreateGame(slug: 'elden-ring', title: 'Elden Ring');
      const b = CreateGame(slug: 'elden-ring', title: 'Elden Ring');
      expect(a, b);
      expect(a.props, ['elden-ring', 'Elden Ring']);
    });
  });

  group('LibraryState', () {
    test('LibraryInitial supports value equality', () {
      expect(const LibraryInitial(), const LibraryInitial());
      expect(const LibraryInitial().props, isEmpty);
    });

    test('LibraryLoading supports value equality', () {
      expect(const LibraryLoading(), const LibraryLoading());
      expect(const LibraryLoading().props, isEmpty);
    });

    test('LibraryLoaded supports value equality and props', () {
      final a = LibraryLoaded(entries: [_entry], total: 1, hasMore: false);
      final b = LibraryLoaded(entries: [_entry], total: 1, hasMore: false);
      expect(a, b);
      expect(a.props, [
        [_entry],
        1,
        false,
      ]);
      expect(
        a,
        isNot(LibraryLoaded(entries: [_entry], total: 1, hasMore: true)),
      );
    });

    test('LibraryError supports value equality and props', () {
      const a = LibraryError(message: 'boom');
      const b = LibraryError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
      expect(a, isNot(const LibraryError(message: 'other')));
    });
  });
}
