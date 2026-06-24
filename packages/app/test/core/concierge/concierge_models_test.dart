import 'package:app/core/concierge/concierge_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ChatMessage', () {
    test('supports value equality and props', () {
      const a = ChatMessage(role: ChatRole.user, text: 'hi');
      const b = ChatMessage(role: ChatRole.user, text: 'hi');
      expect(a, b);
      expect(a.props, [ChatRole.user, 'hi']);
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
  });

  group('ConciergeDelta', () {
    test('supports value equality and props', () {
      const a = ConciergeDelta(delta: 'x', done: true, threadId: 't-1');
      const b = ConciergeDelta(delta: 'x', done: true, threadId: 't-1');
      expect(a, b);
      expect(a.props, ['x', null, true, 't-1']);
    });

    test('default values', () {
      const a = ConciergeDelta();
      expect(a.delta, isNull);
      expect(a.error, isNull);
      expect(a.done, false);
      expect(a.threadId, isNull);
    });

    test('fromJson parses all fields', () {
      final delta = ConciergeDelta.fromJson(const {
        'delta': 'chunk',
        'error': 'oops',
        'done': true,
        'thread_id': 't-9',
      });
      expect(delta.delta, 'chunk');
      expect(delta.error, 'oops');
      expect(delta.done, true);
      expect(delta.threadId, 't-9');
    });

    test('fromJson defaults done to false and tolerates missing keys', () {
      final delta = ConciergeDelta.fromJson(const {});
      expect(delta.delta, isNull);
      expect(delta.error, isNull);
      expect(delta.done, false);
      expect(delta.threadId, isNull);
    });
  });
}
