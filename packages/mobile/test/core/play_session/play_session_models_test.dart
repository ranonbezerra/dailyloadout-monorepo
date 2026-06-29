import 'package:app/core/play_session/play_session_models.dart';
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
      'play_session_next_action': null,
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

  // ── PlaySession ──────────────────────────────────────────────────────

  group('PlaySession', () {
    Map<String, dynamic> buildFullPlaySessionJson() {
      return <String, dynamic>{
        'public_id': 'playSession-001',
        'library_entry': buildLibraryEntryJson(),
        'play_session_type': 'story',
        'recap_text': 'Your playSession today...',
        'wrap_up_text': 'Great session!',
        'extracted_state': <String, dynamic>{'boss_defeated': true},
        'ended_via': 'wrapUp',
        'started_at': '2025-06-20T18:00:00Z',
        'ended_at': '2025-06-20T20:00:00Z',
        'created_at': '2025-06-20T17:55:00Z',
        'updated_at': '2025-06-20T20:05:00Z',
        'last_session_context': buildSessionContextJson(),
      };
    }

    test('fromJson parses full fields', () {
      final json = buildFullPlaySessionJson();

      final playSession = PlaySession.fromJson(json);

      expect(playSession.publicId, equals('playSession-001'));
      expect(playSession.libraryEntry.publicId, equals('entry-001'));
      expect(playSession.playSessionType, equals('story'));
      expect(playSession.recapText, equals('Your playSession today...'));
      expect(playSession.wrapUpText, equals('Great session!'));
      expect(
        playSession.extractedState,
        equals(<String, dynamic>{'boss_defeated': true}),
      );
      expect(playSession.endedVia, equals('wrapUp'));
      expect(playSession.startedAt, equals(DateTime.utc(2025, 6, 20, 18)));
      expect(playSession.endedAt, equals(DateTime.utc(2025, 6, 20, 20)));
      expect(playSession.createdAt, equals(DateTime.utc(2025, 6, 20, 17, 55)));
      expect(playSession.updatedAt, equals(DateTime.utc(2025, 6, 20, 20, 5)));
      expect(playSession.lastSessionContext, isA<SessionContext>());
      expect(playSession.lastSessionContext?.location, equals('Limgrave'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'playSession-002',
        'library_entry': buildLibraryEntryJson(),
        'play_session_type': 'freeplay',
        'recap_text': null,
        'wrap_up_text': null,
        'extracted_state': null,
        'ended_via': null,
        'started_at': '2025-06-21T10:00:00Z',
        'ended_at': null,
        'created_at': '2025-06-21T09:55:00Z',
        'updated_at': '2025-06-21T10:00:00Z',
        'last_session_context': null,
      };

      final playSession = PlaySession.fromJson(json);

      expect(playSession.publicId, equals('playSession-002'));
      expect(playSession.recapText, isNull);
      expect(playSession.wrapUpText, isNull);
      expect(playSession.extractedState, isNull);
      expect(playSession.endedVia, isNull);
      expect(playSession.endedAt, isNull);
      expect(playSession.lastSessionContext, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = buildFullPlaySessionJson();
      final a = PlaySession.fromJson(json);
      final b = PlaySession.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildFullPlaySessionJson();
      final jsonB = Map<String, dynamic>.from(jsonA)
        ..['public_id'] = 'playSession-999';

      final a = PlaySession.fromJson(jsonA);
      final b = PlaySession.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── PlaySessionListItem ──────────────────────────────────────────────

  group('PlaySessionListItem', () {
    Map<String, dynamic> buildFullListItemJson() {
      return <String, dynamic>{
        'public_id': 'playSession-001',
        'library_entry': buildLibraryEntryJson(),
        'play_session_type': 'story',
        'ended_via': 'wrapUp',
        'started_at': '2025-06-20T18:00:00Z',
        'ended_at': '2025-06-20T20:00:00Z',
      };
    }

    test('fromJson parses full fields', () {
      final json = buildFullListItemJson();

      final item = PlaySessionListItem.fromJson(json);

      expect(item.publicId, equals('playSession-001'));
      expect(item.libraryEntry.game.title, equals('Elden Ring'));
      expect(item.playSessionType, equals('story'));
      expect(item.endedVia, equals('wrapUp'));
      expect(item.startedAt, equals(DateTime.utc(2025, 6, 20, 18)));
      expect(item.endedAt, equals(DateTime.utc(2025, 6, 20, 20)));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'public_id': 'playSession-003',
        'library_entry': buildLibraryEntryJson(),
        'play_session_type': 'freeplay',
        'ended_via': null,
        'started_at': '2025-06-21T10:00:00Z',
        'ended_at': null,
      };

      final item = PlaySessionListItem.fromJson(json);

      expect(item.endedVia, isNull);
      expect(item.endedAt, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = buildFullListItemJson();
      final a = PlaySessionListItem.fromJson(json);
      final b = PlaySessionListItem.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildFullListItemJson();
      final jsonB = Map<String, dynamic>.from(jsonA)
        ..['public_id'] = 'playSession-999';

      final a = PlaySessionListItem.fromJson(jsonA);
      final b = PlaySessionListItem.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── PlaySessionListResponse ──────────────────────────────────────────

  group('PlaySessionListResponse', () {
    test('fromJson parses valid response with items', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[
          <String, dynamic>{
            'public_id': 'playSession-001',
            'library_entry': buildLibraryEntryJson(),
            'play_session_type': 'story',
            'ended_via': 'wrapUp',
            'started_at': '2025-06-20T18:00:00Z',
            'ended_at': '2025-06-20T20:00:00Z',
          },
        ],
        'total': 1,
      };

      final response = PlaySessionListResponse.fromJson(json);

      expect(response.items, hasLength(1));
      expect(response.items.first.publicId, equals('playSession-001'));
      expect(response.total, equals(1));
    });

    test('fromJson parses empty items list', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };

      final response = PlaySessionListResponse.fromJson(json);

      expect(response.items, isEmpty);
      expect(response.total, equals(0));
    });

    test('Equatable: equal instances are equal', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };
      final a = PlaySessionListResponse.fromJson(json);
      final b = PlaySessionListResponse.fromJson(json);

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
      final a = PlaySessionListResponse.fromJson(jsonA);
      final b = PlaySessionListResponse.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  // ── RecapPreview ──────────────────────────────────────────────

  group('RecapPreview', () {
    test('fromJson parses full fields', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'recap_text': 'Welcome back, Tarnished.',
        'last_session_context': buildSessionContextJson(),
      };

      final preview = RecapPreview.fromJson(json);

      expect(preview.libraryEntry.publicId, equals('entry-001'));
      expect(preview.recapText, equals('Welcome back, Tarnished.'));
      expect(preview.lastSessionContext, isA<SessionContext>());
      expect(preview.lastSessionContext?.nextAction, equals('Beat Margit'));
    });

    test('fromJson parses with nullable fields null', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'recap_text': null,
        'last_session_context': null,
      };

      final preview = RecapPreview.fromJson(json);

      expect(preview.recapText, isNull);
      expect(preview.lastSessionContext, isNull);
    });

    test('Equatable: equal instances are equal', () {
      final json = <String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'recap_text': 'Recap',
        'last_session_context': buildSessionContextJson(),
      };
      final a = RecapPreview.fromJson(json);
      final b = RecapPreview.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final a = RecapPreview.fromJson(<String, dynamic>{
        'library_entry': buildLibraryEntryJson(),
        'recap_text': 'Recap A',
        'last_session_context': null,
      });
      final b = RecapPreview.fromJson(<String, dynamic>{
        'library_entry': buildLibraryEntryJson(publicId: 'entry-999'),
        'recap_text': 'Recap B',
        'last_session_context': null,
      });

      expect(a, isNot(equals(b)));
    });
  });
}
