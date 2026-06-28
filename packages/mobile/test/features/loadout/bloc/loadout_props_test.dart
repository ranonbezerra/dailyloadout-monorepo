import 'package:app/core/library/library_models.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:app/features/loadout/bloc/loadout_bloc.dart';
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

final _loadout = Loadout(
  publicId: 'loadout-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
  updatedAt: _now,
);

final _listItem = LoadoutListItem(
  publicId: 'loadout-001',
  mood: 'chill',
  availableMinutes: 60,
  mentalEnergy: 'medium',
  reasoning: 'A relaxing session.',
  action: 'accepted',
  libraryEntry: _entry,
  createdAt: _now,
);

void main() {
  group('LoadoutEvent', () {
    test('CreateLoadout supports value equality and props', () {
      const a = CreateLoadout(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'after work',
      );
      const b = CreateLoadout(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
        count: 2,
        context: 'after work',
      );
      expect(a, b);
      expect(a.props, ['chill', 60, 'medium', 2, 'after work']);
    });

    test('CreateLoadout uses default count and null context', () {
      const a = CreateLoadout(
        mood: 'hype',
        availableMinutes: 30,
        mentalEnergy: 'high',
      );
      expect(a.count, 1);
      expect(a.context, isNull);
      expect(a.props, ['hype', 30, 'high', 1, null]);
    });

    test('CreateLoadout differs when fields differ', () {
      const a = CreateLoadout(
        mood: 'chill',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      );
      const b = CreateLoadout(
        mood: 'hype',
        availableMinutes: 60,
        mentalEnergy: 'medium',
      );
      expect(a, isNot(b));
    });

    test('AcceptLoadout supports value equality and props', () {
      const a = AcceptLoadout(publicId: 'l-1');
      const b = AcceptLoadout(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1', null]);
      expect(a, isNot(const AcceptLoadout(publicId: 'l-2')));
    });

    test('AcceptLoadout differs when briefingText differs', () {
      const a = AcceptLoadout(publicId: 'l-1', briefingText: 'go left');
      const b = AcceptLoadout(publicId: 'l-1', briefingText: 'go right');
      expect(a, isNot(b));
      expect(a.props, ['l-1', 'go left']);
    });

    test('GenerateLoadoutBriefing supports value equality and props', () {
      const a = GenerateLoadoutBriefing(
        publicId: 'l-1',
        libraryEntryPublicId: 'e-1',
      );
      const b = GenerateLoadoutBriefing(
        publicId: 'l-1',
        libraryEntryPublicId: 'e-1',
      );
      expect(a, b);
      expect(a.props, ['l-1', 'e-1', 'quick']);
      expect(
        a,
        isNot(
          const GenerateLoadoutBriefing(
            publicId: 'l-1',
            libraryEntryPublicId: 'e-1',
            mode: 'deep',
          ),
        ),
      );
    });

    test('RejectLoadout supports value equality and props', () {
      const a = RejectLoadout(publicId: 'l-1');
      const b = RejectLoadout(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1']);
      expect(a, isNot(const RejectLoadout(publicId: 'l-2')));
    });

    test('LoadLoadouts supports value equality and props', () {
      const a = LoadLoadouts(limit: 10, offset: 5);
      const b = LoadLoadouts(limit: 10, offset: 5);
      expect(a, b);
      expect(a.props, [10, 5]);
      expect(const LoadLoadouts().props, [null, null]);
    });

    test('LoadLatestLoadout supports value equality', () {
      expect(const LoadLatestLoadout(), const LoadLatestLoadout());
      expect(const LoadLatestLoadout().props, isEmpty);
    });
  });

  group('LoadoutState', () {
    test('LoadoutInitial supports value equality', () {
      expect(const LoadoutInitial(), const LoadoutInitial());
      expect(const LoadoutInitial().props, isEmpty);
    });

    test('LoadoutLoading supports value equality', () {
      expect(const LoadoutLoading(), const LoadoutLoading());
      expect(const LoadoutLoading().props, isEmpty);
    });

    test('LoadoutResultsLoaded supports value equality and props', () {
      final a = LoadoutResultsLoaded(results: [_loadout]);
      final b = LoadoutResultsLoaded(results: [_loadout]);
      expect(a, b);
      expect(a.props, [
        [_loadout],
      ]);
    });

    test('LoadoutAccepted supports value equality and props', () {
      final a = LoadoutAccepted(loadout: _loadout);
      final b = LoadoutAccepted(loadout: _loadout);
      expect(a, b);
      expect(a.props, [_loadout]);
    });

    test('LoadoutRejected supports value equality and props', () {
      final a = LoadoutRejected(loadout: _loadout);
      final b = LoadoutRejected(loadout: _loadout);
      expect(a, b);
      expect(a.props, [_loadout]);
    });

    test('LoadoutBriefingLoading supports value equality and props', () {
      const a = LoadoutBriefingLoading(publicId: 'l-1');
      const b = LoadoutBriefingLoading(publicId: 'l-1');
      expect(a, b);
      expect(a.props, ['l-1']);
      expect(a, isNot(const LoadoutBriefingLoading(publicId: 'l-2')));
    });

    test('LoadoutBriefingReady supports value equality and props', () {
      const a = LoadoutBriefingReady(publicId: 'l-1', briefingText: 'go');
      const b = LoadoutBriefingReady(publicId: 'l-1', briefingText: 'go');
      expect(a, b);
      expect(a.props, ['l-1', 'go']);
      expect(
        a,
        isNot(const LoadoutBriefingReady(publicId: 'l-1', briefingText: 'no')),
      );
    });

    test('LoadoutListLoaded supports value equality and props', () {
      final a = LoadoutListLoaded(loadouts: [_listItem], total: 1);
      final b = LoadoutListLoaded(loadouts: [_listItem], total: 1);
      expect(a, b);
      expect(a.props, [
        [_listItem],
        1,
      ]);
    });

    test('LatestLoadoutLoaded supports value equality and props', () {
      final a = LatestLoadoutLoaded(loadout: _loadout);
      final b = LatestLoadoutLoaded(loadout: _loadout);
      expect(a, b);
      expect(a.props, [_loadout]);
      expect(const LatestLoadoutLoaded().props, [null]);
    });

    test('LoadoutError supports value equality and props', () {
      const a = LoadoutError(message: 'boom');
      const b = LoadoutError(message: 'boom');
      expect(a, b);
      expect(a.props, ['boom']);
      expect(a, isNot(const LoadoutError(message: 'other')));
    });
  });
}
