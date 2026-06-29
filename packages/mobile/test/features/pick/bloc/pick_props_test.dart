import 'package:app/core/library/library_models.dart';
import 'package:app/core/pick/pick_models.dart';
import 'package:app/features/pick/bloc/pick_bloc.dart';
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

final _pick = Pick(
  publicId: 'pick-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
  updatedAt: _now,
);

final _listItem = PickListItem(
  publicId: 'pick-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
);

void main() {
  group('PickEvent', () {
    test('CreatePick supports value equality and props', () {
      const a = CreatePick(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'after work',
      );
      const b = CreatePick(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'after work',
      );
      expect(a, b);
      expect(a.props, ['chill', 60, 'medium', 2, 'after work']);
    });

    test('CreatePick uses default count and null context', () {
      const a = CreatePick(
        mood: 'hype',
        availableMinutes: 30,
        mentalEnergy: 'high',
      );
      expect(a.count, 1);
      expect(a.context, isNull);
      expect(a.props, ['hype', 30, 'high', 1, null]);
    });

    test('CreatePick differs when fields differ', () {
      const a = CreatePick(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      );
      const b = CreatePick(
        mood: 'hype',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      );
      expect(a, isNot(b));
    });

    test('AcceptPick supports value equality and props', () {
      const a = AcceptPick(publicId: 'l-1');
      const b = AcceptPick(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1', null]);
      expect(a, isNot(const AcceptPick(publicId: 'l-2')));
    });

    test('AcceptPick differs when recapText differs', () {
      const a = AcceptPick(publicId: 'l-1', recapText: 'go left');
      const b = AcceptPick(publicId: 'l-1', recapText: 'go right');
      expect(a, isNot(b));
      expect(a.props, ['l-1', 'go left']);
    });

    test('GeneratePickRecap supports value equality and props', () {
      const a = GeneratePickRecap(publicId: 'l-1', libraryEntryPublicId: 'e-1');
      const b = GeneratePickRecap(publicId: 'l-1', libraryEntryPublicId: 'e-1');
      expect(a, b);
      expect(a.props, ['l-1', 'e-1', 'quick']);
      expect(
        a,
        isNot(
          const GeneratePickRecap(
            publicId: 'l-1',
            libraryEntryPublicId: 'e-1',
            mode: 'deep',
          ),
        ),
      );
    });

    test('RejectPick supports value equality and props', () {
      const a = RejectPick(publicId: 'l-1');
      const b = RejectPick(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1']);
      expect(a, isNot(const RejectPick(publicId: 'l-2')));
    });

    test('LoadPicks supports value equality and props', () {
      const a = LoadPicks(limit: 10, offset: 5);
      const b = LoadPicks(limit: 10, offset: 5);
      expect(a, b);
      expect(a.props, [10, 5]);
      expect(const LoadPicks().props, [null, null]);
    });

    test('LoadLatestPick supports value equality', () {
      expect(const LoadLatestPick(), const LoadLatestPick());
      expect(const LoadLatestPick().props, isEmpty);
    });
  });

  group('PickState', () {
    test('PickInitial supports value equality', () {
      expect(const PickInitial(), const PickInitial());
      expect(const PickInitial().props, isEmpty);
    });

    test('PickLoading supports value equality', () {
      expect(const PickLoading(), const PickLoading());
      expect(const PickLoading().props, isEmpty);
    });

    test('PickResultsLoaded supports value equality and props', () {
      final a = PickResultsLoaded(results: [_pick]);
      final b = PickResultsLoaded(results: [_pick]);
      expect(a, b);
      expect(a.props, [
        [_pick],
      ]);
    });

    test('PickAccepted supports value equality and props', () {
      final a = PickAccepted(pick: _pick);
      final b = PickAccepted(pick: _pick);
      expect(a, b);
      expect(a.props, [_pick]);
    });

    test('PickRejected supports value equality and props', () {
      final a = PickRejected(pick: _pick);
      final b = PickRejected(pick: _pick);
      expect(a, b);
      expect(a.props, [_pick]);
    });

    test('PickRecapLoading supports value equality and props', () {
      const a = PickRecapLoading(publicId: 'l-1');
      const b = PickRecapLoading(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1']);
      expect(a, isNot(const PickRecapLoading(publicId: 'l-2')));
    });

    test('PickRecapReady supports value equality and props', () {
      const a = PickRecapReady(publicId: 'l-1', recapText: 'go');
      const b = PickRecapReady(publicId: 'l-1', recapText: 'go');
      expect(a, b);
      expect(a.props, ['l-1', 'go']);
      expect(a, isNot(const PickRecapReady(publicId: 'l-1', recapText: 'no')));
    });

    test('PickListLoaded supports value equality and props', () {
      final a = PickListLoaded(picks: [_listItem], total: 1);
      final b = PickListLoaded(picks: [_listItem], total: 1);
      expect(a, b);
      expect(a.props, [
        [_listItem],
        1,
      ]);
    });

    test('LatestPickLoaded supports value equality and props', () {
      final a = LatestPickLoaded(pick: _pick);
      final b = LatestPickLoaded(pick: _pick);
      expect(a, b);
      expect(a.props, [_pick]);
      expect(const LatestPickLoaded().props, [null]);
    });

    test('PickError supports value equality and props', () {
      const a = PickError(message: 'boom');
      const b = PickError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
      expect(a, isNot(const PickError(message: 'other')));
    });
  });
}
