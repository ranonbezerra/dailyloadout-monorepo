import 'package:app/core/theme/slate_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SlateColors', () {
    test('constants are not null', () {
      // Neutrals
      expect(SlateColors.bg, isNotNull);
      expect(SlateColors.bg2, isNotNull);
      expect(SlateColors.surface, isNotNull);
      expect(SlateColors.surface2, isNotNull);
      expect(SlateColors.line, isNotNull);
      expect(SlateColors.lineSoft, isNotNull);

      // Text
      expect(SlateColors.text, isNotNull);
      expect(SlateColors.textMuted, isNotNull);
      expect(SlateColors.textDim, isNotNull);

      // Hero
      expect(SlateColors.coral, isNotNull);
      expect(SlateColors.coralBright, isNotNull);
      expect(SlateColors.coralDeep, isNotNull);

      // Secondary
      expect(SlateColors.violet, isNotNull);
      expect(SlateColors.violetDeep, isNotNull);

      // Semantic
      expect(SlateColors.green, isNotNull);
      expect(SlateColors.red, isNotNull);

      // Status
      expect(SlateColors.statusBacklog, isNotNull);
      expect(SlateColors.statusPlaying, isNotNull);
      expect(SlateColors.statusPaused, isNotNull);
      expect(SlateColors.statusCompleted, isNotNull);
      expect(SlateColors.statusSetAside, isNotNull);
    });

    test('status colors map to the expected brand colors', () {
      expect(SlateColors.statusPlaying, equals(SlateColors.coral));
      expect(SlateColors.statusPaused, equals(SlateColors.violet));
      expect(SlateColors.statusCompleted, equals(SlateColors.green));
      expect(SlateColors.statusSetAside, equals(SlateColors.textDim));
    });

    test('bg color matches midnight hex value 0xFF121119', () {
      expect(SlateColors.bg, equals(const Color(0xFF121119)));
    });

    test('coral color matches hex value 0xFFFF5A4D', () {
      expect(SlateColors.coral, equals(const Color(0xFFFF5A4D)));
    });
  });

  group('SlateTheme', () {
    test('dark getter returns a ThemeData instance', () {
      final theme = SlateTheme.dark;

      expect(theme, isA<ThemeData>());
    });

    test('dark theme has correct colorScheme brightness (dark)', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.brightness, equals(Brightness.dark));
    });

    test('dark theme scaffoldBackgroundColor is SlateColors.bg', () {
      final theme = SlateTheme.dark;

      expect(theme.scaffoldBackgroundColor, equals(SlateColors.bg));
    });

    test('dark theme appBarTheme backgroundColor is SlateColors.bg', () {
      final theme = SlateTheme.dark;

      expect(theme.appBarTheme.backgroundColor, equals(SlateColors.bg));
    });

    test('dark theme primary color is coral', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.primary, equals(SlateColors.coral));
    });

    test('dark theme secondary color is violet', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.secondary, equals(SlateColors.violet));
    });

    test('dark theme surface color matches SlateColors.surface', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.surface, equals(SlateColors.surface));
    });

    test('dark theme cardColor is SlateColors.surface', () {
      final theme = SlateTheme.dark;

      expect(theme.cardColor, equals(SlateColors.surface));
    });

    test('dark theme appBar elevation is zero', () {
      final theme = SlateTheme.dark;

      expect(theme.appBarTheme.elevation, equals(0));
    });

    test('dark theme appBar title font family is Outfit (display)', () {
      final theme = SlateTheme.dark;

      expect(
        theme.appBarTheme.titleTextStyle?.fontFamily,
        equals(SlateTheme.displayFamily),
      );
    });

    test('darkScheme constant is accessible and consistent', () {
      const schemeFromConst = SlateTheme.darkScheme;
      final schemeFromTheme = SlateTheme.dark.colorScheme;

      expect(schemeFromConst.primary, equals(schemeFromTheme.primary));
      expect(schemeFromConst.secondary, equals(schemeFromTheme.secondary));
      expect(schemeFromConst.brightness, equals(schemeFromTheme.brightness));
    });

    test('font family constants are defined', () {
      expect(SlateTheme.displayFamily, equals('Outfit'));
      expect(SlateTheme.bodyFamily, equals('Inter'));
      expect(SlateTheme.monoFamily, equals('JetBrains Mono'));
    });
  });
}
