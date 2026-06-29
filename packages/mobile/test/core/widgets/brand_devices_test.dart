import 'package:app/core/theme/slate_theme.dart';
import 'package:app/core/widgets/brand_devices.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) => MaterialApp(
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('DLSlot', () {
    testWidgets('lit slot uses the coral border', (tester) async {
      await tester.pumpWidget(_wrap(const DLSlot(lit: true, child: Text('P'))));
      expect(find.text('P'), findsOneWidget);
      final container = tester.widget<Container>(find.byType(Container));
      final decoration = container.decoration! as BoxDecoration;
      expect(decoration.border!.top.color, DLColors.coral);
      expect(decoration.boxShadow, isNotNull);
    });

    testWidgets('waiting slot uses the muted line border, no shadow', (
      tester,
    ) async {
      await tester.pumpWidget(_wrap(const DLSlot()));
      final container = tester.widget<Container>(find.byType(Container));
      final decoration = container.decoration! as BoxDecoration;
      expect(decoration.border!.top.color, DLColors.line);
      expect(decoration.boxShadow, isNull);
    });
  });

  group('DLLineup', () {
    testWidgets('renders the requested number of slots', (tester) async {
      await tester.pumpWidget(_wrap(const DLLineup(count: 4, litIndex: 2)));
      expect(find.byType(DLSlot), findsNWidgets(4));
    });
  });

  testWidgets('DLRecapLabel renders the glyph and uppercases the label', (
    tester,
  ) async {
    await tester.pumpWidget(_wrap(const DLRecapLabel('previously on')));
    expect(find.text('▸ PREVIOUSLY ON'), findsOneWidget);
  });

  group('DLSpotlight', () {
    testWidgets('active wraps the child in a glow', (tester) async {
      await tester.pumpWidget(_wrap(const DLSpotlight(child: Text('pick'))));
      expect(find.text('pick'), findsOneWidget);
      expect(find.byType(DecoratedBox), findsWidgets);
    });

    testWidgets('inactive returns the child unwrapped', (tester) async {
      await tester.pumpWidget(
        _wrap(const DLSpotlight(active: false, child: Text('pick'))),
      );
      expect(find.text('pick'), findsOneWidget);
    });
  });
}
