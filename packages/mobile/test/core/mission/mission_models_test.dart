import 'package:app/core/mission/mission_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // ── Shared JSON builders ──────────────────────────────────────────

  Map<String, dynamic> buildLibraryEntryJson({String publicId = 'entry-001'}) {
    return <String, dynamic>{
      'public_id': publicId,
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
      'acquired_at': null,
      'last_played_at': null,
      'mission_next_action': null,
      'notes': null,
      'created_at': '2025-01-01T00:00:00Z',
      'updated_at': '2025-01-01T00:00:00Z',
    };
  }

  Map<String, dynamic> buildSessionContextJson() {
    return <String, dynamic>{
      'location': 'Limgrave',
      'next_action': 'Beat Margit',
      'level': '35',
      'current_quest': 'Main Story',
    };
  }

  // ── SessionContext ────────────────────────────────────────────────

  group('SessionContext', () {
    test('fromJson parses full fields', () {
      final json = buildSessionContextJson();

      final ctx = SessionContext.fromJson(json);

      expect(ctx.location, equals('Limgrave'));
      expect(ctx.nextAction, equals('Beat Margit'));
      expect(ctx.level, equals('35'));
      expect(ctx.currentQuest, equals('Main Story'));
    });

    test('fromJson parses with all fields null', () {
      final json = <String, dynamic>{
        'location': null,
        'next_action': null,
        'level': null,
        'current_quest': null,
      };

      final ctx = SessionContext.fromJson(json);

      expect(ctx.location, isNull);
      expect(ctx.nextAction, isNull);
      expect(ctx.level, isNull);
      expect(ctx.currentQuest, isNull);
    });

    test('Equatable: equal instances are equal', () {
      const a = SessionContext(
        location: 'Limgrave',
        nextAction: 'Beat Margit',
        level: '35',
        currentQuest: 'Main Story',
      );
      const b = SessionContext(
        location: 'Limgrave',
        nextAction: 'Beat Margit',
        level: '35',
        currentQuest: 'Main Story',
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      const a = SessionContext(location: 'Limgrave');
      const b = SessionContext(location: 'Caelid');

      expect(a, isNot(equals(b)));
    });
  });

  // ── Mission ──────────────────────────────────────────────────────

  group('Mission', () {
    Map<String, dynamic> buildFullMissionJson() {
      return <String, dynamic>{
        'public_id': 'mission-001',
        'library_entry': buildLibraryEntryJson(),
        'mission_type': 'story',
        'briefing_text': 'Your mission today...',
        'debrief_text': 'Great session!',
        'extracted_state': <String, dynamic>{'boss_defeated': true},
        'ended_via': 'debrief',
        'started_at': '2025-06-20T18:00:00Z',
        'ended_at': '2025-06-20T20:00:00Z',
        'created_at': '2025-06-20T17:55:00Z',
        'updated_at': '2025-06-20T20:05:00Z',
        'last_session_context': buildSessionContextJson(),
      };
    }

    test('fromJson parses full fields', () {
      final json = buildFullMissionJson();

      final mission = Mission.fromJson(json);

      expect(mission.publicId, equals('mission-001'));
      expect(mission.libraryEntry.publicId, equals('entry-001'));
      expect(mission.missionType, equals('story'));
      expect(mission.briefingText, equals('Your mission today...'));
      expect(mission.debriefText, equals('Great session!'));
      expect(
        mission.extractedState,
        equals(<String, dynamic>{'boss_defeated': true}),
      );
      expect(mission.endedVia, equals('debrief'));
      expect(mission.startedAt, equals(DateTime.utc(2025, 6, 20, 18)));
      expect(mission.endedAt, equals(DateTime.utc(2025, 6, 20, 20)));
      expect(mission.createdAt, equals(DateTime.utc(2025, 6, 20, 17, 55)));
      expect(mission.updatedAt, equals(DateTime.utc(2025, 6, 20, 20, 5)));
      expect(mission.lastSessionContext, isA<SessionContext>());
      expect(mission.lastSessionContext?.location, equals('Limgrave'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'mission-002',
        'library_entry': buildLibraryEntryJson(),
        'mission_type': 'freeplay',
        'briefing_text': null,
        'debrief_text': null,
        'extracted_state': null,
        'ended_via': null,
        'started_at': '2025-06-21T10:00:00Z',
        'ended_at': null,
        'created_at': '2025-06-21T09:55:00Z',
        'updated_at': '2025-06-21T10:00:00Z',
        'last_session_context': null,
      };

      final mission = Mission.fromJson(json);

      expect(mission.publicId, equals('mission-002'));
      expect(mission.briefingText, isNull);
      expect(mission.debriefText, isNull);
      expect(mission.extractedState, isNull);
      expect(mission.endedVia, isNull);
      expect(mission.endedAt, isNull);
      expect(mission.lastSessionContext, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = buildFullMissionJson();
      final a = Mission.fromJson(json);
      final b = Mission.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildFullMissionJson();
      final jsonB = Map<String, dynamic>.from(jsonA)
        ..['public_id'] = 'mission-999';

      final a = Mission.fromJson(jsonA);
      final b = Mission.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── MissionListItem ──────────────────────────────────────────────

  group('MissionListItem', () {
    Map<String, dynamic> buildFullListItemJson() {
      return <String, dynamic>{
        'public_id': 'mission-001',
        'library_entry': buildLibraryEntryJson(),
        'mission_type': 'story',
        'ended_via': 'debrief',
        'started_at': '2025-06-20T18:00:00Z',
        'ended_at': '2025-06-20T20:00:00Z',
      };
    }

    test('fromJson parses full fields', () {
      final json = buildFullListItemJson();

      final item = MissionListItem.fromJson(json);

      expect(item.publicId, equals('mission-001'));
      expect(item.libraryEntry.game.title, equals('Elden Ring'));
      expect(item.missionType, equals('story'));
      expect(item.endedVia, equals('debrief'));
      expect(item.startedAt, equals(DateTime.utc(2025, 6, 20, 18)));
      expect(item.endedAt, equals(DateTime.utc(2025, 6, 20, 20)));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'mission-003',
        'library_entry': buildLibraryEntryJson(),
        'mission_type': 'freeplay',
        'ended_via': null,
        'started_at': '2025-06-21T10:00:00Z',
        'ended_at': null,
      };

      final item = MissionListItem.fromJson(json);

      expect(item.endedVia, isNull);
      expect(item.endedAt, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = buildFullListItemJson();
      final a = MissionListItem.fromJson(json);
      final b = MissionListItem.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildFullListItemJson();
      final jsonB = Map<String, dynamic>.from(jsonA)
        ..['public_id'] = 'mission-999';

      final a = MissionListItem.fromJson(jsonA);
      final b = MissionListItem.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── MissionListResponse ──────────────────────────────────────────

  group('MissionListResponse', () {
    test('fromJson parses valid response with items', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[
          <String, dynamic>{
            'public_id': 'mission-001',
            'library_entry': buildLibraryEntryJson(),
            'mission_type': 'story',
            'ended_via': 'debrief',
            'started_at': '2025-06-20T18:00:00Z',
            'ended_at': '2025-06-20T20:00:00Z',
          },
        ],
        'total': 1,
      };

      final response = MissionListResponse.fromJson(json);

      expect(response.items, hasLength(1));
      expect(response.items.first.publicId, equals('mission-001'));
      expect(response.total, equals(1));
    });

    test('fromJson parses empty items list', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };

      final response = MissionListResponse.fromJson(json);

      expect(response.items, isEmpty);
      expect(response.total, equals(0));
    });

    test('Equatable: equal instances are equal', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };
      final a = MissionListResponse.fromJson(json);
      final b = MissionListResponse.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };
      final jsonB = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 5,
      };
      final a = MissionListResponse.fromJson(jsonA);
      final b = MissionListResponse.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── BriefingPreview ──────────────────────────────────────────────

  group('BriefingPreview', () {
    test('fromJson parses full fields', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'briefing_text': 'Welcome back, Tarnished.',
        'last_session_context': buildSessionContextJson(),
      };

      final preview = BriefingPreview.fromJson(json);

      expect(preview.libraryEntry.publicId, equals('entry-001'));
      expect(preview.briefingText, equals('Welcome back, Tarnished.'));
      expect(preview.lastSessionContext, isA<SessionContext>());
      expect(preview.lastSessionContext?.nextAction, equals('Beat Margit'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'briefing_text': null,
        'last_session_context': null,
      };

      final preview = BriefingPreview.fromJson(json);

      expect(preview.briefingText, isNull);
      expect(preview.lastSessionContext, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'briefing_text': 'Brief',
        'last_session_context': buildSessionContextJson(),
      };
      final a = BriefingPreview.fromJson(json);
      final b = BriefingPreview.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final a = BriefingPreview.fromJson(<String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'briefing_text': 'Brief A',
        'last_session_context': null,
      });
      final b = BriefingPreview.fromJson(<String, dynamic>{
        'library_entry': buildLibraryEntryJson(publicId: 'entry-999'),
        'briefing_text': 'Brief B',
        'last_session_context': null,
      });

      expect(a, isNot(equals(b)));
    });
  });
}
