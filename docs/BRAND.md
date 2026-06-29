# Slate - Brand Standards

**Version:** 1.0 | **Direction:** Night Den x Coral | **Last updated:** 2026-06

> This is the **public, versioned extract**. The full brand guide is maintained locally in `branding/BRAND.md` (the canonical source); keep this file in sync with it.

---

## 1. Identity

**Tagline:** *Less deciding. More playing.*
**Voice line:** *What's the move?*

Slate is the companion that knows your backlog and hands you the right game for tonight — then catches you up on where you left off, like a "previously on..." before the episode.

**We are:** calm, decisive, warm, sharp, honest.
**We are not:** gamified, guilt-inducing, military/tactical, loud, corporate.

### A deliberate non-military stance

Slate keeps one idea from gaming culture — *a deliberate pick for the moment* — without the military baggage that idea usually drags along. The instinct is right; the war-room register is not. Slate is **not a war room**: no camouflage, crosshairs/reticles, "operator / deploy / soldier" theatrics, or dog tags. That register excludes the exact person this is for — someone settling in at night to continue a story-driven game. What we keep is *a deliberate pick for the moment*; what we drop is everything that reads as combat or hierarchy. The feeling is a **good game-night host**, not a commander. The warm lexicon (§5) is the default; the tactical flavor survives only as an opt-in easter egg (see the TODO in §5).

---

## 2. Logo

### The mark — "The Pick"

A single lit slot with a **game controller**: the one game, chosen and ready to play. Coral means lit / chosen for now. The controller is a generic, trademark-free modern gamepad (flat-top body, flared grips, D-pad + two sticks + a four-button diamond) — never a specific console's pad.

| Asset | File | Use |
| --- | --- | --- |
| Mark (color) | `docs/brand/slate-mark.svg` | Primary mark |
| Mark (mono) | `docs/brand/slate-mark-mono.svg` | Single-color contexts |
| Wordmark | `docs/brand/slate-wordmark.svg` | Text-only branding |
| Lockup (horizontal) | `docs/brand/slate-lockup-horizontal.svg` | Header, README, nav |
| Lockup (stacked) | `docs/brand/slate-lockup-stacked.svg` | Square spaces, splash |
| Lockup raster | `docs/brand/lockup-2x.png`, `lockup-stacked-2x.png` | Slides, social |
| Mark raster | `docs/brand/mark-128.png`, `mark-256.png`, `mark-512.png` | Avatars, previews |

### Wordmark rules

`slate` — always lowercase, one word. Set in **Outfit** Bold (700).

### Rules

- Clear space: margin equal to the height of the play triangle on all sides
- Min size: mark 16 px; horizontal lockup 120 px wide
- On dark backgrounds (default). On light, use the mono mark
- Never recolor the controller details, add bevels/shadows, stretch, or rotate
- Never add tactical brackets, crosshairs, or targeting reticles

---

## 3. Color

Dark-first. The base carries a faint indigo warmth (night den). Coral is the spotlight: one warm focal point per screen.

### Core neutrals

| Token | Hex | Use |
| --- | --- | --- |
| `--bg` | `#121119` | App background (Midnight) |
| `--bg-2` | `#17161F` | Secondary background |
| `--surface` | `#1E1C28` | Cards, panels |
| `--surface-2` | `#272433` | Raised / hover |
| `--line` | `#322E3F` | Borders |
| `--line-soft` | `#262232` | Hairlines, grid |

### Text

| Token | Hex | Use |
| --- | --- | --- |
| `--text` | `#F0EDF5` | Primary text |
| `--text-muted` | `#A39FB2` | Secondary text |
| `--text-dim` | `#6B6679` | Tertiary, disabled |

### Accents

| Token | Hex | Use |
| --- | --- | --- |
| `--coral` | `#FF5A4D` | Hero. Primary action, "playing", lit state |
| `--coral-bright` | `#FF7A6E` | Glow, highlight, hover |
| `--coral-deep` | `#E03E2F` | Pressed; coral-as-text on light |
| `--violet` | `#9A8CF5` | Secondary. Recaps, links, "paused" |
| `--violet-deep` | `#6E5FD6` | Pressed violet |
| `--green` | `#46C28A` | Success, completed |
| `--red` | `#E5484D` | Destructive only (rare, outline-only) |

### Status colors (no-guilt mapping)

| Status | Color | Note |
| --- | --- | --- |
| Backlog | `#8A8699` | Neutral |
| Playing | `--coral` | Lit / active |
| Paused | `--violet` | Resting |
| Completed | `--green` | Done |
| Set aside | `--text-dim` | Quietly shelved, never red |

