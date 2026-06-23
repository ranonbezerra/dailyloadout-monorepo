import 'package:app/core/library/library_models.dart';
import 'package:app/core/loadout/loadout_models.dart';
import 'package:flutter_test/flutter_test.dart';

/// Builds a minimal [Platform] JSON map.
Map<String, dynamic> _platformJson({
  int id = 1,
  String slug = 'ps5',
  String label = 'PlayStation 5',
  String family = 'playstation',
}) => <String, dynamic>{
  'id': id,
  'slug': slug,
  'label': label,
  'family': family,
};

/// Builds a minimal [Game] JSON map.
Map<String, dynamic> _gameJson({
  String publicId = 'game-uuid-1',
  String slug = 'elden-ring',
  String title = 'Elden Ring',
  String metadataSource = 'igdb',
  String createdAt = '2025-01-01T00:00:00Z',
}) => <String, dynamic>{
  'public_id': publicId,
  'slug': slug,
  'title': title,
  'metadata_source': metadataSource,
  'created_at': createdAt,
};

/// Builds a minimal [LibraryEntry] JSON map.
Map<String, dynamic> _libraryEntryJson({
  String publicId = 'entry-uuid-1',
  String status = 'playing',
  String createdAt = '2025-01-01T00:00:00Z',
  String updatedAt = '2025-01-02T00:00:00Z',
}) => <String, dynamic>{
  'public_id': publicId,
  'game': _gameJson(),
  'platform': _platformJson(),
  'status': status,
  'created_at': createdAt,
  'updated_at': updatedAt,
};

/// Builds a full [Loadout] JSON map.
Map<String, dynamic> _loadoutJson({
  String publicId = 'loadout-uuid-1',
  String mood = 'chill',
  int availableMinutes = 60,
  String mentalEnergy = 'medium',
  String? context = 'Relaxing after work',
  String? reasoning = 'A calm exploration game',
  String? action = 'Continue the main quest',
  String createdAt = '2025-06-01T10:00:00Z',
  String updatedAt = '2025-06-01T10:30:00Z',
  bool includeLibraryEntry = true,
}) => <String, dynamic>{
  'public_id': publicId,
  'mood': mood,
  'available_minutes': availableMinutes,
  'mental_energy': mentalEnergy,
  'context': context,
  'reasoning': reasoning,
  'action': action,
  'created_at': createdAt,
  'updated_at': updatedAt,
  if (includeLibraryEntry) 'library_entry': _libraryEntryJson(),
};

/// Builds a full [LoadoutListItem] JSON map.
Map<String, dynamic> _loadoutListItemJson({
  String publicId = 'loadout-uuid-1',
  String mood = 'focused',
  int availableMinutes = 90,
  String mentalEnergy = 'high',
  String? reasoning = 'A strategic challenge',
  String? action = 'Beat the boss',
  String createdAt = '2025-06-02T14:00:00Z',
  bool includeLibraryEntry = true,
}) => <String, dynamic>{
  'public_id': publicId,
  'mood': mood,
  'available_minutes': availableMinutes,
  'mental_energy': mentalEnergy,
  'reasoning': reasoning,
  'action': action,
  'created_at': createdAt,
  if (includeLibraryEntry) 'library_entry': _libraryEntryJson(),
};

