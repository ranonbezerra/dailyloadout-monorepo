import 'package:app/features/home/view/home_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('HomePage', () {
    testWidgets('renders AppBar with Slate title', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: HomePage()));

      expect(find.byType(AppBar), findsOneWidget);

      // The AppBar title should contain 'Slate'.
      final appBar = tester.widget<AppBar>(find.byType(AppBar));
      final titleWidget = appBar.title! as Text;
      expect(titleWidget.data, 'Slate');
    });

    testWidgets('renders WIP text', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: HomePage()));

      expect(find.text('WIP'), findsOneWidget);
    });

    testWidgets('has Scaffold', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: HomePage()));

      expect(find.byType(Scaffold), findsOneWidget);
    });
  });
}
