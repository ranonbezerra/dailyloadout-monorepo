# DailyLoadout — Roadmap

Execution plan organized in weekend-sized epics. Each epic ends in a **demonstrable state** — if the weekend runs out, descope the epic rather than ending in a broken halfway state.

The repository is public from Epic 0 onward. Every commit and PR is part of the narrative. A recruiter cloning at any point should see something that runs.

---

## Calendar overview

| Weekend | Epic | Focus |
|---|---|---|
| 1 | Foundation | Setup, Docker Compose, 3 packages booting |
| 2 | Auth + Users | fastapi-users, JWT rotation, login on app + web |
| 3 | Library | Manual CRUD, schema working end to end |
| 4 | Capture (text) + IGDB | First AI flow, simplest input |
| 5 | Capture (voice) | faster-whisper local |
| 6 | Capture (photo) | Multimodal LLM (vision) |
| 7 | Mission + Briefing | **Anchor feature** — anti-hallucination |
| 8 | Daily Loadout | Second AI feature with UUID validation |
| 8.5 | Async Debrief (Taskiq) | Decouple LLM extraction from debrief flow |
| 9 | Stats + Web analytics | Where the dashboard shines |
| 10 | Polish + Launch | README final, demo GIF, announcement |
| 11 | Deep Research Briefing | Web-augmented spoiler-free suggestions (v1.1+) |

Total: **10 weekends ≈ 2.5 months** for v1.0 (assuming 8–12 productive hours per weekend). Epic 11 is a v1.1+ enhancement.

---

## Epic 0 — Foundation (Weekend 1)

**Goal:** public repo, empty but professional, with Docker Compose booting "hello world" across all three packages.

### Tasks

- [ ] Create `dailyloadout-monorepo` on GitHub, public, MIT license
- [ ] Initial README (work-in-progress version): problem, vision, stack, "WIP" status badge
- [ ] `.gitignore` for Python, Flutter, Node, IDE files
- [ ] `docker-compose.yml` with 4 services: postgres, redis, ollama, api (placeholder returning `{"status": "ok"}` at `/health`)
- [ ] `docker-compose.dev.yml` with hot-reload
- [ ] `.env.example` complete (every env var from ARCHITECTURE.md §7)
- [ ] `packages/api/pyproject.toml` with Poetry, Python 3.14, base deps (FastAPI, Pydantic v2, SQLAlchemy, asyncpg, alembic, arq, structlog, ruff, mypy, pytest, pytest-asyncio)
- [ ] `packages/api/src/dailyloadout/main.py` with minimal app factory + `/health`
- [ ] `packages/app/` initialized via `flutter create`, configured for iOS/Android. Renders "DailyLoadout WIP"
- [ ] `packages/web/` initialized with Vite (Bun), React 19, TypeScript, Mantine v8. Renders empty layout on `localhost:3200`
- [ ] GitHub Actions: three separate workflows (`ci-api.yml`, `ci-app.yml`, `ci-web.yml`) running lint + test on every PR
- [ ] Issue templates (bug, feature, question)
- [ ] PR template
- [ ] README with CI badges

### Definition of Done

- `docker compose up` brings everything online (API responds 200 at `/health`)
- `cd packages/app && flutter run -d <device>` opens the app
- `cd packages/web && bun run dev` opens the web
- CI is green on all three workflows
- README explains how to run each package

### Why this epic before any feature

The vitrine starts with the **first impression**. A recruiter cloning the repo at month 1 or month 6 should have the same experience: "I cloned, `docker compose up`, it worked." This foundation stays stable while features change.

---

## Epic 1 — Auth + Users (Weekend 2)

**Goal:** signup, login, and logout work end-to-end across all three packages.

### Tasks