### Accessibility

- Body text on `--bg`/`--surface` clears WCAG AA
- For text on coral fill, use `--bg` (ink-on-coral > white-on-coral)
- Never encode status by color alone — always pair with label or icon

### Light mode (deferred)

A light palette is sketched in the canonical guide (`--bg #F5F4F8`, `--surface #FFFFFF`, `--text #1A1822`; hero coral darkens to `--coral-deep`, violet to `--violet-deep`), but **light mode is not implemented** — the app ships dark-first only. Status: **deferred** (recorded here so the gap reads as a deliberate decision, not an unfinished promise).

---

## 4. Typography

| Role | Family | Weights | Where |
| --- | --- | --- | --- |
| Display | Outfit | 400, 500, 700 | Wordmark, headings, verdicts, big numbers |
| Body / UI | Inter | 400, 500, 600 | All interface text and paragraphs |
| Data (mono) | JetBrains Mono | 400, 500 | Timestamps, durations, counts (sparingly) |

All open-source. Loaded from Google Fonts on web; bundled or via `google_fonts` on Flutter.

### The recap label

Signature style: play glyph + uppercase, letter-spaced in Outfit. E.g. `PREVIOUSLY ON`, `TONIGHT'S PICK`, `WHERE YOU LEFT OFF`.

---

## 5. Voice & tone

Talk like the friend who knows your backlog. Concise. A little dry. Never hype, never guilt.

### Preferred lexicon

| Prefer | Over |
| --- | --- |
| Daily Pick / tonight's pick | Deploy |
| Library / backlog | PlaySession log |
| Session | PlaySession (in UI) |
| Recap / "Previously on..." | Recap / intel |
| Your wrap-up / where you left off | WrapUp |
| Set aside | Dropped / abandoned |

### Rules

- Lead with the help, flavor the chrome
- No guilt, ever. No streaks, no idle-shaming
- Respect autonomy — suggest, don't command
- Admit uncertainty — weak context = say so

The data model and code keep the tactical metaphor (`play session`, `recap`, `wrap-up`) — that's precise and already built. **User-facing copy leans warm by default** (the table above); the tactical flavor is reserved for an opt-in "Operator mode" easter egg.

> **TODO (owner decision — pending):** "Operator mode" is the only place the brand deliberately embraces the tactical register. Decide whether to **keep** it (opt-in easter egg), **rename** it (a warmer label for the same toggle), or **remove** it. Not resolved here — needs the owner's sign-off.
>
> **Resolved:** the product was renamed from DailyLoadout to **Slate**. The wordmark, package namespace, and all identifiers now use `slate`. The wordmark/lockup SVGs were re-typeset to "slate" but still need a proper design pass for kerning and sizing.

---

## 6. Asset locations

### Web (`packages/web/app/public/`)

| File | Source | Purpose |
| --- | --- | --- |
| `favicon.svg` | Brand mark as SVG | Modern browsers |
| `favicon.ico` | Brand mark as ICO | Legacy browsers |
| `og-image.png` | 1200x630 | Open Graph / Twitter card previews |
| `apple-touch-icon.png` | 180x180 | iOS home screen bookmark |

The `index.html` `<head>` includes all necessary meta tags for OG, Twitter card, and apple-touch-icon.

### Flutter app (`packages/mobile/`)

| File | Purpose |
| --- | --- |
| `assets/icon/app-icon.png` | 512x512 source icon |
| Generated via `flutter_launcher_icons` | iOS/Android platform icons |

To regenerate icons after changing the source:

```bash
cd packages/mobile && dart run flutter_launcher_icons
```

Configuration is in `pubspec.yaml` under `flutter_launcher_icons:`.

#### Splash (not wired yet)

