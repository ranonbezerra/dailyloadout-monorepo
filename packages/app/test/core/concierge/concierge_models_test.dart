import 'package:app/core/concierge/concierge_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ChatMessage', () {
    test('supports value equality and props', () {
      const a = ChatMessage(role: ChatRole.user, text: 'hi');
      const b = ChatMessage(role: ChatRole.user, text: 'hi');
      expect(a, b);
      expect(a.props, [ChatRole.user, 'hi', null]);
      expect(a, isNot(const ChatMessage(role: ChatRole.assistant, text: 'hi')));
    });

    test('copyWith overrides text but keeps role', () {
      const a = ChatMessage(role: ChatRole.assistant, text: 'hello');
      final updated = a.copyWith(text: 'world');
      expect(updated.role, ChatRole.assistant);
      expect(updated.text, 'world');
    });

    test('copyWith keeps text when not provided', () {
      const a = ChatMessage(role: ChatRole.user, text: 'keep');
      final same = a.copyWith();
      expect(same, a);
    });

    test('carries an optional recommendation', () {
      const rec = Recommendation(id: 'abc', title: 'Hades');
      const a = ChatMessage(
        role: ChatRole.assistant,
        text: 'go',
        recommendation: rec,
      );
      expect(a.recommendation, rec);
    });
  });

  group('Recommendation', () {
    test('fromJson and value equality', () {
      final rec = Recommendation.fromJson(const {
        'id': 'abc',
        'title': 'Hades',
      });
      expect(rec, const Recommendation(id: 'abc', title: 'Hades'));
    });
  });

  group('ConciergeDelta', () {
    test('supports value equality and props', () {
      const a = ConciergeDelta(token: 'x', done: true, threadId: 't-1');
      const b = ConciergeDelta(token: 'x', done: true, threadId: 't-1');
      expect(a, b);
      expect(a.props, ['x', null, null, null, null, null, true, 't-1']);
    });

    test('default values', () {
      const a = ConciergeDelta();
      expect(a.token, isNull);
      expect(a.tool, isNull);
      expect(a.recommendation, isNull);
      expect(a.degrade, isNull);
      expect(a.error, isNull);
      expect(a.done, false);
      expect(a.threadId, isNull);
    });

    test('fromJson parses prose, tool, and recommendation events', () {
      final tokenEvent = ConciergeDelta.fromJson(const {'token': 'chunk'});
      expect(tokenEvent.token, 'chunk');

      final toolEvent = ConciergeDelta.fromJson(const {
        'tool': 'search_library',
        'phase': 'start',
      });
      expect(toolEvent.tool, 'search_library');
      expect(toolEvent.phase, 'start');

      final recEvent = ConciergeDelta.fromJson(const {
        'recommendation': {'id': 'abc', 'title': 'Hades'},
      });
      expect(
        recEvent.recommendation,
        const Recommendation(id: 'abc', title: 'Hades'),
      );

      final doneEvent = ConciergeDelta.fromJson(const {
        'done': true,
        'thread_id': 't-9',
      });
      expect(doneEvent.done, true);
      expect(doneEvent.threadId, 't-9');
    });

    test('fromJson defaults done to false and tolerates missing keys', () {
      final delta = ConciergeDelta.fromJson(const {});
      expect(delta.token, isNull);
      expect(delta.error, isNull);
      expect(delta.done, false);
      expect(delta.threadId, isNull);
    });
  });
}
