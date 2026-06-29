import 'package:app/core/theme/slate_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DLColors', () {
    test('constants are not null', () {
      // Neutrals
      expect(DLColors.bg, isNotNull);
      expect(DLColors.bg2, isNotNull);
      expect(DLColors.surface, isNotNull);
      expect(DLColors.surface2, isNotNull);
      expect(DLColors.line, isNotNull);
      expect(DLColors.lineSoft, isNotNull);

      // Text
      expect(DLColors.text, isNotNull);
      expect(DLColors.textMuted, isNotNull);
      expect(DLColors.textDim, isNotNull);

      // Hero
      expect(DLColors.coral, isNotNull);
      expect(DLColors.coralBright, isNotNull);
      expect(DLColors.coralDeep, isNotNull);

      // Secondary
      expect(DLColors.violet, isNotNull);
      expect(DLColors.violetDeep, isNotNull);

      // Semantic
      expect(DLColors.green, isNotNull);
      expect(DLColors.red, isNotNull);

      // Status
      expect(DLColors.statusBacklog, isNotNull);
      expect(DLColors.statusPlaying, isNotNull);
      expect(DLColors.statusPaused, isNotNull);
      expect(DLColors.statusCompleted, isNotNull);
      expect(DLColors.statusSetAside, isNotNull);
    });

    test('status colors map to the expected brand colors', () {
      expect(DLColors.statusPlaying, equals(DLColors.coral));
      expect(DLColors.statusPaused, equals(DLColors.violet));
      expect(DLColors.statusCompleted, equals(DLColors.green));
      expect(DLColors.statusSetAside, equals(DLColors.textDim));
    });

    test('bg color matches midnight hex value 0xFF121119', () {
      expect(DLColors.bg, equals(const Color(0xFF121119)));
    });

    test('coral color matches hex value 0xFFFF5A4D', () {
      expect(DLColors.coral, equals(const Color(0xFFFF5A4D)));
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

    test('dark theme scaffoldBackgroundColor is DLColors.bg', () {
      final theme = SlateTheme.dark;

      expect(theme.scaffoldBackgroundColor, equals(DLColors.bg));
    });

    test('dark theme appBarTheme backgroundColor is DLColors.bg', () {
      final theme = SlateTheme.dark;

      expect(theme.appBarTheme.backgroundColor, equals(DLColors.bg));
    });

    test('dark theme primary color is coral', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.primary, equals(DLColors.coral));
    });

    test('dark theme secondary color is violet', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.secondary, equals(DLColors.violet));
    });

    test('dark theme surface color matches DLColors.surface', () {
      final theme = SlateTheme.dark;

      expect(theme.colorScheme.surface, equals(DLColors.surface));
    });

    test('dark theme cardColor is DLColors.surface', () {
      final theme = SlateTheme.dark;

      expect(theme.cardColor, equals(DLColors.surface));
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
