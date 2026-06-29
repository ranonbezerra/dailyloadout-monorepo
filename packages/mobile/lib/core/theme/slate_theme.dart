import 'package:flutter/material.dart';

/// Slate brand color tokens.
///
/// Mirrors `brand/BRAND.md` §14. Dark-first "Night Den": a midnight base
/// with a coral spotlight and a violet secondary. Do not introduce ad-hoc
/// colors in widgets — reference these tokens (or the [ColorScheme]) instead.
abstract final class SlateColors {
  // Neutrals
  static const Color bg = Color(0xFF121119); // Midnight — app background
  static const Color bg2 = Color(0xFF17161F);
  static const Color surface = Color(0xFF1E1C28); // cards, panels
  static const Color surface2 = Color(0xFF272433); // raised / hover
  static const Color line = Color(0xFF322E3F); // borders
  static const Color lineSoft = Color(0xFF262232); // hairlines

  // Text
  static const Color text = Color(0xFFF0EDF5);
  static const Color textMuted = Color(0xFFA39FB2);
  static const Color textDim = Color(0xFF6B6679);

  // Hero — coral
  static const Color coral = Color(0xFFFF5A4D); // the pick, primary action
  static const Color coralBright = Color(0xFFFF7A6E); // glow / hover
  static const Color coralDeep = Color(0xFFE03E2F); // pressed

  // Secondary — violet
  static const Color violet = Color(0xFF9A8CF5); // recaps, links, paused
  static const Color violetDeep = Color(0xFF6E5FD6);

  // Semantic
  static const Color green = Color(0xFF46C28A); // completed / success
  static const Color red = Color(0xFFE5484D); // destructive (rare, outline)

  // Status (no-guilt mapping)
  static const Color statusBacklog = Color(0xFF8A8699);
  static const Color statusPlaying = coral;
  static const Color statusPaused = violet;
  static const Color statusCompleted = green;
  static const Color statusSetAside = textDim; // never red
}

/// Slate [ThemeData]. The app is dark-first; [dark] is the canonical
/// theme.
///
/// ## Fonts
/// The brand uses **Outfit** (display) + **Inter** (body) + **JetBrains Mono**
/// (data). They are not bundled yet, so by default Flutter falls back to the
/// platform font. To enable them, either:
///
/// 1. Add `google_fonts` and swap the text theme:
///    ```dart
///    import 'package:google_fonts/google_fonts.dart';
///    // inside dark:
///    final body = GoogleFonts.interTextTheme(base.textTheme);
///    final textTheme = _applyDisplay(body, GoogleFonts.outfit().fontFamily!);
///    ```
/// 2. Or bundle the .ttf files under `assets/fonts/` and declare the
///    `Outfit` / `Inter` / `JetBrains Mono` families in `pubspec.yaml`.
abstract final class SlateTheme {
  static const String displayFamily = 'Outfit';
  static const String bodyFamily = 'Inter';
  static const String monoFamily = 'JetBrains Mono';

  static const ColorScheme darkScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: SlateColors.coral,
    onPrimary: SlateColors.bg,
    primaryContainer: SlateColors.coralDeep,
    onPrimaryContainer: SlateColors.text,
    secondary: SlateColors.violet,
    onSecondary: SlateColors.bg,
    secondaryContainer: SlateColors.violetDeep,
    onSecondaryContainer: SlateColors.text,
    tertiary: SlateColors.green,
    onTertiary: SlateColors.bg,
    error: SlateColors.red,
    onError: SlateColors.text,
    surface: SlateColors.surface,
    onSurface: SlateColors.text,
    onSurfaceVariant: SlateColors.textMuted,
    surfaceContainerLowest: SlateColors.bg,
    surfaceContainerLow: SlateColors.bg2,
    surfaceContainer: SlateColors.surface,
    surfaceContainerHigh: SlateColors.surface2,
    surfaceContainerHighest: SlateColors.surface2,
    outline: SlateColors.line,
    outlineVariant: SlateColors.lineSoft,
  );

  static ThemeData get dark {
    final base = ThemeData.dark(useMaterial3: true);

    final textTheme = base.textTheme
        .apply(
          fontFamily: bodyFamily,
          bodyColor: SlateColors.text,
          displayColor: SlateColors.text,
        )
        .copyWith(
          displayLarge: base.textTheme.displayLarge?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            color: SlateColors.text,
          ),
          displayMedium: base.textTheme.displayMedium?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            color: SlateColors.text,
          ),
          displaySmall: base.textTheme.displaySmall?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            color: SlateColors.text,
          ),
          headlineLarge: base.textTheme.headlineLarge?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            color: SlateColors.text,
          ),
          headlineMedium: base.textTheme.headlineMedium?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            color: SlateColors.text,
          ),
          headlineSmall: base.textTheme.headlineSmall?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w600,
            color: SlateColors.text,
          ),
          titleLarge: base.textTheme.titleLarge?.copyWith(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w600,
            color: SlateColors.text,
          ),
        );

    return base.copyWith(
      colorScheme: darkScheme,
      scaffoldBackgroundColor: SlateColors.bg,
      canvasColor: SlateColors.bg,
      cardColor: SlateColors.surface,
      dividerColor: SlateColors.line,
      dividerTheme: const DividerThemeData(
        color: SlateColors.line,
        thickness: 0.5,
        space: 1,
      ),
      textTheme: textTheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: SlateColors.bg,
        foregroundColor: SlateColors.text,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: displayFamily,
          fontWeight: FontWeight.w700,
          fontSize: 20,
          color: SlateColors.text,
        ),
      ),
      cardTheme: CardThemeData(
        color: SlateColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: SlateColors.line, width: 0.5),
        ),
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: SlateColors.coral,
          foregroundColor: SlateColors.bg,
          disabledBackgroundColor: SlateColors.surface2,
          disabledForegroundColor: SlateColors.textDim,
          textStyle: const TextStyle(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: SlateColors.coral,
          foregroundColor: SlateColors.bg,
          elevation: 0,
          textStyle: const TextStyle(
            fontFamily: displayFamily,
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: SlateColors.coral),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: SlateColors.surface2,
        labelStyle: const TextStyle(color: SlateColors.textMuted, fontSize: 13),
        side: BorderSide.none,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: SlateColors.surface,
        hintStyle: const TextStyle(color: SlateColors.textDim),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 14,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: SlateColors.line, width: 0.5),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: SlateColors.line, width: 0.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: SlateColors.coral, width: 1.5),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: SlateColors.coral,
      ),
      iconTheme: const IconThemeData(color: SlateColors.textMuted),
      splashColor: SlateColors.coralDeep.withValues(alpha: 0.12),
      highlightColor: SlateColors.coralDeep.withValues(alpha: 0.08),
    );
  }
}
