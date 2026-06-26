import 'package:app/core/library/library_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Platform', () {
    test('fromJson parses valid JSON', () {
      final json = <String, dynamic>{
        'id': 48,
        'slug': 'ps5',
        'label': 'PlayStation 5',
        'family': 'PlayStation',
      };

      final platform = Platform.fromJson(json);

      expect(platform.id, equals(48));
      expect(platform.slug, equals('ps5'));
      expect(platform.label, equals('PlayStation 5'));
      expect(platform.family, equals('PlayStation'));
    });

    test('Equatable: equal instances are equal', () {
      const a = Platform(
        id: 1,
        slug: 'switch',
        label: 'Switch',
        family: 'Nintendo',
      );
      const b = Platform(
        id: 1,
        slug: 'switch',
        label: 'Switch',
        family: 'Nintendo',
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      const a = Platform(id: 1, slug: 'ps5', label: 'PS5', family: 'PS');
      const b = Platform(id: 2, slug: 'xbox', label: 'Xbox', family: 'MS');

      expect(a, isNot(equals(b)));
    });
  });

  group('Game', () {
    test('fromJson parses full fields', () {
      final json = <String, dynamic>{
        'public_id': 'game-001',
        'slug': 'elden-ring',
        'title': 'Elden Ring',
        'igdb_id': 119133,
        'summary': 'An action RPG by FromSoftware.',
        'cover_url': 'https://images.igdb.com/cover.jpg',
        'first_release_date': '2022-02-25T00:00:00Z',
        'genres': ['RPG', 'Action'],
        'metadata_source': 'igdb',
        'created_at': '2025-01-01T00:00:00Z',
      };

      final game = Game.fromJson(json);

      expect(game.publicId, equals('game-001'));
      expect(game.slug, equals('elden-ring'));
      expect(game.title, equals('Elden Ring'));
      expect(game.igdbId, equals(119133));
      expect(game.summary, equals('An action RPG by FromSoftware.'));
      expect(game.coverUrl, equals('https://images.igdb.com/cover.jpg'));
      expect(game.firstReleaseDate, equals(DateTime.utc(2022, 2, 25)));
      expect(game.genres, equals(['RPG', 'Action']));
      expect(game.metadataSource, equals('igdb'));
      expect(game.createdAt, equals(DateTime.utc(2025)));
    });

    test('fromJson parses minimal fields with nullable fields as null', () {
      final json = <String, dynamic>{
        'public_id': 'game-002',
        'slug': 'custom-game',
        'title': 'Custom Game',
        'igdb_id': null,
        'summary': null,
        'cover_url': null,
        'first_release_date': null,
        'genres': null,
        'metadata_source': 'manual',
        'created_at': '2025-06-01T00:00:00Z',
      };

      final game = Game.fromJson(json);

      expect(game.igdbId, isNull);
      expect(game.summary, isNull);
      expect(game.coverUrl, isNull);
      expect(game.firstReleaseDate, isNull);
      expect(game.genres, isNull);
      expect(game.metadataSource, equals('manual'));
    });

    test('Equatable: equal instances are equal', () {
      final createdAt = DateTime.utc(2025);
      final a = Game(
        publicId: 'g1',
        slug: 'slug',
        title: 'Title',
        metadataSource: 'igdb',
        createdAt: createdAt,
      );
      final b = Game(
        publicId: 'g1',
        slug: 'slug',
        title: 'Title',
        metadataSource: 'igdb',
        createdAt: createdAt,
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final createdAt = DateTime.utc(2025);
      final a = Game(
        publicId: 'g1',
        slug: 'a',
        title: 'A',
        metadataSource: 'igdb',
        createdAt: createdAt,
      );
      final b = Game(
        publicId: 'g2',
        slug: 'b',
        title: 'B',
        metadataSource: 'igdb',
        createdAt: createdAt,
      );

      expect(a, isNot(equals(b)));
    });
  });

  group('LibraryEntry', () {
    Map<String, dynamic> buildFullEntryJson() {
      return <String, dynamic>{
        'public_id': 'entry-001',
        'game': <String, dynamic>{
          'public_id': 'game-001',
          'slug': 'elden-ring',
          'title': 'Elden Ring',
          'igdb_id': 119133,
          'summary': 'An action RPG.',
          'cover_url': 'https://cover.jpg',
          'first_release_date': '2022-02-25T00:00:00Z',
          'genres': ['RPG'],
          'metadata_source': 'igdb',
          'created_at': '2025-01-01T00:00:00Z',
        },
        'platform': <String, dynamic>{
          'id': 48,
          'slug': 'ps5',
          'label': 'PS5',
          'family': 'PlayStation',
        },
        'status': 'playing',
        'acquired_at': '2025-03-01T00:00:00Z',
        'last_played_at': '2025-06-15T20:00:00Z',
        'mission_next_action': 'Beat Margit',
        'notes': 'Love this game',
        'created_at': '2025-01-01T00:00:00Z',
        'updated_at': '2025-06-15T20:00:00Z',
      };
    }

    test('fromJson parses full fields with nested Game and Platform', () {
      final json = buildFullEntryJson();

      final entry = LibraryEntry.fromJson(json);

      expect(entry.publicId, equals('entry-001'));
      expect(entry.game.title, equals('Elden Ring'));
      expect(entry.platform.slug, equals('ps5'));
      expect(entry.status, equals('playing'));
      expect(entry.acquiredAt, equals(DateTime.utc(2025, 3)));
      expect(entry.lastPlayedAt, equals(DateTime.utc(2025, 6, 15, 20)));
      expect(entry.missionNextAction, equals('Beat Margit'));
      expect(entry.notes, equals('Love this game'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'entry-002',
        'game': <String, dynamic>{
          'public_id': 'game-002',
          'slug': 'custom',
          'title': 'Custom',
          'igdb_id': null,
          'summary': null,
          'cover_url': null,
          'first_release_date': null,
          'genres': null,
          'metadata_source': 'manual',
          'created_at': '2025-01-01T00:00:00Z',
        },
        'platform': <String, dynamic>{
          'id': 1,
          'slug': 'pc',
          'label': 'PC',
          'family': 'PC',
        },
        'status': 'backlog',
        'acquired_at': null,
        'last_played_at': null,
        'mission_next_action': null,
        'notes': null,
        'created_at': '2025-06-01T00:00:00Z',
        'updated_at': '2025-06-01T00:00:00Z',
      };

      final entry = LibraryEntry.fromJson(json);

      expect(entry.acquiredAt, isNull);
      expect(entry.lastPlayedAt, isNull);
      expect(entry.missionNextAction, isNull);
      expect(entry.notes, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = buildFullEntryJson();
      final a = LibraryEntry.fromJson(json);
      final b = LibraryEntry.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildFullEntryJson();
      final jsonB = Map<String, dynamic>.from(jsonA)
        ..['public_id'] = 'entry-999';

      final a = LibraryEntry.fromJson(jsonA);
      final b = LibraryEntry.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  group('LibraryPlatformState', () {
    Map<String, dynamic> buildFullStateJson({String publicId = 'entry-001'}) {
      return <String, dynamic>{
        'public_id': publicId,
        'platform': <String, dynamic>{
          'id': 48,
          'slug': 'ps5',
          'label': 'PS5',
          'family': 'PlayStation',
        },
        'status': 'playing',
        'acquired_at': '2025-03-01T00:00:00Z',
        'last_played_at': '2025-06-15T20:00:00Z',
        'mission_next_action': 'Beat Margit',
        'notes': 'Love this game',
        'created_at': '2025-01-01T00:00:00Z',
        'updated_at': '2025-06-15T20:00:00Z',
      };
    }

    test('fromJson parses full fields with nested Platform', () {
      final state = LibraryPlatformState.fromJson(buildFullStateJson());

      expect(state.publicId, equals('entry-001'));
      expect(state.platform.slug, equals('ps5'));
      expect(state.status, equals('playing'));
      expect(state.acquiredAt, equals(DateTime.utc(2025, 3)));
      expect(state.lastPlayedAt, equals(DateTime.utc(2025, 6, 15, 20)));
      expect(state.missionNextAction, equals('Beat Margit'));
      expect(state.notes, equals('Love this game'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'entry-002',
        'platform': <String, dynamic>{
          'id': 1,
          'slug': 'pc',
          'label': 'PC',
          'family': 'PC',
        },
        'status': 'backlog',
        'acquired_at': null,
        'last_played_at': null,
        'mission_next_action': null,
        'notes': null,
        'created_at': '2025-06-01T00:00:00Z',
        'updated_at': '2025-06-01T00:00:00Z',
      };

      final state = LibraryPlatformState.fromJson(json);

      expect(state.acquiredAt, isNull);
      expect(state.lastPlayedAt, isNull);
      expect(state.missionNextAction, isNull);
      expect(state.notes, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final a = LibraryPlatformState.fromJson(buildFullStateJson());
      final b = LibraryPlatformState.fromJson(buildFullStateJson());

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different entry ids are not equal', () {
      final a = LibraryPlatformState.fromJson(buildFullStateJson());
      final b = LibraryPlatformState.fromJson(
        buildFullStateJson(publicId: 'entry-999'),
      );

      expect(a, isNot(equals(b)));
    });
  });

  group('LibraryGameGroup', () {
    Map<String, dynamic> buildGroupJson() {
      return <String, dynamic>{
        'game': <String, dynamic>{
          'public_id': 'game-001',
          'slug': 'elden-ring',
          'title': 'Elden Ring',
          'igdb_id': null,
          'summary': null,
          'cover_url': null,
          'first_release_date': null,
          'genres': ['RPG'],
          'metadata_source': 'igdb',
          'created_at': '2025-01-01T00:00:00Z',
        },
        'platforms': <Map<String, dynamic>>[
          <String, dynamic>{
            'public_id': 'entry-ps5',
            'platform': <String, dynamic>{
              'id': 48,
              'slug': 'ps5',
              'label': 'PS5',
              'family': 'PlayStation',
            },
            'status': 'playing',
            'acquired_at': null,
            'last_played_at': null,
            'mission_next_action': null,
            'notes': null,
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z',
          },
          <String, dynamic>{
            'public_id': 'entry-pc',
            'platform': <String, dynamic>{
              'id': 6,
              'slug': 'pc',
              'label': 'PC',
              'family': 'PC',
            },
            'status': 'backlog',
            'acquired_at': null,
            'last_played_at': null,
            'mission_next_action': null,
            'notes': null,
            'created_at': '2025-01-01T00:00:00Z',
            'updated_at': '2025-01-01T00:00:00Z',
          },
        ],
      };
    }

    test('fromJson parses one game with multiple platform states', () {
      final group = LibraryGameGroup.fromJson(buildGroupJson());

      expect(group.game.title, equals('Elden Ring'));
      expect(group.platforms, hasLength(2));
      expect(group.platforms.first.publicId, equals('entry-ps5'));
      expect(group.platforms.first.platform.slug, equals('ps5'));
      expect(group.platforms.last.publicId, equals('entry-pc'));
      expect(group.platforms.last.status, equals('backlog'));
    });

    test('Equatable: equal instances are equal', () {
      final a = LibraryGameGroup.fromJson(buildGroupJson());
      final b = LibraryGameGroup.fromJson(buildGroupJson());

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('LibraryListResponse (grouped)', () {
    test('fromJson parses valid response with grouped items', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[
          <String, dynamic>{
            'game': <String, dynamic>{
              'public_id': 'game-001',
              'slug': 'zelda',
              'title': 'Zelda',
              'igdb_id': null,
              'summary': null,
              'cover_url': null,
              'first_release_date': null,
              'genres': null,
              'metadata_source': 'manual',
              'created_at': '2025-01-01T00:00:00Z',
            },
            'platforms': <Map<String, dynamic>>[
              <String, dynamic>{
                'public_id': 'entry-001',
                'platform': <String, dynamic>{
                  'id': 1,
                  'slug': 'switch',
                  'label': 'Switch',
                  'family': 'Nintendo',
                },
                'status': 'playing',
                'acquired_at': null,
                'last_played_at': null,
                'mission_next_action': null,
                'notes': null,
                'created_at': '2025-01-01T00:00:00Z',
                'updated_at': '2025-01-01T00:00:00Z',
              },
            ],
          },
        ],
        'total': 1,
        'limit': 20,
        'offset': 0,
      };

      final response = LibraryListResponse.fromJson(json);

      expect(response.items, hasLength(1));
      expect(response.items.first.game.title, equals('Zelda'));
      expect(response.items.first.platforms, hasLength(1));
      expect(
        response.items.first.platforms.first.publicId,
        equals('entry-001'),
      );
      expect(response.total, equals(1));
      expect(response.limit, equals(20));
      expect(response.offset, equals(0));
    });

    test('fromJson parses empty items list', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
        'limit': 20,
        'offset': 0,
      };

      final response = LibraryListResponse.fromJson(json);

      expect(response.items, isEmpty);
      expect(response.total, equals(0));
    });
  });
}
