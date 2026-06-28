import 'package:app/core/capture/capture_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('CaptureCandidate', () {
    test('fromJson parses full fields', () {
      final json = <String, dynamic>{
        'public_id': 'cand-001',
        'title': 'Elden Ring',
        'platform_hint': 'PS5',
        'igdb_title': 'Elden Ring',
        'igdb_cover_url': 'https://cover.jpg',
        'igdb_summary': 'An action RPG.',
        'igdb_genres': ['RPG', 'Action'],
        'confidence': 0.95,
        'status': 'pending',
      };

      final candidate = CaptureCandidate.fromJson(json);

      expect(candidate.publicId, equals('cand-001'));
      expect(candidate.title, equals('Elden Ring'));
      expect(candidate.platformHint, equals('PS5'));
      expect(candidate.igdbTitle, equals('Elden Ring'));
      expect(candidate.igdbCoverUrl, equals('https://cover.jpg'));
      expect(candidate.igdbSummary, equals('An action RPG.'));
      expect(candidate.igdbGenres, equals(['RPG', 'Action']));
      expect(candidate.confidence, equals(0.95));
      expect(candidate.status, equals('pending'));
    });

    test('fromJson parses minimal/null optional fields', () {
      final json = <String, dynamic>{
        'public_id': 'cand-002',
        'title': 'Unknown Game',
        'platform_hint': null,
        'igdb_title': null,
        'igdb_cover_url': null,
        'igdb_summary': null,
        'igdb_genres': null,
        'confidence': null,
        'status': 'rejected',
      };

      final candidate = CaptureCandidate.fromJson(json);

      expect(candidate.platformHint, isNull);
      expect(candidate.igdbTitle, isNull);
      expect(candidate.igdbCoverUrl, isNull);
      expect(candidate.igdbSummary, isNull);
      expect(candidate.igdbGenres, isNull);
      expect(candidate.confidence, isNull);
      expect(candidate.status, equals('rejected'));
    });

    test('fromJson handles integer confidence via num cast', () {
      final json = <String, dynamic>{
        'public_id': 'cand-003',
        'title': 'Some Game',
        'status': 'confirmed',
        'confidence': 1,
      };

      final candidate = CaptureCandidate.fromJson(json);

      expect(candidate.confidence, equals(1.0));
      expect(candidate.confidence, isA<double>());
    });

    test('Equatable: equal instances are equal', () {
      const a = CaptureCandidate(
        publicId: 'c1',
        title: 'Game',
        status: 'pending',
        confidence: 0.8,
      );
      const b = CaptureCandidate(
        publicId: 'c1',
        title: 'Game',
        status: 'pending',
        confidence: 0.8,
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      const a = CaptureCandidate(
        publicId: 'c1',
        title: 'Game A',
        status: 'pending',
      );
      const b = CaptureCandidate(
        publicId: 'c2',
        title: 'Game B',
        status: 'confirmed',
      );

      expect(a, isNot(equals(b)));
    });
  });

  group('Capture', () {
    Map<String, dynamic> buildCaptureJson({
      List<Map<String, dynamic>>? candidates,
    }) {
      return <String, dynamic>{
        'public_id': 'cap-001',
        'input_type': 'text',
        'raw_text': 'I just bought Elden Ring for PS5',
        'status': 'review',
        'error_message': null,
        'candidates':
            candidates ??
            <Map<String, dynamic>>[
              <String, dynamic>{
                'public_id': 'cand-001',
                'title': 'Elden Ring',
                'platform_hint': 'PS5',
                'igdb_title': null,
                'igdb_cover_url': null,
                'igdb_summary': null,
                'igdb_genres': null,
                'confidence': 0.9,
                'status': 'pending',
              },
            ],
        'created_at': '2025-06-01T12:00:00Z',
        'updated_at': '2025-06-01T12:05:00Z',
      };
    }

    test('fromJson parses with candidates list', () {
      final json = buildCaptureJson();

      final capture = Capture.fromJson(json);

      expect(capture.publicId, equals('cap-001'));
      expect(capture.inputType, equals('text'));
      expect(capture.rawText, equals('I just bought Elden Ring for PS5'));
      expect(capture.status, equals('review'));
      expect(capture.errorMessage, isNull);
      expect(capture.candidates, hasLength(1));
      expect(capture.candidates.first.title, equals('Elden Ring'));
      expect(capture.createdAt, equals(DateTime.utc(2025, 6, 1, 12)));
      expect(capture.updatedAt, equals(DateTime.utc(2025, 6, 1, 12, 5)));
    });

    test('fromJson with null candidates defaults to empty list', () {
      final json = buildCaptureJson()..['candidates'] = null;

      final capture = Capture.fromJson(json);

      expect(capture.candidates, isEmpty);
      expect(capture.candidates, isA<List<CaptureCandidate>>());
    });

    test('fromJson with missing candidates key defaults to empty list', () {
      final json = buildCaptureJson()..remove('candidates');

      final capture = Capture.fromJson(json);

      expect(capture.candidates, isEmpty);
    });

    test('fromJson parses error_message when present', () {
      final json = buildCaptureJson()
        ..['status'] = 'error'
        ..['error_message'] = 'LLM extraction failed';

      final capture = Capture.fromJson(json);

      expect(capture.status, equals('error'));
      expect(capture.errorMessage, equals('LLM extraction failed'));
    });

    test('Equatable: equal instances are equal', () {
      final json = buildCaptureJson();
      final a = Capture.fromJson(json);
      final b = Capture.fromJson(json);

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      final jsonA = buildCaptureJson();
      final jsonB = Map<String, dynamic>.from(jsonA)..['public_id'] = 'cap-999';

      final a = Capture.fromJson(jsonA);
      final b = Capture.fromJson(jsonB);

      expect(a, isNot(equals(b)));
    });
  });

  group('TranscribeResult', () {
    test('fromJson parses full fields', () {
      final json = <String, dynamic>{
        'text': 'I just finished playing Zelda',
        'language': 'en',
        'duration_seconds': 5.2,
      };

      final result = TranscribeResult.fromJson(json);

      expect(result.text, equals('I just finished playing Zelda'));
      expect(result.language, equals('en'));
      expect(result.durationSeconds, equals(5.2));
    });

    test('fromJson parses minimal fields with nulls', () {
      final json = <String, dynamic>{
        'text': 'Some text',
        'language': null,
        'duration_seconds': null,
      };

      final result = TranscribeResult.fromJson(json);

      expect(result.text, equals('Some text'));
      expect(result.language, isNull);
      expect(result.durationSeconds, isNull);
    });

    test('fromJson handles integer duration via num cast', () {
      final json = <String, dynamic>{'text': 'audio', 'duration_seconds': 10};

      final result = TranscribeResult.fromJson(json);

      expect(result.durationSeconds, equals(10.0));
      expect(result.durationSeconds, isA<double>());
    });

    test('Equatable: equal instances are equal', () {
      const a = TranscribeResult(
        text: 'hello',
        language: 'en',
        durationSeconds: 3,
      );
      const b = TranscribeResult(
        text: 'hello',
        language: 'en',
        durationSeconds: 3,
      );

      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('Equatable: different instances are not equal', () {
      const a = TranscribeResult(text: 'hello');
      const b = TranscribeResult(text: 'goodbye');

      expect(a, isNot(equals(b)));
    });
  });

  group('CaptureListResponse', () {
    test('fromJson parses valid response', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[
          <String, dynamic>{
            'public_id': 'cap-001',
            'input_type': 'voice',
            'raw_text': 'test',
            'status': 'review',
            'error_message': null,
            'candidates': <Map<String, dynamic>>[],
            'created_at': '2025-06-01T00:00:00Z',
            'updated_at': '2025-06-01T00:00:00Z',
          },
        ],
        'total': 1,
      };

      final response = CaptureListResponse.fromJson(json);

      expect(response.items, hasLength(1));
      expect(response.items.first.inputType, equals('voice'));
      expect(response.total, equals(1));
    });

    test('fromJson parses empty items list', () {
      final json = <String, dynamic>{
        'items': <Map<String, dynamic>>[],
        'total': 0,
      };

      final response = CaptureListResponse.fromJson(json);

      expect(response.items, isEmpty);
      expect(response.total, equals(0));
    });
  });
}
