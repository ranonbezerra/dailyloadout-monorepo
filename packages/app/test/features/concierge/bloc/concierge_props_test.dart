import 'package:app/core/concierge/concierge_models.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ConciergeEvent', () {
    test('SendConciergeMessage supports value equality and props', () {
      const a = SendConciergeMessage('what should I play?');
      const b = SendConciergeMessage('what should I play?');
      expect(a, b);
      expect(a.props, ['what should I play?']);
      expect(a, isNot(const SendConciergeMessage('other')));
    });
  });

  group('ConciergeState', () {
    const message = ChatMessage(role: ChatRole.user, text: 'hi');

    test('default state has expected values', () {
      const state = ConciergeState();
      expect(state.messages, isEmpty);
      expect(state.status, ConciergeStatus.initial);
      expect(state.threadId, isNull);
      expect(state.errorMessage, isNull);
      expect(state.isStreaming, false);
    });

    test('supports value equality and props', () {
      const a = ConciergeState(
        messages: [message],
        status: ConciergeStatus.streaming,
        threadId: 't-1',
        errorMessage: 'oops',
      );
      const b = ConciergeState(
        messages: [message],
        status: ConciergeStatus.streaming,
        threadId: 't-1',
        errorMessage: 'oops',
      );
      expect(a, b);
      expect(a.isStreaming, true);
      expect(a.props, [
        [message],
        ConciergeStatus.streaming,
        't-1',
        'oops',
        null,
      ]);
    });

    test('copyWith sets and clears the active tool', () {
      const base = ConciergeState();
      final running = base.copyWith(activeTool: 'search_library');
      expect(running.activeTool, 'search_library');
      // A plain copyWith keeps it; clearActiveTool resets it.
      expect(running.copyWith(threadId: 't').activeTool, 'search_library');
      expect(running.copyWith(clearActiveTool: true).activeTool, isNull);
    });

    test('copyWith updates provided fields and clears errorMessage', () {
      const base = ConciergeState(
        status: ConciergeStatus.error,
        errorMessage: 'boom',
        threadId: 't-1',
      );
      final updated = base.copyWith(
        status: ConciergeStatus.idle,
        messages: const [message],
      );
      expect(updated.status, ConciergeStatus.idle);
      expect(updated.messages, [message]);
      expect(updated.threadId, 't-1');
      // errorMessage is always reset by copyWith.
      expect(updated.errorMessage, isNull);
    });
  });
}
