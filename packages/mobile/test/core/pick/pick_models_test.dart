import 'package:app/core/library/library_models.dart';
import 'package:app/core/pick/pick_models.dart';
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

/// Builds a full [Pick] JSON map.
Map<String, dynamic> _pickJson({
  String publicId = 'pick-uuid-1',
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

/// Builds a full [PickListItem] JSON map.
Map<String, dynamic> _pickListItemJson({
  String publicId = 'pick-uuid-1',
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

  group('PickMood', () {
    test('has exactly 4 values', () {
      expect(PickMood.values, hasLength(4));
    });

    test('contains all expected values', () {
      expect(
        PickMood.values,
        containsAll([
          PickMood.chill,
          PickMood.focused,
          PickMood.energetic,
          PickMood.adventurous,
        ]),
      );
    });

    test('values have correct names', () {
      expect(PickMood.chill.name, 'chill');
      expect(PickMood.focused.name, 'focused');
      expect(PickMood.energetic.name, 'energetic');
      expect(PickMood.adventurous.name, 'adventurous');
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

  // ── Pick ────────────────────────────────────────────

  group('Pick', () {
    group('fromJson', () {
      test('parses full JSON with all fields', () {
        final json = _pickJson();
        final pick = Pick.fromJson(json);

        expect(pick.publicId, 'pick-uuid-1');
        expect(pick.mood, 'chill');
        expect(pick.availableMinutes, 60);
        expect(pick.mentalEnergy, 'medium');
        expect(pick.context, 'Relaxing after work');
        expect(pick.reasoning, 'A calm exploration game');
        expect(pick.action, 'Continue the main quest');
        expect(pick.createdAt, DateTime.utc(2025, 6, 1, 10));
        expect(pick.updatedAt, DateTime.utc(2025, 6, 1, 10, 30));
        expect(pick.libraryEntry, isNotNull);
        expect(pick.libraryEntry!.publicId, 'entry-uuid-1');
      });

      test('parses JSON with null optional fields', () {
        final json = _pickJson(
          context: null,
          reasoning: null,
          action: null,
          includeLibraryEntry: false,
        );
        final pick = Pick.fromJson(json);

        expect(pick.publicId, 'pick-uuid-1');
        expect(pick.mood, 'chill');
        expect(pick.availableMinutes, 60);
        expect(pick.mentalEnergy, 'medium');
        expect(pick.context, isNull);
        expect(pick.reasoning, isNull);
        expect(pick.action, isNull);
        expect(pick.libraryEntry, isNull);
      });

      test('parses JSON with missing library_entry key', () {
        final json = _pickJson(includeLibraryEntry: false);
        // Explicitly set to null to test the
        // null-check branch.
        json['library_entry'] = null;
        final pick = Pick.fromJson(json);

        expect(pick.libraryEntry, isNull);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different publicId '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(publicId: 'other-uuid'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different mood '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(mood: 'focused'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different '
          'availableMinutes are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(availableMinutes: 120));

        expect(a, isNot(equals(b)));
      });

      test('instances with different mentalEnergy '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(mentalEnergy: 'high'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different context '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(context: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different reasoning '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(reasoning: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different action '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(action: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different createdAt '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(createdAt: '2024-01-01T00:00:00Z'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different updatedAt '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(updatedAt: '2024-01-01T00:00:00Z'));

        expect(a, isNot(equals(b)));
      });

      test('instances with vs without libraryEntry '
          'are not equal', () {
        final a = Pick.fromJson(_pickJson());
        final b = Pick.fromJson(_pickJson(includeLibraryEntry: false));

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final pick = Pick.fromJson(_pickJson());

        expect(pick.props, hasLength(10));
      });
    });
  });

  // ── PickListItem ────────────────────────────────────

  group('PickListItem', () {
    group('fromJson', () {
      test('parses full JSON with all fields', () {
        final json = _pickListItemJson();
        final item = PickListItem.fromJson(json);

        expect(item.publicId, 'pick-uuid-1');
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
        final json = _pickListItemJson(
          reasoning: null,
          action: null,
          includeLibraryEntry: false,
        );
        final item = PickListItem.fromJson(json);

        expect(item.publicId, 'pick-uuid-1');
        expect(item.reasoning, isNull);
        expect(item.action, isNull);
        expect(item.libraryEntry, isNull);
      });

      test('parses JSON with null library_entry '
          'value', () {
        final json = _pickListItemJson(includeLibraryEntry: false);
        json['library_entry'] = null;
        final item = PickListItem.fromJson(json);

        expect(item.libraryEntry, isNull);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(_pickListItemJson());

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different publicId '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(
          _pickListItemJson(publicId: 'other-uuid'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different mood '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(_pickListItemJson(mood: 'chill'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different '
          'availableMinutes are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(
          _pickListItemJson(availableMinutes: 30),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different mentalEnergy '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(_pickListItemJson(mentalEnergy: 'low'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different reasoning '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(
          _pickListItemJson(reasoning: 'Different'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with different action '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(_pickListItemJson(action: 'Different'));

        expect(a, isNot(equals(b)));
      });

      test('instances with different createdAt '
          'are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(
          _pickListItemJson(createdAt: '2024-01-01T00:00:00Z'),
        );

        expect(a, isNot(equals(b)));
      });

      test('instances with vs without '
          'libraryEntry are not equal', () {
        final a = PickListItem.fromJson(_pickListItemJson());
        final b = PickListItem.fromJson(
          _pickListItemJson(includeLibraryEntry: false),
        );

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final item = PickListItem.fromJson(_pickListItemJson());

        expect(item.props, hasLength(8));
      });
    });
  });

  // ── PickListResponse ────────────────────────────────

  group('PickListResponse', () {
    group('fromJson', () {
      test('parses JSON with items', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[
            _pickListItemJson(),
            _pickListItemJson(
              publicId: 'pick-uuid-2',
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
        final response = PickListResponse.fromJson(json);

        expect(response.items, hasLength(2));
        expect(response.total, 10);
        expect(response.items[0].publicId, 'pick-uuid-1');
        expect(response.items[1].publicId, 'pick-uuid-2');
      });

      test('parses JSON with empty items', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        };
        final response = PickListResponse.fromJson(json);

        expect(response.items, isEmpty);
        expect(response.total, 0);
      });
    });

    group('Equatable', () {
      test('equal instances are equal', () {
        final json = <String, dynamic>{
          'items': <Map<String, dynamic>>[_pickListItemJson()],
          'total': 1,
        };
        final a = PickListResponse.fromJson(json);
        final b = PickListResponse.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances with different total '
          'are not equal', () {
        final a = PickListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 5,
        });
        final b = PickListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 10,
        });

        expect(a, isNot(equals(b)));
      });

      test('instances with different items '
          'are not equal', () {
        final a = PickListResponse.fromJson(<String, dynamic>{
          'items': <Map<String, dynamic>>[_pickListItemJson()],
          'total': 1,
        });
        final b = PickListResponse.fromJson(<String, dynamic>{
          'items': <Map<String, dynamic>>[
            _pickListItemJson(publicId: 'other-uuid'),
          ],
          'total': 1,
        });

        expect(a, isNot(equals(b)));
      });
    });

    group('props', () {
      test('contains all fields', () {
        final response = PickListResponse.fromJson(const <String, dynamic>{
          'items': <Map<String, dynamic>>[],
          'total': 0,
        });

        expect(response.props, hasLength(2));
      });
    });
  });
}