- [ ] PostgreSQL schema: `users`, `oauth_identities`, `refresh_tokens` via Alembic migration
- [ ] Integrate `fastapi-users[sqlalchemy]`
- [ ] Endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`
- [ ] JWT access 15min + refresh 30d with rotation
- [ ] Bcrypt 12 rounds (fastapi-users default)
- [ ] Rate limit on `/auth/login` (10 attempts/min via slowapi)
- [ ] `SINGLE_USER_MODE` env: if true, disables signup, creates single user via env on startup
- [ ] Pytest covering: valid signup, duplicate signup, valid login, invalid login, valid refresh, revoked refresh, rate limit
- [ ] App: BLoC `AuthBloc` with states `Unauthenticated | Authenticating | Authenticated | AuthError`
- [ ] App: screens Login, Register, splash with auto-redirect
- [ ] App: `flutter_secure_storage` for refresh token, in-memory for access token
- [ ] App: dio interceptor that auto-refreshes access on 401
- [ ] Web: login screen with Mantine `<TextInput>`, `<PasswordInput>`, `<Button>`
- [ ] Web: stores tokens in httpOnly cookie (preferred) or localStorage (simpler; document the choice)
- [ ] Web: TanStack Query setup with `useAuth` hook

### Definition of Done

- User registers via app, logs in, sees a "logged in" placeholder
- User registers via web, logs in, sees a dashboard placeholder
- User closes the app, reopens, stays logged in (refresh works)
- 11 failed login attempts in 1 minute return 429
- Pytest auth coverage ≥ 85% for the auth module

### Technical highlight (worth a paragraph in ARCHITECTURE.md)

> **Auth strategy:** access token JWT 15min in memory, refresh token 30d in secure storage with rotation on every use. Trade-off: short access reduces the exposure window if leaked; rotation invalidates the previous refresh, so if a leaked refresh is used, the next legitimate use fails and forces re-login (signal of compromise).

---

## Epic 2 — Library basics (Weekend 3)

**Goal:** manual game CRUD in the app. No AI yet. Proves the modeled domain works.

### Tasks

- [ ] Schema: `games`, `platforms`, `library_entries` via migration
- [ ] Seed platforms (Switch, PS5, PS4, Xbox Series, PC-Steam, PC-GOG, PC-Epic, iOS, Android, Other)
- [ ] Endpoints:
  - `POST /v1/games` (manual create)
  - `GET /v1/games/search?q=` (trigram fuzzy search)
  - `GET /v1/library` (paginated, filters by status/platform)
  - `POST /v1/library` (add from existing game or create new)
  - `PATCH /v1/library/{public_id}` (status, notes, etc.)
  - `DELETE /v1/library/{public_id}` (hard delete for now)
- [ ] Pytest for each endpoint
- [ ] App: screens `LibraryListPage` (list with filters), `LibraryDetailPage`, `AddGameManualPage`
- [ ] App: BLoC `LibraryBloc` with `LoadLibrary`, `AddEntry`, `UpdateEntry`, `DeleteEntry`
- [ ] App: thoughtful empty state ("Your backlog is empty. Add your first game.")
- [ ] Web: `/library` route with Mantine DataTable, filters, basic inline edit

### Definition of Done

- User adds a manual game via app, it appears in the list
- User edits status (backlog → playing) via app, change reflects in web on reload
- User deletes a game, it disappears
- Paginated list works with 50+ games
- Web shows the same library for the logged-in user

### Why this epic before AI

Before spending a weekend configuring Ollama and prompts, prove that **CRUD on the modeled domain** works. If the schema has bugs, discover them here cheaply. **Order: schema → CRUD → AI on top.** Inverting this order will hurt.

---

## Epic 3 — Capture (text) + IGDB (Weekend 4)

**Goal:** first light AI flow. User types free text, LLM extracts candidates, IGDB enriches metadata.

### Tasks

- [ ] Schema: `captures`, `capture_candidates` via migration
- [ ] `infrastructure/llm/`:
  - `AbstractLLMClient` with `parse_capture_text(text: str) -> list[CaptureCandidate]`
  - `OllamaClient` via HTTP
  - `DummyLLMClient` returning fixed output for tests
  - `factory.py` based on env
- [ ] Prompt `prompts/capture_parse.j2` with PT-BR instructions + few-shot examples
- [ ] `infrastructure/igdb/`:
  - Client with Twitch token auth (cached in Redis)
  - `search_game(title: str) -> list[IGDBGame]`
  - Internal rate limit (4 req/s)
  - If `IGDB_CLIENT_ID` empty, raises `IGDBNotConfigured` (expected, not an error)
- [ ] Worker `capture_processor.py` with arq:
  1. Pick up queued capture
  2. Call LLM
  3. For each extracted game, search IGDB if active
  4. Create capture_candidates
  5. Mark capture `status='review'`
- [ ] Endpoints:
  - `POST /v1/captures/text` (creates queued capture)
  - `GET /v1/captures/{public_id}` (status + candidates)
  - `POST /v1/captures/{public_id}/candidates/{cid}/confirm` (creates library_entry, `confirmed`)
  - `POST /v1/captures/{public_id}/candidates/{cid}/reject`
- [ ] Pytest with `DummyLLMClient` and mocked IGDB
- [ ] App: screens `CaptureTextPage` (large textarea), `CaptureReviewPage` (candidate cards)
- [ ] App: BLoC `CaptureBloc` with polling of status (every 2s while `processing`)
- [ ] App: screen `CaptureChoicePage` (voice/photo/text/manual — voice and photo disabled for now)
- [ ] Web: `/captures` route listing captures (admin overview)

### Definition of Done

- User opens app, taps Capture, picks Text, types "got Hollow Knight and Hades for the Switch", confirms
- Within 30s, review screen appears with 2 candidates
- User confirms both → both go to library on Switch
- IGDB enriches cover + summary (if active)
- Without IGDB, still works (no cover, `metadata_source='llm_extracted'`)
- Capture module coverage ≥ 80%

### Technical highlight

> **Why a state machine for captures:** captures cross three systems (LLM, IGDB, user review), each with its own failure modes. Modeling as a state machine (`queued → processing → review → committed/partially_committed/failed/cancelled`) makes recovery and retries explicit. The worker is idempotent: re-running processing on a stuck capture is safe.

---

## Epic 4 — Capture (voice) + Whisper local (Weekend 5)

**Goal:** integrate local STT. Same flow, but with audio.

### Tasks

- [ ] `infrastructure/stt/`:
  - `AbstractSTTClient` with `transcribe(audio_path: str, language: str = "pt") -> str`
  - `WhisperLocalClient` using `faster-whisper`
  - `DummySTTClient`
  - `factory.py`
- [ ] Whisper model downloaded to Docker volume (script `infra/scripts/download_whisper.sh`)
- [ ] Worker `capture_processor.py` extends logic: if `input_type='voice'`, call STT first, then LLM
- [ ] Endpoint `POST /v1/captures/voice` (multipart with audio file)
- [ ] Server-side validation: max 60s, max 5MB, accepted mime types
- [ ] Storage: save audio to local_fs or S3 per env
- [ ] Delete audio after capture reaches terminal state
- [ ] App: `record: ^5.1.2` package
- [ ] App: `CaptureVoicePage` with large mic button, 60s countdown, optional waveform
- [ ] App: client-side 60s limit
- [ ] Pytest with DummySTT

### Definition of Done

- User records 10s of "got Hollow Knight for the Switch", confirms
- Within 30s, review screen appears with a candidate
- Audio is deleted from storage after review
- Attempt to record > 60s is blocked client-side
- Attempt to upload > 60s audio via direct API is rejected with 400

### Technical highlight

> **Why Whisper local instead of API:** zero egress cost, full privacy, no rate limit. Trade-off: needs CPU/GPU for inference. On CPU, `faster-whisper` with the `base` model transcribes 10s of audio in ~3s. For self-hosted deployment this is acceptable. README documents GPU acceleration via the CUDA flag.

---

## Epic 5 — Capture (photo) + LLM Vision (Weekend 6)

**Goal:** photo capture using multimodal LLM directly, no separate OCR pipeline.

### Tasks

- [ ] Worker extends: if `input_type='photo'`, send image + prompt directly to Ollama (smart vision-capable model)
- [ ] Prompt `prompts/capture_parse_vision.j2` for covers vs shelves
- [ ] Support multiple games in one photo (shelf) — limit 12
- [ ] Endpoint `POST /v1/captures/photo`
- [ ] Validation: max 10MB, mime `image/*`
- [ ] App: `CapturePhotoPage` with `image_picker` (camera or gallery)
- [ ] Web: photo upload at `/captures/new`
- [ ] Pytest with DummyLLM returning 1, 3, and 12 games

### Definition of Done

- User photographs a cover, within 60s a candidate appears
- User photographs a shelf of 3 games, within 90s 3 candidates appear
- Capture module coverage ≥ 80%

### Technical highlight

> **Why multimodal LLM instead of OCR + LLM pipeline:** Gemma 3 vision processes the image and extracts game titles in one inference, eliminating OCR error propagation. For environments without GPU, the README documents a fallback to Tesseract + text-only LLM as an alternative path with a separate prompt template.

---

## Epic 6 — Mission lifecycle + Briefing (Weekend 7)

**Goal:** the **anchor feature** of the vitrine. AI briefing with anti-hallucination validation.

### Tasks

- [ ] Schema: `missions` with partial unique index for "one active per user"
- [ ] Endpoints:
  - `POST /v1/missions` (start — validates: has entry? no other active?)
  - `GET /v1/missions/active`
  - `PATCH /v1/missions/{public_id}/debrief` (free text from user)
  - `POST /v1/missions/{public_id}/end` (no debrief, sets `ended_via`)
- [ ] Worker `debrief_processor.py`:
  - Picks missions with `debrief_text` but no `extracted_state`
  - LLM extracts: `{location, next_action, level, current_quest}`
  - Saves `extracted_state`
  - Updates `library_entries.mission_next_action`
- [ ] Worker `mission_auto_clamp.py`:
  - Cron hourly
  - Active mission > 8h → `ended_via='auto_clamp_8h'`, `ended_at=started_at+8h`
- [ ] Endpoint `POST /v1/missions/{public_id}/briefing/regenerate` (optional)
- [ ] Briefing logic:
  - Query: last 3 ended missions of same library_entry with `extracted_state`
  - Prompt `prompts/briefing.j2` receives those debriefs + current `mission_next_action`
  - Call smart LLM
  - **Anti-hallucination validation:** extract proper nouns + numbers from output, check overlap with input. < 70% overlap → log `suspicious_briefing`, add disclaimer
- [ ] App: screens `BriefingPage` (briefing + Start Mission / Skip), `MissionActivePage` (simple timer), `DebriefPage`
- [ ] App: BLoC `MissionBloc` with Active/Idle states
- [ ] Pytest scenarios: first mission (no prior briefing), third mission (3 debriefs in context), anti-hallucination validation

### Definition of Done

- User taps Start on an entry, sees a generated briefing
- After the session, user writes a free-text debrief, app extracts state
- Next time user starts a mission on the same game, briefing reflects the new debrief
- Attempt to start a second active mission returns 409
- Mission abandoned > 8h is closed by the cron
- Mission module coverage ≥ 85% (this is the heart of the app)

### Technical highlight (the most important of the project)

> **Anti-hallucination validation:** LLM output is parsed for proper nouns and numbers, then validated against the input context. If less than 70% of "interesting tokens" in the output appear in the input, the briefing is flagged as `suspicious_briefing` and the user sees a disclaimer. This is a deterministic safeguard layered on top of probabilistic LLM output — no fine-tuning needed.

In interviews this becomes: *"How do you handle LLM hallucinations in production?"* — concrete answer, not philosophical.

---

## Epic 7 — Daily Loadout (Weekend 8)

**Goal:** second AI feature. 3 questions → 1 game + reasoning.

### Tasks

- [ ] Schema: `loadouts` via migration
- [ ] Endpoints:
  - `POST /v1/loadouts` (input: mood, available_minutes, mental_energy)
  - `POST /v1/loadouts/{public_id}/accept` (creates mission)
  - `POST /v1/loadouts/{public_id}/reject`
- [ ] Logic:
  - List eligible library_entries (backlog/playing/paused, no ended mission < 12h ago)
  - Prompt `prompts/loadout.j2` with list + context
  - Smart LLM returns `{library_entry_public_id, reasoning}`
  - **UUID validation:** if returned public_id is not in candidate list → reroll. Second failure → 422
- [ ] Cron: mark loadout `action='ignored'` after 24h without accept/reject
- [ ] App: screens `LoadoutQuestionsPage` (3 sliders/radio groups), `LoadoutResultPage` (big game card + reasoning)
- [ ] Pytest with DummyLLM returning invalid UUID → test the reroll

### Definition of Done

- User answers 3 questions, sees a suggestion with reasoning within 15s
- User accepts → mission starts automatically
- If LLM returns a non-existent UUID, system rerolls and works
- "Empty library" scenario shows a decent message ("Add games first")

### Technical highlight

> **Constraint: LLM must pick from existing library.** The loadout endpoint validates that the returned UUID exists in the user's eligible library entries. If not (the LLM hallucinated a UUID), reroll once, then 422. Same anti-hallucination pattern as briefing, applied to structured output.

---

## Epic 7B — Async Debrief Extraction with Taskiq (Weekend 8.5)

**Goal:** decouple LLM debrief extraction from the mission end flow. User gets an instant response; extraction happens in a background worker with retries.

### Context

When a user submits a debrief, `submit_debrief()` currently calls `extract_debrief_state()` synchronously — blocking the HTTP response while the LLM processes the text. The extracted state (location, next_action, level, current_quest) is only needed later, when generating a briefing for the next mission on that game. There's no reason to make the user wait.

### Strategy

1. **Debrief submission returns immediately.** Save the debrief text, end the mission, respond to the user. No LLM call in the request path.
2. **Async extraction via Taskiq worker.** A background task picks up the debrief and calls `extract_debrief_state()` with automatic retries on failure.
3. **Sync fallback at next briefing.** When starting a new mission, if the previous mission has `debrief_text` but null `extracted_state` (extraction failed or hasn't run yet), do a synchronous extraction at that point with a friendly loading message. This is a rare edge case — the async worker will have succeeded in almost all cases.

### Why Taskiq

- **Asyncio-native** — tasks are plain `async def`, no event loop conflicts with FastAPI
- **Official FastAPI integration** via `taskiq-fastapi` with shared dependency injection
- **Actively maintained** (2026 releases, growing community)
- **Broker-flexible** — Redis now (already in the stack), can swap to RabbitMQ/NATS/Kafka later
- **Built-in retries and middleware** — covers the retry strategy without custom code
- **arq is dead** (maintenance-only, creator moved on) and **Celery lacks async support** (sync workers, event loop conflicts, operational overhead)

### Tasks

- [ ] Add `taskiq`, `taskiq-redis`, and `taskiq-fastapi` to API dependencies
- [ ] Create `infrastructure/tasks/` module with Taskiq broker configuration (Redis)
- [ ] Create task `extract_debrief_state_task` that runs the LLM extraction + DB update
- [ ] Configure retry policy: 3 attempts with exponential backoff
- [ ] Modify `MissionService.submit_debrief()`: save text, end mission, dispatch async task, return immediately
- [ ] Add sync fallback in `MissionService.start_mission()` / briefing generation: if previous mission has `debrief_text` but null `extracted_state`, run extraction synchronously before generating the briefing
- [ ] Frontend: add a brief loading state when the sync fallback triggers ("Loading context from your last session...")
- [ ] Add Taskiq worker to `docker-compose.yml` as a separate service
- [ ] Pytest: test debrief submission returns instantly without LLM call, test extraction task runs correctly, test sync fallback path
- [ ] Update `ARCHITECTURE.md` with the async extraction pattern

### Definition of Done

- Submitting a debrief responds instantly (no LLM latency in the response)
- Extracted state appears on the mission within seconds (background worker)
- If the worker fails all retries, the next briefing still works (sync fallback with friendly loading message)
- Taskiq worker runs as a separate process alongside the API
- Tests cover: happy path (async extraction succeeds), failure path (sync fallback triggers)

### Technical highlight

> **Async-first with sync fallback:** debrief extraction is fire-and-forget with retries. The system optimistically processes in the background, but never loses data — if all retries fail, the extraction runs on-demand when the data is actually needed (next briefing). The user only experiences latency in the rare failure case, and even then gets a clear explanation of what's happening.

---

## Epic 8 — Stats and analytics (Weekend 9)

**Goal:** where the web really shines. Rich dashboard.

### Tasks

- [ ] Endpoints `/v1/stats/*`:
  - `overview` (total games, status counts, missions last 30d, avg mission duration)
  - `play-heatmap?from=&to=` (missions grouped by day)
  - `genres` (estimated time per genre)
  - `platforms` (distribution)
  - `timeline?limit=` (recent missions with debriefs)
- [ ] Web: `/analytics/overview` route with KPI cards (Mantine `<Card>`)
- [ ] Web: `/analytics/heatmap` with GitHub-contributions-style calendar
- [ ] Web: `/analytics/genres` with pie/donut
- [ ] Web: `/analytics/timeline` with chronological mission list
- [ ] Web: period filters (last 7d, 30d, 90d, 1y, custom)
- [ ] Pytest for each stats endpoint

### Definition of Done

- Heatmap shows 30 days with intensity by mission count
- Genre pie shows real data
- Timeline shows last 20 missions with expandable debriefs
- Performance: each endpoint < 500ms with 500 missions

### Technical highlight

> **Stats queries use materialized aggregations.** For users with > 1000 missions, naïve aggregation per request hits Postgres hard. A nightly cron pre-computes `daily_user_stats` materialized view. Hot path reads from the view; cold path falls back to raw query. Same pattern used in production Freeler dashboards.

This is the spot that connects DailyLoadout to Freeler narratively. A recruiter who reads both notices: *"this engineer applies the same performance pattern across different projects — not a one-off."*

---

## Epic 9 — Polish + Documentation + Launch (Weekend 10)

**Goal:** state of "vitrine ready to announce".

### Tasks

- [ ] Final README.md with:
  - Hook: demo GIF (voice capture → review → briefing → loadout)
  - Brief problem/solution
  - Stack badges
  - "Why this exists" (vitrine + personal use)
  - Quickstart "clone + docker compose up + done"
  - Features list with checkboxes
  - Architecture diagram (mermaid)
  - Brief self-hosting guide, link to docs/DEPLOYMENT.md
  - Brief contributing section
  - License
- [ ] ARCHITECTURE.md with documented technical decisions (all the highlights flagged in epics 1–8)
- [ ] docs/PRODUCT.md (product vision, copied and adapted from original spec)
- [ ] docs/DEPLOYMENT.md (Fly.io, Railway, VPS)
- [ ] docs/OLLAMA.md (models, VRAM requirements, CPU-friendly alternatives)
- [ ] docs/API.md (points to FastAPI's `/docs` served by Scalar)
- [ ] GitHub issues open for v1.1 features (multi-device offline sync, push, Live Activities, plugin system) — visible roadmap
- [ ] Demo GIF recorded and committed to `docs/assets/`
- [ ] Empty states polished in app and web
- [ ] Error states polished
- [ ] Loading states with shimmer/skeleton
- [ ] Coverage badges in README
- [ ] LinkedIn announcement post

### Definition of Done

- README is a piece in itself (worth reading without cloning)
- Every important technical decision has a paragraph in ARCHITECTURE.md
- Everything works offline (Ollama local, zero cloud dependency)
- Future roadmap is visible in open issues

---

## Epic 10 — Deep Research Briefing (v1.1+)

**Goal:** augment mission briefings with web-researched, spoiler-free game knowledge using local deep research.

### Context

Epic 6 briefings use only the LLM's parametric knowledge and the user's own debrief data to suggest next steps. This works well for popular titles but produces vague suggestions for niche games or complex quest structures. Deep research bridging the gap between "what the user told us" and "what's actually available in the game world" would make briefings significantly more useful.

### Integration: local-deep-research

[local-deep-research](https://github.com/LearningCircuit/local-deep-research) is a privacy-first, local-first research agent that supports Ollama and SearXNG. It fits DailyLoadout's architecture: no cloud keys required, runs alongside the existing stack.

### Tasks

- [ ] Add SearXNG + local-deep-research to `docker-compose.yml`
- [ ] New infrastructure module `infrastructure/research/` with abstract base + LDR client + dummy for tests
- [ ] "Deep briefing" mode: opt-in per mission start (user chooses quick vs. deep)
- [ ] Research query construction: `"{game_title} walkthrough tips after {location} {current_quest} spoiler-free"`
- [ ] Spoiler filter prompt layer: LLM receives research results but is constrained to suggest **directions and areas**, never reveal boss names, plot twists, story events, or item locations the player hasn't mentioned
- [ ] Latency handling: deep briefing takes 30-60s — show progress indicator, allow cancellation, fall back to quick briefing on timeout
- [ ] Search source config: allow users to choose search engines (Wikipedia, game wikis, etc.) via settings
- [ ] Pytest with DummyResearchClient returning canned results
- [ ] Web: toggle in briefing modal for "Quick briefing" vs. "Deep briefing (slower, web-researched)"

### Definition of Done

- User starts a mission with "deep briefing" selected
- Within 60s, briefing includes web-researched suggestions grounded in the game world
- Suggestions are spoiler-free: "explore the northwest passage" not "defeat the hidden boss there"
- Quick briefing still works in 2-3s (default, no regression)
- Deep briefing falls back gracefully if SearXNG/LDR is unavailable

### Technical highlight

> **Spoiler-free constraint on web-augmented AI:** the research agent fetches walkthrough content that inherently contains spoilers. The briefing prompt is constrained to suggest directions and areas without revealing what the player will find. This is a two-layer filter: the research query targets "next steps" content, and the briefing prompt strips specifics. The anti-hallucination validator from Epic 6 still runs on the output.

### Why this is a separate epic

LDR integration adds Docker services (SearXNG), a new dependency stack (LangGraph/LangChain), and a hard prompt engineering problem (spoiler filtering). Mixing this into Epic 6 would risk the anchor feature's stability. Epic 6 delivers actionable briefings from LLM knowledge; Epic 10 enhances them with web research.

---

## Descope guide if time runs short

If at some point you feel you're pushing, these are the epics to defer to **v1.1** without destroying the vitrine:

1. **Epic 5 (photo capture).** Keeping text + voice is already strong. Photo goes to v1.1.
2. **Epic 7 (loadout).** Briefing alone is already the anchor AI feature. Loadout can wait.
3. **Epic 8 (stats).** Web can ship with just the library data table for v1; stats moves to v1.1.

**Don't skip:** Foundation, Auth, Library, Capture Text (Epic 3), Mission + Briefing (Epic 6), Polish (Epic 9). These are the **core of the vitrine**.

---

## Optional decisions you can still make

1. **Weekly LinkedIn updates?** Could become a "Building DailyLoadout in public" series — visibility for each epic. More work, but valuable if you want growth.

2. **Private beta with friends during Epic 9?** Not required for the vitrine, but generates real feedback and testimonials for the README.

3. **Versioning from Epic 0?** Tags `v0.1.0`, `v0.2.0` per epic make the repo's evolution easy to inspect. Recommended.

---

## Final note

The 10 weekends are not a contract. Life happens, Trezya happens, family happens. If an epic takes two weekends, that's fine — the order is what matters, not the calendar.

What you must defend: **the repo must never be in a broken state on `main`.** Every merge is a stable point in the narrative. If you're not done with an epic, finish what you started before merging, even if smaller. PR your own draft, leave it open, come back.

That discipline is half the vitrine.
