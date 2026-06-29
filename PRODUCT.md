# Slate — Product Document

**Version:** 2.0 (showcase / open-source)
**Last updated:** 2026-05
**Audience:** humans + AI agents working on the project

## Changelog from v1.1 (original commercial spec)

This is an adapted version of the original product. The product premise is identical; the delivery vehicle is different.

**Removed (was commercial-only):**
- Freemium tier, Plus monthly (R$14,90/mo), Pro Lifetime (R$299)
- AI quotas, soft-throttle, `ai_usage_meter`, `subscriptions`, `entitlements_cache`
- StoreKit 2 and App Store Server API
- App Store submission, TestFlight, ASO
- CloudKit sync (Plus-only feature)
- Sign in with Apple, APNs

**Changed:**
- iOS-only (Swift + SwiftUI) → **Flutter mobile** (iOS, Android)
- Amazon Bedrock (Claude Sonnet/Haiku) → **Ollama local-first** (Gemma 3 4B + 12B), Bedrock as opt-in fallback
- OpenAI Whisper API → **faster-whisper local** in-process
- VisionKit on-device OCR → **multimodal LLM** (Gemma 3 vision) on backend
- Apple-only auth → **email/password + JWT** (via fastapi-users), Google OAuth opt-in
- AWS-hosted infra → **Docker Compose self-hosted**, with deployment guides for Fly.io/Railway/VPS

**Added (showcase-specific):**
- **Web dashboard** (`packages/web/`) — analytics and admin views, not part of original spec
- **Single-user mode** via env var — for personal self-hosting without auth friction

---

## 1. Vision and purpose

Slate is an app to manage your gaming backlog. The problem is familiar: you own 60 games, you play 2, you forget the others. Every time you turn on the console, you spend half the session deciding between "continue that RPG" and "try something new" — and indecision consumes the gaming time. Worse: when you return to a game after 3 weeks, you've forgotten where you stopped, what the quest was, what build you were running.

Slate solves this with three core ideas:

1. **Frictionless capture.** Voice, photo, free text. You don't type "Hollow Knight, Switch, bought 2022, metroidvania, ~30h." You say "got Hollow Knight" and the app fills the rest.

2. **PlaySession recap.** Before each gaming session, the app generates a personalized "previously on...": what you were doing, your objective, suggested next action. Like a TV series recap.

3. **Daily Pick.** Three quick questions (mood, available time, mental energy) → one game suggestion. You don't choose; the app does. Indecision drops to zero.

### Central thesis

The gaming backlog is not an organization problem — it's a **decision** problem. Apps like HowLongToBeat or Backloggd solve cataloging. Slate solves "what should I play right now, and where do I pick up from?"

### Product metaphor

Each gaming session is a **play session**. The app is your **tactical operator** — it keeps a sheet on each active operation, recaps you before the play session, wraps you up after. The "daily Pick" is the game selected for today's play session.

### Inspiration

- **HowLongToBeat** — catalog reference, but static.
- **Backloggd / Grouvee** — social, but focused on post-game reviews.
- **Anti-pattern: Steam, PSN, Nintendo Network** — all have data, none act on it. Slate is the **opposite of stats display**; it's a decision layer.

### Competitive differentiators

1. Zero-friction capture (voice + photo + text).
2. Personalized LLM recap based on past sessions.
3. Daily Pick removes indecision.
4. **No guilt mechanics** — no streaks, no "you haven't played X days", no hours ranking. Dropping a game is a legitimate decision, not a failure.
5. **No Steam/PSN/Nintendo integration.** Deliberate decision — APIs are restrictive, require platform login that breaks UX, and aggravate the problem (importing 200 games you never opened). Capture is manual with AI assistance.

> **Metadata catalog ≠ account integration.** Bulk library import (Epic 14) lets a user *photograph* their library list and reads the text with OCR. This is **not** an account link: no Steam/PSN/Nintendo login, no playtime, achievements, or library sync via official APIs. Cleaning the extracted titles against a canonical games-metadata catalog (IGDB/RAWG) is a reference-dictionary lookup, not a connected account — a different category entirely. The user's independence from platform accounts stays intact.

### Non-goals

- Not a social network. No feeds, no friends, no comments.
- Not a replacement for HowLongToBeat (no playtime database).
- No platform API integration (Steam/PSN/Nintendo) — see thesis above.
- Not an achievement/trophy tracker.
- Not a store. Doesn't recommend purchases.

---

## 2. Glossary

These distinctions are precise — don't conflate them.

- **Game ≠ LibraryEntry.** Game is the canonical global record (Hollow Knight). LibraryEntry is "Ranon's Hollow Knight on Switch." Same Game on two platforms = two LibraryEntries.

- **PlaySession = a gaming session.** Has start, end, wrap-up. **Don't confuse with "in-game objective"** — that's `play_session_next_action`, a field on LibraryEntry.

- **Three concepts of "pause" — never confuse:**
  - **Ending a play session** = play session ends normally, with wrap-up.
  - **Leaving without ending** (`ended_via='paused_app'`) = play session ends without wrap-up.
  - **Pausing a LibraryEntry** (`status='paused'`) = a decision about the **game**, not the session.

