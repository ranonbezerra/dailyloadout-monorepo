import 'package:app/core/concierge/concierge_models.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:app/features/concierge/view/concierge_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
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

  Widget buildSubject() {
    return MaterialApp(
      theme: DailyLoadoutTheme.dark,
      home: BlocProvider(
        create: (_) => ConciergeBloc(conciergeRepository: repository),
        child: const ConciergePage(),
      ),
    );
  }

  testWidgets('shows the empty-state prompt', (tester) async {
    await tester.pumpWidget(buildSubject());

    expect(find.text('What should you play tonight?'), findsOneWidget);
  });

  testWidgets('sends a message and renders the streamed reply', (tester) async {
    when(
      () => repository.streamChat(
        message: any(named: 'message'),
        threadId: any(named: 'threadId'),
        cancelToken: any(named: 'cancelToken'),
      ),
    ).thenAnswer(
      (_) => _deltas(const [
        ConciergeDelta(token: 'Try Hades.'),
        ConciergeDelta(done: true, threadId: 't1'),
      ]),
    );

    await tester.pumpWidget(buildSubject());

    await tester.enterText(find.byType(TextField), 'something short');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    expect(find.text('something short'), findsOneWidget);
    expect(find.text('Try Hades.'), findsOneWidget);
  });

  testWidgets('renders a Play CTA for a validated recommendation', (
    tester,
  ) async {
    when(
      () => repository.streamChat(
        message: any(named: 'message'),
        threadId: any(named: 'threadId'),
        cancelToken: any(named: 'cancelToken'),
      ),
    ).thenAnswer(
      (_) => _deltas(const [
        ConciergeDelta(token: 'Give this a go.'),
        ConciergeDelta(
          recommendation: Recommendation(id: 'abc', title: 'Hades'),
        ),
        ConciergeDelta(done: true, threadId: 't1'),
      ]),
    );

    await tester.pumpWidget(buildSubject());
    await tester.enterText(find.byType(TextField), 'what should I play?');
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    expect(find.text('Play Hades'), findsOneWidget);
  });
}