void main() {
  // ── Enums ──────────────────────────────────────────────

  group('LoadoutMood', () {
    test('has exactly 4 values', () {
      expect(LoadoutMood.values, hasLength(4));
    });

    test('contains all expected values', () {
      expect(
        LoadoutMood.values,
        containsAll([
          LoadoutMood.chill,
          LoadoutMood.focused,
          LoadoutMood.energetic,
          LoadoutMood.adventurous,
        ]),
      );
    });

    test('values have correct names', () {
      expect(LoadoutMood.chill.name, 'chill');
      expect(LoadoutMood.focused.name, 'focused');
      expect(LoadoutMood.energetic.name, 'energetic');
      expect(LoadoutMood.adventurous.name, 'adventurous');
    });
  });

  group('MentalEnergy', () {
    test('has exactly 3 values', () {
      expect(MentalEnergy.values, hasLength(3));
    });

    test('contains all expected values', () {
      expect(
        MentalEnergy.values,
        containsAll([MentalEnergy.low, MentalEnergy.medium, MentalEnergy.high]),
      );
    });

    test('values have correct names', () {
      expect(MentalEnergy.low.name, 'low');
      expect(MentalEnergy.medium.name, 'medium');
      expect(MentalEnergy.high.name, 'high');
    });
  });

  // ── Loadout ────────────────────────────────────────────

  group('Loadout', () {
    group('fromJson', () {
      test('parses full JSON with all fields', () {
        final json = _loadoutJson();
        final loadout = Loadout.fromJson(json);

        expect(loadout.publicId, 'loadout-uuid-1');
        expect(loadout.mood, 'chill');
        expect(loadout.availableMinutes, 60);
        expect(loadout.mentalEnergy, 'medium');
        expect(loadout.context, 'Relaxing after work');
        expect(loadout.reasoning, 'A calm exploration game');
        expect(loadout.action, 'Continue the main quest');
        expect(loadout.createdAt, DateTime.utc(2025, 6, 1, 10));
        expect(loadout.updatedAt, DateTime.utc(2025, 6, 1, 10, 30));
        expect(loadout.libraryEntry, isNotNull);
        expect(loadout.libraryEntry!.publicId, 'entry-uuid-1');
      });

      test('parses JSON with null optional fields', () {
        final json = _loadoutJson(
          context: null,
          reasoning: null,
          action: null,
          includeLibraryEntry: false,
        );
        final loadout = Loadout.fromJson(json);

        expect(loadout.publicId, 'loadout-uuid-1');
        expect(loadout.mood, 'chill');
        expect(loadout.availableMinutes, 60);
        expect(loadout.mentalEnergy, 'medium');
        expect(loadout.context, isNull);
        expect(loadout.reasoning, isNull);
        expect(loadout.action, isNull);
        expect(loadout.libraryEntry, isNull);
      });

      test('parses JSON with missing library_entry key', () {
        final json = _loadoutJson(includeLibraryEntry: false);
        // Explicitly set to null to test the
        // null-check branch.
        json['library_entry'] = null;
        final loadout = Loadout.fromJson(json);

        expect(loadout.libraryEntry, isNull);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different publicId '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(publicId: 'other-uuid'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different mood '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(mood: 'focused'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different '
          'availableMinutes are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(availableMinutes: 120));

        expect(a, isNot(equals(b)));
      });

      test('instances with different mentalEnergy '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(mentalEnergy: 'high'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different context '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(context: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different reasoning '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(reasoning: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different action '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(action: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different createdAt '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(
          _loadoutJson(createdAt: '2024-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different updatedAt '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(
          _loadoutJson(updatedAt: '2024-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with vs without libraryEntry '
          'are not equal', () {
        final a = Loadout.fromJson(_loadoutJson());
        final b = Loadout.fromJson(_loadoutJson(includeLibraryEntry: false));

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final loadout = Loadout.fromJson(_loadoutJson());

        expect(loadout.props, hasLength(10));
      });
    });
  });

  // ── LoadoutListItem ────────────────────────────────────

  group('LoadoutListItem', () {
    group('fromJson', () {
      test('parses full JSON with all fields', () {
        final json = _loadoutListItemJson();
        final item = LoadoutListItem.fromJson(json);

        expect(item.publicId, 'loadout-uuid-1');
        expect(item.mood, 'focused');
        expect(item.availableMinutes, 90);
        expect(item.mentalEnergy, 'high');
        expect(item.reasoning, 'A strategic challenge');
        expect(item.action, 'Beat the boss');
        expect(item.createdAt, DateTime.utc(2025, 6, 2, 14));
        expect(item.libraryEntry, isNotNull);
        expect(item.libraryEntry!.publicId, 'entry-uuid-1');
      });

      test('parses JSON with null optional fields', () {
        final json = _loadoutListItemJson(
          reasoning: null,
          action: null,
          includeLibraryEntry: false,
        );
        final item = LoadoutListItem.fromJson(json);

        expect(item.publicId, 'loadout-uuid-1');
        expect(item.reasoning, isNull);
        expect(item.action, isNull);
        expect(item.libraryEntry, isNull);
      });

      test('parses JSON with null library_entry '
          'value', () {
        final json = _loadoutListItemJson(includeLibraryEntry: false);
        json['library_entry'] = null;
        final item = LoadoutListItem.fromJson(json);

        expect(item.libraryEntry, isNull);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(_loadoutListItemJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different publicId '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(publicId: 'other-uuid'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different mood '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(_loadoutListItemJson(mood: 'chill'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different '
          'availableMinutes are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(availableMinutes: 30),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different mentalEnergy '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(mentalEnergy: 'low'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different reasoning '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(reasoning: 'Different'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different action '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(action: 'Different'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different createdAt '
          'are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(createdAt: '2024-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with vs without '
          'libraryEntry are not equal', () {
        final a = LoadoutListItem.fromJson(_loadoutListItemJson());
        final b = LoadoutListItem.fromJson(
          _loadoutListItemJson(includeLibraryEntry: false),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final item = LoadoutListItem.fromJson(_loadoutListItemJson());

        expect(item.props, hasLength(8));
      });
    });
  });

  // ── LoadoutListResponse ────────────────────────────────

  group('LoadoutListResponse', () {
    group('fromJson', () {
      test('parses JSON with items', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[
            _loadoutListItemJson(),
            _loadoutListItemJson(
              publicId: 'loadout-uuid-2',
              mood: 'energetic',
              availableMinutes: 45,
              mentalEnergy: 'low',
              reasoning: 'Quick fun session',
              action: 'Play a few matches',
              createdAt: '2025-06-03T08:00:00Z',
            ),
          ],
          'total': 10,
        };
        final response = LoadoutListResponse.fromJson(json);

        expect(response.items, hasLength(2));
        expect(response.total, 10);
        expect(response.items[0].publicId, 'loadout-uuid-1');
        expect(response.items[1].publicId, 'loadout-uuid-2');
      });

      test('parses JSON with empty items', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        };
        final response = LoadoutListResponse.fromJson(json);

        expect(response.items, isEmpty);
        expect(response.total, 0);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[_loadoutListItemJson()],
          'total': 1,
        };
        final a = LoadoutListResponse.fromJson(json);
        final b = LoadoutListResponse.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different total '
          'are not equal', () {
        final a = LoadoutListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 5,
        });
        final b = LoadoutListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 10,
        });

        expect(a, isNot(equals(b)));
      });

      test('instances with different items '
          'are not equal', () {
        final a = LoadoutListResponse.fromJson(<String, dynamic>{
          'items': <Map<String, dynamic>>[_loadoutListItemJson()],
          'total': 1,
        });
        final b = LoadoutListResponse.fromJson(<String, dynamic>{
          'items': <Map<String, dynamic>>[
            _loadoutListItemJson(publicId: 'other-uuid'),
          ],
          'total': 1,
        });

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final response = LoadoutListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        });

        expect(response.props, hasLength(2));
      });
    });
  });
}
