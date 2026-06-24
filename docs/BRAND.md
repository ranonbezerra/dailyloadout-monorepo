# DailyLoadout - Brand Standards

**Version:** 1.0 | **Direction:** Night Den x Coral | **Last updated:** 2026-06

---

## 1. Identity

**Tagline:** *Less deciding. More playing.*
**Voice line:** *What's the move?*

DailyLoadout is the companion that knows your backlog and hands you the right game for tonight — then catches you up on where you left off, like a "previously on..." before the episode.

**We are:** calm, decisive, warm, sharp, honest.
**We are not:** gamified, guilt-inducing, military/tactical, loud, corporate.

---

## 2. Logo

### The mark — "The Pick"

A single lit slot with a play triangle: the one game, chosen and ready. Coral means lit / chosen for now.

| Asset | File | Use |
| --- | --- | --- |
| Mark (color) | `docs/brand/dailyloadout-mark.svg` | Primary mark |
| Mark (mono) | `docs/brand/dailyloadout-mark-mono.svg` | Single-color contexts |
| Wordmark | `docs/brand/dailyloadout-wordmark.svg` | Text-only branding |
| Lockup | `docs/brand/dailyloadout-lockup-horizontal.svg` | Header, README, nav |
| Lockup raster | `docs/brand/lockup-2x.png` | Slides, social |
| Mark raster | `docs/brand/mark-128.png`, `mark-256.png`, `mark-512.png` | Avatars, previews |

### Wordmark rules

`dailyloadout` — always lowercase, one word. Set in **Outfit** with `daily` in Regular (400) and `loadout` in Bold (700).

### Rules

- Clear space: margin equal to the height of the play triangle on all sides
- Min size: mark 16 px; horizontal lockup 120 px wide
- On dark backgrounds (default). On light, use the mono mark
- Never recolor the play triangle, add bevels/shadows, stretch, or rotate
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

---

## 4. Typography

| Role | Family | Weights | Where |
| --- | --- | --- | --- |
| Display | Outfit | 400, 500, 700 | Wordmark, headings, verdicts, big numbers |
| Body / UI | Inter | 400, 500, 600 | All interface text and paragraphs |
| Data (mono) | JetBrains Mono | 400, 500 | Timestamps, durations, counts (sparingly) |

All open-source. Loaded from Google Fonts on web; bundled or via `google_fonts` on Flutter.

### The recap label

Signature style: play glyph + uppercase, letter-spaced in Outfit. E.g. `PREVIOUSLY ON`, `TONIGHT'S LOADOUT`, `WHERE YOU LEFT OFF`.

---

## 5. Voice & tone

Talk like the friend who knows your backlog. Concise. A little dry. Never hype, never guilt.

### Preferred lexicon

| Prefer | Over |
| --- | --- |
| Loadout / tonight's pick | Deploy |
| Library / backlog | Mission log |
| Session | Mission (in UI) |
| Recap / "Previously on..." | Briefing / intel |
| Your note / where you left off | Debrief |
| Set aside | Dropped / abandoned |

### Rules

- Lead with the help, flavor the chrome
- No guilt, ever. No streaks, no idle-shaming
- Respect autonomy — suggest, don't command
- Admit uncertainty — weak context = say so

---

## 6. Asset locations

### Web (`packages/web/public/`)

| File | Source | Purpose |
| --- | --- | --- |
| `favicon.svg` | Brand mark as SVG | Modern browsers |
| `favicon.ico` | Brand mark as ICO | Legacy browsers |
| `og-image.png` | 1200x630 | Open Graph / Twitter card previews |
| `apple-touch-icon.png` | 180x180 | iOS home screen bookmark |

The `index.html` `<head>` includes all necessary meta tags for OG, Twitter card, and apple-touch-icon.

### Flutter app (`packages/app/`)

| File | Purpose |
| --- | --- |
| `assets/icon/app-icon.png` | 512x512 source icon |
| Generated via `flutter_launcher_icons` | iOS/Android platform icons |

To regenerate icons after changing the source:

```bash
cd packages/app && dart run flutter_launcher_icons
```

Configuration is in `pubspec.yaml` under `flutter_launcher_icons:`.

### Shared (`docs/brand/`)

Tracked, canonical copies of brand assets for README, docs, and social:

| File | Purpose |
| --- | --- |
| `readme-hero.png` | README banner (1280x430) |
| `readme-hero@2x.png` | Retina version |
| `og-image.png` | Canonical OG image |
| `dailyloadout-mark.svg` | Color mark |
| `dailyloadout-mark-mono.svg` | Mono mark |
| `dailyloadout-wordmark.svg` | Wordmark |
| `dailyloadout-lockup-horizontal.svg` | Horizontal lockup |
| `lockup-2x.png` | Raster lockup for slides |
| `mark-128.png`, `mark-256.png`, `mark-512.png` | Raster marks |

### Untracked source (`brand/`)

The `/brand/` directory is gitignored. It contains SVG sources, export scripts, and the full brand guide. Assets are exported from there and copied into the tracked locations above.

---

## 7. README hero

Use in the root `README.md`:

```md
<p align="center">
  <img src="./docs/brand/readme-hero.png" alt="DailyLoadout" width="100%" />
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
  --red:          #E5484D;

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
2. **The play triangle** — universal "play". Lives in mark, primary buttons, the pick
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
