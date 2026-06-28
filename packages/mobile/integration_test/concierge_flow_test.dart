import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/api/api_client.dart';
import 'package:app/core/auth/auth_token_store.dart';
import 'package:app/core/concierge/concierge_repository.dart';
import 'package:app/core/theme/dailyloadout_theme.dart';
import 'package:app/features/concierge/bloc/concierge_bloc.dart';
import 'package:app/features/concierge/view/concierge_page.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

/// Headless integration test for the Backlog Concierge.
///
/// Unlike the widget test (which mocks [ConciergeRepository]), this drives the
/// *real* stack — [ConciergeRepository] → [ApiClient]'s Dio → SSE line parsing
/// → [ConciergeBloc] → [ConciergePage] — mocking only at the network adapter.
/// It validates that the on-the-wire SSE format the API emits is decoded and
/// rendered end to end, including the validated-recommendation Play CTA.
///
/// Run headless: `fvm flutter test integration_test/concierge_flow_test.dart`.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('streams a guarded reply and offers a Play CTA', (tester) async {
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8100'))
      ..httpClientAdapter = _SseMockAdapter();
    final apiClient = ApiClient(tokenStore: AuthTokenStore(), dio: dio);
    final repository = ConciergeRepository(apiClient: apiClient);

    await tester.pumpWidget(
      MaterialApp(
        theme: DailyLoadoutTheme.dark,
        home: BlocProvider(
          create: (_) => ConciergeBloc(conciergeRepository: repository),
          child: const ConciergePage(),
        ),
      ),
    );

    expect(find.text('What should you play tonight?'), findsOneWidget);

    await tester.enterText(
      find.byType(TextField),
      'what should I play tonight?',
    );
    await tester.testTextInput.receiveAction(TextInputAction.send);
    await tester.pumpAndSettle();

    // The streamed prose and the validated recommendation CTA both render;
    // the raw `RECOMMEND:` marker is withheld by the server-side gate.
    expect(find.text('Give Hollow Knight a go tonight.'), findsOneWidget);
    expect(find.text('Play Hollow Knight'), findsOneWidget);
  });
}

/// A Dio adapter that replies to the concierge endpoint with a canned SSE
/// stream matching the API's on-the-wire event format, and `{}` to anything
/// else so an unexpected call never hangs the test.
class _SseMockAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path == '/v1/concierge/chat') {
      const rec = '{"id": "le-hollow-knight", "title": "Hollow Knight"}';
      final sse = [
        'data: {"tool": "search_library", "phase": "start"}',
        'data: {"tool": "search_library", "phase": "end"}',
        'data: {"token": "Give Hollow Knight a go tonight."}',
        'data: {"recommendation": $rec}',
        'data: {"done": true, "thread_id": "t-it"}',
      ].map((line) => '$line\n\n').join();
      return ResponseBody(
        Stream<Uint8List>.fromIterable([Uint8List.fromList(utf8.encode(sse))]),
        200,
        headers: {
          Headers.contentTypeHeader: ['text/event-stream'],
        },
      );
    }
    return ResponseBody.fromString(
      '{}',
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
