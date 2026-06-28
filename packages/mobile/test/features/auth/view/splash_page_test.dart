import 'package:app/features/auth/view/splash_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SplashPage', () {
    testWidgets('renders Scaffold with CircularProgressIndicator', (
      tester,
    ) async {
      await tester.pumpWidget(const MaterialApp(home: SplashPage()));

      expect(find.byType(Scaffold), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('has no AppBar', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: SplashPage()));

      expect(find.byType(AppBar), findsNothing);
    });
  });
}
