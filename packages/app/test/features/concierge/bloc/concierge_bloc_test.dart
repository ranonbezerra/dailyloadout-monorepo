import 'package:app/core/concierge/concierge_models.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:bloc_test/bloc_test.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockConciergeRepository extends Mock implements ConciergeRepository {}

Stream<ConciergeDelta> _deltas(List<ConciergeDelta> items) async* {
  for (final item in items) {
    yield item;
  }
}

void main() {
  late MockConciergeRepository repository;

  setUp(() {
    repository = MockConciergeRepository();
  });

  ConciergeBloc buildBloc() => ConciergeBloc(conciergeRepository: repository);

  group('ConciergeBloc', () {
    test('initial state is empty and idle', () {
      final bloc = buildBloc();
      expect(bloc.state.messages, isEmpty);
      expect(bloc.state.status, ConciergeStatus.initial);
      bloc.close();
    });

    blocTest<ConciergeBloc, ConciergeState>(
      'streams the reply, threads the id, and ends idle',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            ConciergeDelta(token: 'Play '),
            ConciergeDelta(token: 'Hades.'),
            ConciergeDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) =>
          bloc.add(const SendConciergeMessage('what should I play?')),
      verify: (bloc) {
        expect(bloc.state.status, ConciergeStatus.idle);
        expect(bloc.state.threadId, 't1');
        expect(bloc.state.messages, [
          const ChatMessage(role: ChatRole.user, text: 'what should I play?'),
          const ChatMessage(role: ChatRole.assistant, text: 'Play Hades.'),
        ]);
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'ignores blank messages',
      build: buildBloc,
      act: (bloc) => bloc.add(const SendConciergeMessage('   ')),
      expect: () => const <ConciergeState>[],
      verify: (_) {
        verifyNever(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        );
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'emits an error state when the stream fails',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenThrow(
          DioException(
            requestOptions: RequestOptions(path: '/v1/concierge/chat'),
          ),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendConciergeMessage('hello')),
      verify: (bloc) {
        expect(bloc.state.status, ConciergeStatus.error);
        expect(bloc.state.errorMessage, isNotNull);
        expect(bloc.state.messages.last.role, ChatRole.assistant);
        expect(bloc.state.messages.last.text, contains('something went wrong'));
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'surfaces a server error event as an error state',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            ConciergeDelta(error: 'The concierge is unavailable right now.'),
            ConciergeDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendConciergeMessage('hi')),
      verify: (bloc) {
        expect(bloc.state.status, ConciergeStatus.error);
        expect(bloc.state.errorMessage, contains('unavailable'));
        expect(bloc.state.messages.last.text, contains('unavailable'));
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'attaches a recommendation and surfaces tool activity',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            ConciergeDelta(tool: 'search_library', phase: 'start'),
            ConciergeDelta(tool: 'search_library', phase: 'end'),
            ConciergeDelta(token: 'Give this a go.'),
            ConciergeDelta(
              recommendation: Recommendation(id: 'abc', title: 'Hades'),
            ),
            ConciergeDelta(done: true, threadId: 't1'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) =>
          bloc.add(const SendConciergeMessage('what should I play?')),
      verify: (bloc) {
        expect(bloc.state.status, ConciergeStatus.idle);
        expect(bloc.state.activeTool, isNull); // cleared once the turn ends
        final last = bloc.state.messages.last;
        expect(last.text, 'Give this a go.');
        expect(
          last.recommendation,
          const Recommendation(id: 'abc', title: 'Hades'),
        );
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'cancelling keeps the partial reply and settles idle',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenThrow(
          DioException.requestCancelled(
            requestOptions: RequestOptions(path: '/v1/concierge/chat'),
            reason: 'cancelled',
          ),
        );
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SendConciergeMessage('hello')),
      verify: (bloc) {
        // A cancellation is not an error — no error state, partial kept.
        expect(bloc.state.status, ConciergeStatus.idle);
        expect(bloc.state.errorMessage, isNull);
      },
    );

    blocTest<ConciergeBloc, ConciergeState>(
      'threads the previous thread id into the next turn',
      setUp: () {
        when(
          () => repository.streamChat(
            message: any(named: 'message'),
            threadId: any(named: 'threadId'),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).thenAnswer(
          (_) => _deltas(const [
            ConciergeDelta(done: true, threadId: 'thread-42'),
          ]),
        );
      },
      build: buildBloc,
      act: (bloc) async {
        bloc.add(const SendConciergeMessage('first'));
        await bloc.stream.firstWhere((s) => s.status == ConciergeStatus.idle);
        bloc.add(const SendConciergeMessage('second'));
        await bloc.stream.firstWhere(
          (s) => s.status == ConciergeStatus.idle && s.messages.length == 4,
        );
      },
      verify: (_) {
        verify(
          () => repository.streamChat(
            message: 'first',
            threadId: any(named: 'threadId', that: isNull),
            cancelToken: any(named: 'cancelToken'),
          ),
        ).called(1);
        verify(
          () => repository.streamChat(
            message: 'second',
            threadId: 'thread-42',
            cancelToken: any(named: 'cancelToken'),
          ),
        ).called(1);
      },
    );
  });
}