A splash asset using the **lineup** device (one lit coral slot on Midnight) is exported to `docs/brand/splash.png` (source: `branding/social/slate-splash.svg`). To wire it with [`flutter_native_splash`](https://pub.dev/packages/flutter_native_splash) later — **not installed or generated yet; pending owner OK** — copy the PNG into the mobile package assets and add to `pubspec.yaml`:

```yaml
flutter_native_splash:
  color: "#121119"          # Midnight base
  image: assets/splash/splash.png  # the lineup device, centered
  android_12:
    color: "#121119"
    image: assets/splash/splash.png
```

Then run `dart run flutter_native_splash:create`. Until then, the app has no branded splash.

### Store assets

Exported from `branding/` to `docs/brand/`:

| Asset | File | Spec / use |
| --- | --- | --- |
| Android adaptive icon (foreground) | `docs/brand/adaptive-foreground.png` | The mark inside the 66% safe zone. Pair with `adaptive_icon_background: "#121119"` (Midnight) in `flutter_launcher_icons`; copy the PNG into the mobile assets and run `flutter_launcher_icons`. |
| Google Play feature graphic | `docs/brand/feature-graphic.png` | 1024×500 store banner (lockup + tagline + lineup). |

```yaml
flutter_launcher_icons:
  adaptive_icon_background: "#121119"
  adaptive_icon_foreground: assets/icon/adaptive-foreground.png
```

**Follow-up (not generated yet):** App Store screenshot frame templates — per-device frames (6.7", 6.1", 12.9" iPad) with a Midnight backdrop and a coral caption band, into which marketing screenshots are dropped. Track as a separate design task.

### Shared (`docs/brand/`)

Tracked, canonical copies of brand assets for README, docs, and social:

| File | Purpose |
| --- | --- |
| `readme-hero.png` | README banner (1280x430) |
| `readme-hero@2x.png` | Retina version |
| `og-image.png` | Canonical OG image |
| `slate-mark.svg` | Color mark |
| `slate-mark-mono.svg` | Mono mark |
| `slate-wordmark.svg` | Wordmark |
| `slate-lockup-horizontal.svg` | Horizontal lockup |
| `lockup-2x.png` | Raster lockup for slides |
| `mark-128.png`, `mark-256.png`, `mark-512.png` | Raster marks |

### Untracked source (`branding/`)

The `branding/` directory is gitignored (the owner's brand studio). It holds the SVG sources, the export script (`branding/export.py`), and the canonical full guide (`branding/BRAND.md`). Running the script rasterizes to `branding/_export/` and then copies the versioned artifacts into the tracked locations above (`docs/brand/` and `packages/web/app/public/`).

---

## 7. README hero

Use in the root `README.md`:

```md
<p align="center">
  <img src="./docs/brand/readme-hero.png" alt="Slate" width="100%" />
</p>
```

---

## 8. Design tokens (CSS)

```css
:root {
  --bg:         #121119;
  --bg-2:       #17161F;
  --surface:    #1E1C28;
  --surface-2:  #272433;
  --line:       #322E3F;
  --line-soft:  #262232;

  --text:       #F0EDF5;
  --text-muted: #A39FB2;
  --text-dim:   #6B6679;

  --coral:        #FF5A4D;
  --coral-bright: #FF7A6E;
  --coral-deep:   #E03E2F;
  --coral-wash:   rgba(255, 90, 77, 0.13);
  --violet:       #9A8CF5;
  --violet-deep:  #6E5FD6;
  --violet-wash:  rgba(154, 140, 245, 0.12);
  --green:        #46C28A;
  --red:          #E5484D; /* destructive, outline-only, rare */

  /* Status (no-guilt mapping) */
  --status-backlog:   #8A8699;
  --status-playing:   var(--coral);
  --status-paused:    var(--violet);
  --status-completed: var(--green);
  --status-setaside:  var(--text-dim);

  --font-display: 'Outfit', system-ui, sans-serif;
  --font-body:    'Inter', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', ui-monospace, monospace;

  --radius-slot: 14px;
  --radius-card: 16px;
}
```

---

## 9. Brand devices

1. **The slot** — rounded-square cell. Lit (coral) = selected; outlined = waiting
2. **The controller** — universal "play". The gamepad silhouette lives in the mark and the pick (the `▸` glyph remains only as the recap-label typographic device)
3. **The lineup** — row of slots, one lit. For empty states, loading, splash
4. **The spotlight** — soft coral glow behind tonight's pick. One per screen
5. **The recap label** — `PREVIOUSLY ON` in Outfit, uppercase, letter-spaced

**One coral focal point per screen.** Coral is a spotlight; more than one and nothing is lit.

---

## 10. Motion

- Durations 120-200 ms; ease-out for entrances
- No bouncy overshoot, no confetti (anti-gamification)
- The daily pick lock-in: single scale 0.98 -> 1 with a one-shot coral glow
- Respect `prefers-reduced-motion`

---

## 11. Iconography

- Line icons, 1.75 px stroke on 24 grid, rounded caps
- Outline by default; filled only for active/selected item (paired with coral)
- Avoid weapon, target, military, or rank metaphors