- **Recap exists only inside a PlaySession.** It's not a standalone artifact. It's the "previously on" generated before play.

- **Pick = daily suggestion. Pick ≠ PlaySession.** User accepts a Pick → it creates a PlaySession.

- **Capture = the operation of adding a Game.** Not the Game itself. Has a state machine: `queued → processing → review → (partially_committed | committed | failed | cancelled)`.

- **Recap uses only ended play sessions.** The currently active play session does NOT enter the context.

- **`igdb_id` is nullable.** Manually-added games use `slug` as dedupe key, with `metadata_source='manual'`.

- **`play_session_next_action` is denormalized** on `library_entries` — updated by the `wrap_up_processor` worker. Recomputed when the most recent play session is deleted.

- **One active play session per user, globally.** Enforced in the database via partial unique index on `play sessions(user_id) WHERE ended_at IS NULL`.

- **Audio retention:** S3 audio deleted when capture reaches terminal status. Storage lifecycle policy as fallback (24h).

---

## 3. Core flows (user-facing)

### 3.1 First-run experience

1. User installs the app, opens it.
2. **Single-user mode (`SINGLE_USER_MODE=true`)**: skip signup; one user is created via env. User goes straight to library.
3. **Multi-user mode (default)**: signup screen → email + password → email verification (if SMTP configured) → library.

### 3.2 Capture by voice

1. User taps the mic button.
2. Records up to 60s. Says: "I got Hollow Knight and Hades for the Switch."
3. Audio uploads to backend; capture enters `queued`.
4. Worker:
   - Transcribes audio (faster-whisper)
   - Sends transcript to LLM (Gemma 4B) with capture-parse prompt
   - LLM returns structured candidates: `[{"title": "Hollow Knight", "platform_hint": "switch"}, {"title": "Hades", "platform_hint": "switch"}]`
   - Queries IGDB for each candidate (if configured)
   - Creates `capture_candidates` rows with `pending` status
   - Marks capture as `review`
   - Deletes the audio file
5. App polls capture status, sees `review`, opens review screen.
6. User confirms each candidate → library entries created.

### 3.3 Capture by photo

1. User taps the camera button, takes a photo of a game cover or a shelf.
2. Photo uploads; capture enters `queued`.
3. Worker sends image directly to multimodal LLM (Gemma 12B vision) with a vision-specific prompt.
4. LLM extracts up to 12 game titles from the image.
5. Remaining flow identical to voice capture (review → confirm).

### 3.4 Capture by text

1. User types: "got hollow knight and hades on switch."
2. No transcription step; goes straight to LLM parse.
3. Otherwise identical.

### 3.5 Starting a play session with recap

1. User opens a LibraryEntry, taps "Start PlaySession".
2. Backend validates: user has no other active play session. Creates play session row.
3. Backend queries last 3 ended play sessions of the same LibraryEntry with non-null `extracted_state`.
4. LLM (Gemma 12B) generates recap using the recap prompt.
5. **Anti-hallucination check**: extract proper nouns and numbers from output; verify ≥70% overlap with input context. If not, flag as `suspicious_recap` and add disclaimer.
6. App shows recap screen: "Previously on Hollow Knight..." + "Start" / "Skip".
7. User plays. Eventually returns to the app.

### 3.6 Ending a play session with wrap-up

1. User taps "End PlaySession".
2. App shows wrap-up screen: free-text input. "Beat the Mantis Lords. Got the cloak. Heading to Greenpath next, need to find the Mothwing Cloak."
3. App submits wrap-up.
4. Backend marks play session `ended_via='wrap_up_completed'`.
5. `wrap_up_processor` worker:
   - LLM extracts structured state: `{"location": "Greenpath", "next_action": "find Mothwing Cloak", "level": null}`
   - Saves to `play sessions.extracted_state`
   - Updates `library_entries.play_session_next_action` (denormalized for fast read)
6. Next recap for this LibraryEntry uses this wrap-up as context.

### 3.7 Daily Pick

1. User taps "What's the move?" on home screen.
2. App asks three questions:
   - **Mood**: focused / tired / social / creative
   - **Time available**: 15min / 30min / 1h / 2h+ / open-ended
   - **Mental energy**: low / medium / high
3. App POSTs to `/v1/picks`.
4. Backend:
   - Lists eligible LibraryEntries (status in backlog/playing/paused, no ended play session < 12h ago for that entry)
   - LLM picks one with reasoning
   - **Validates returned public_id exists in candidate list.** If not, reroll once. Second failure → 422.
5. App shows result: game card + reasoning. "Hollow Knight — you have 1h, your mental energy is high, and you stopped right before a boss fight. Good moment to push through."
6. User accepts → play session auto-starts with recap. Rejects → pick marked `action='rejected'`.

### 3.8 Auto-clamp of forgotten play sessions

A cron runs hourly. For each play session with `ended_at IS NULL` and `started_at < now() - 8h`:

- Marks `ended_via='auto_clamp_8h'`
- Sets `ended_at = started_at + 8h`
- No wrap-up extracted.

Prevents zombie play sessions blocking the "one active play session per user" constraint.

---

## 4. Web dashboard (the showcase delta)

The web (`packages/web/`) is the **personal admin panel of the self-hosting user**. It is NOT a SaaS operator dashboard. It exists because some views are better on a large screen than on mobile.

### Views

- **Overview** — KPI cards: total games, status breakdown, play sessions in last 30 days, average play session duration.
- **Library** — data grid with sort, filter, inline edit. The "spreadsheet view" of your backlog.
- **Analytics – Heatmap** — calendar-style heatmap (GitHub contributions style) of play sessions.
- **Analytics – Genres** — pie/donut of estimated playtime by genre.
- **Analytics – Platforms** — distribution across consoles/PC.
- **PlaySession Timeline** — chronological list of play sessions with expandable wrap-ups.
- **Captures** — list of all captures with their state, useful for debugging AI extractions.
- **Settings** — Ollama models in use, IGDB status, storage backend, single-user mode toggle.

### Stack

- **Bun** as runtime and package manager
- **Vite** as bundler
- **React 19** + **TypeScript**
- **Mantine v8** for UI components (DataTable, Charts, Forms)
- **TanStack Query** for server state
- **react-router-dom** for routing

---

## 5. Risks and open decisions

### Risks

1. **Ollama hardware requirements vary.** Gemma 12B needs ~8GB VRAM or generous RAM with CPU offload. Self-hosters with smaller hardware need a documented downgrade path (e.g., everything on Gemma 4B with reduced recap quality).

2. **Hallucination in recap is the critical UX risk.** User returns after 3 weeks, recap invents "you were fighting boss Harkenburg" — destroys trust instantly. Mitigated aggressively: restrictive prompt, term validation against previous wrap-ups, fallback to "generic recall" tone when context is weak.

3. **Multimodal LLM photo capture fails on stylized covers.** Souls-style logos, heavily stylized fonts → LLM may miss. Plan B: if confidence < 0.5, prompt user to retake or switch to text capture.

4. **IGDB rate limits and API changes.** Mitigated with aggressive caching, RAWG documented as fallback.

5. **Tactical metaphor (play session, recap, operator) may alienate casual users.** Mitigated with easter egg copy ("play session: kill boredom") and an optional tone setting (reserved for v1.1).

### Open decisions

- [ ] Analytics provider for repo usage (PostHog self-hosted vs none in v1) — currently none.
- [ ] Where to host the personal instance (Fly.io vs Hetzner VPS) — docs cover both.
- [ ] Recording length limit (60s default) — test with real usage.
- [ ] Audio retention policy — currently "delete immediately after Whisper". A future "replay original capture" feature would force a change.
- [ ] Whisper model size — start with `base`, document `small`/`medium` trade-offs.
- [ ] Cover art override — for v1, always use IGDB cover if available. User customization in v1.1+.

---

## 6. Definition of Done — v1.0

The vitrine (showcase) is ready to announce when:

- [ ] User can sign up, log in, and make first capture in < 5 minutes from a fresh clone.
- [ ] Single-user mode works end-to-end (signup disabled, default user created).
- [ ] Voice capture works in < 30s end-to-end (record → transcribe → LLM → IGDB → review) on commodity hardware (no GPU).
- [ ] Photo capture detects ≥ 1 game correctly in 80% of modern cover photos (manual test on 30 samples).
- [ ] Shelf capture works for up to 12 games. Limit enforced hard.
- [ ] Text capture and manual entry work. Manual entry creates Game with `metadata_source='manual'` and dedupes by slug.
- [ ] Capture review supports partial commit: user resolves some candidates, exits, comes back later.
- [ ] Recap is coherent in 90% of cases (manual evaluation of 20 samples with real wrap-ups). Suspicious terms are logged.
- [ ] Daily Pick produces sensible suggestions (human validates 20 cases). 100% of returned UUIDs exist in user's library.
- [ ] PlaySession lifecycle complete: start → wrap-up → next recap uses context.
- [ ] One-active-play session constraint enforced at the database level (not just the app).
- [ ] `play_session_auto_clamp_8h` job works: forgotten play session > 8h is closed with `ended_via='auto_clamp_8h'`.
- [ ] Multi-device basic sync via backend: same user on two devices sees consistent library after pull-to-refresh.
- [ ] Delete account works (soft delete) — for multi-user mode.
- [ ] CI green on all three packages.
- [ ] Test coverage ≥ 70% in `services/` and `repositories/` of API. Quota-free auth and capture state machine ≥ 90%.
- [ ] README has demo GIF.
- [ ] ARCHITECTURE.md documents the four highlight decisions (LLM abstraction, anti-hallucination, state machines, denormalization rationale).
- [ ] OpenAPI served at `/docs` via Scalar.
- [ ] At least three "Future" issues open on GitHub for visible roadmap.
