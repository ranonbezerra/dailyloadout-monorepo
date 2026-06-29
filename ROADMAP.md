# Slate — Roadmap

Execution plan organized in weekend-sized epics. Each epic ends in a **demonstrable state** — if the weekend runs out, descope the epic rather than ending in a broken halfway state.

The repository is public from Epic 0 onward. Every commit and PR is part of the narrative.

---

## Calendar overview

| Weekend | Epic | Focus |
| --- | --- | --- |
| 1 | Foundation | Setup, Docker Compose, 3 packages booting |
| 2 | Auth + Users | fastapi-users, JWT rotation, login on app + web |
| 3 | Library | Manual CRUD, schema working end to end |
| 4 | Capture (text) + IGDB | First AI flow, simplest input |
| 5 | Capture (voice) | faster-whisper local |
| 6 | Capture (photo) | Multimodal LLM (vision) |
| 7 | PlaySession + Recap | **Anchor feature** — anti-hallucination |
| 8 | Daily Pick | Second AI feature with UUID validation |
| 8.5 | Async WrapUp (Taskiq) | Decouple LLM extraction from wrap-up flow |
| 9 | Stats + Web analytics | Where the dashboard shines |
| 10 | Polish + Launch | README final, demo GIF, announcement |
| 11 | Deep Research Recap | LangGraph research graph — web-augmented, spoiler-free (v1.1+) |
| 12 | Backlog Concierge | LangGraph tool-using conversational agent (v1.1+) |

Total: **10 weekends ≈ 2.5 months** for v1.0 (assuming 8–12 productive hours per weekend). Epics 11–12 are v1.1+ enhancements and the home for the agentic (LangGraph) work.

---

## Epic 0 — Foundation (Weekend 1)

**Goal:** public repo, empty but professional, with Docker Compose booting "hello world" across all three packages.

### Tasks

- [ ] Create `slate-monorepo` on GitHub, public, MIT license
- [ ] Initial README (work-in-progress version): problem, vision, stack, "WIP" status badge
- [ ] `.gitignore` for Python, Flutter, Node, IDE files
- [ ] `docker-compose.yml` with 4 services: postgres, redis, ollama, api (placeholder returning `{"status": "ok"}` at `/health`)
- [ ] `docker-compose.dev.yml` with hot-reload
- [ ] `.env.example` complete (every env var from ARCHITECTURE.md §7)
- [ ] `packages/api/pyproject.toml` with Poetry, Python 3.14, base deps (FastAPI, Pydantic v2, SQLAlchemy, asyncpg, alembic, arq, structlog, ruff, mypy, pytest, pytest-asyncio)
- [ ] `packages/api/src/slate/main.py` with minimal app factory + `/health`
- [ ] `packages/mobile/` initialized via `flutter create`, configured for iOS/Android. Renders "Slate WIP"
- [ ] `packages/web/` initialized with Vite (Bun), React 19, TypeScript, Mantine v8. Renders empty layout on `localhost:3200`
- [ ] GitHub Actions: three separate workflows (`ci-api.yml`, `ci-app.yml`, `ci-web.yml`) running lint + test on every PR
- [ ] Issue templates (bug, feature, question)
- [ ] PR template
- [ ] README with CI badges

### Definition of Done

- `docker compose up` brings everything online (API responds 200 at `/health`)
- `cd packages/mobile && flutter run -d <device>` opens the app
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
- [ ] Web: stores refresh tokens in httpOnly cookie
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

## Epic 6 — PlaySession lifecycle + Recap (Weekend 7)

**Goal:** the **anchor feature** of the vitrine. AI recap with anti-hallucination validation.

### Tasks

- [ ] Schema: `play sessions` with partial unique index for "one active per user"
- [ ] Endpoints:
  - `POST /v1/play-sessions` (start — validates: has entry? no other active?)
  - `GET /v1/play-sessions/active`
  - `PATCH /v1/play-sessions/{public_id}/wrap-up` (free text from user)
  - `POST /v1/play-sessions/{public_id}/end` (no wrap-up, sets `ended_via`)
- [ ] Worker `wrap_up_processor.py`:
  - Picks play sessions with `wrap_up_text` but no `extracted_state`
  - LLM extracts: `{location, next_action, level, current_quest}`
  - Saves `extracted_state`
  - Updates `library_entries.play_session_next_action`
- [ ] Worker `play_session_auto_clamp.py`:
  - Cron hourly
  - Active play session > 8h → `ended_via='auto_clamp_8h'`, `ended_at=started_at+8h`
- [ ] Endpoint `POST /v1/play-sessions/{public_id}/recap/regenerate` (optional)
- [ ] Recap logic:
  - Query: last 3 ended play sessions of same library_entry with `extracted_state`
  - Prompt `prompts/recap.j2` receives those wrap-ups + current `play_session_next_action`
  - Call smart LLM
  - **Anti-hallucination validation:** extract proper nouns + numbers from output, check overlap with input. < 70% overlap → log `suspicious_recap`, add disclaimer
- [ ] App: screens `RecapPage` (recap + Start PlaySession / Skip), `PlaySessionActivePage` (simple timer), `WrapUpPage`
- [ ] App: BLoC `PlaySessionBloc` with Active/Idle states
- [ ] Pytest scenarios: first play session (no prior recap), third play session (3 wrap-ups in context), anti-hallucination validation

### Definition of Done

- User taps Start on an entry, sees a generated recap
- After the session, user writes a free-text wrap-up, app extracts state
- Next time user starts a play session on the same game, recap reflects the new wrap-up
- Attempt to start a second active play session returns 409
- PlaySession abandoned > 8h is closed by the cron
- PlaySession module coverage ≥ 85% (this is the heart of the app)

### Technical highlight (the most important of the project)

> **Anti-hallucination validation:** LLM output is parsed for proper nouns and numbers, then validated against the input context. If less than 70% of "interesting tokens" in the output appear in the input, the recap is flagged as `suspicious_recap` and the user sees a disclaimer. This is a deterministic safeguard layered on top of probabilistic LLM output — no fine-tuning needed.

In interviews this becomes: *"How do you handle LLM hallucinations in production?"* — concrete answer, not philosophical.

---

## Epic 7 — Daily Pick (Weekend 8)

**Goal:** second AI feature. 3 questions → 1 game + reasoning.

### Tasks

- [ ] Schema: `picks` via migration
- [ ] Endpoints:
  - `POST /v1/picks` (input: mood, available_minutes, mental_energy)
  - `POST /v1/picks/{public_id}/accept` (creates play session)
  - `POST /v1/picks/{public_id}/reject`
- [ ] Logic:
  - List eligible library_entries (backlog/playing/paused, no ended play session < 12h ago)
  - Prompt `prompts/pick_selection.j2` with list + context
  - Smart LLM returns `{library_entry_public_id, reasoning}`
  - **UUID validation:** if returned public_id is not in candidate list → reroll. Second failure → 422
- [ ] Cron: mark pick `action='ignored'` after 24h without accept/reject
- [ ] App: screens `PickQuestionsPage` (3 sliders/radio groups), `PickResultPage` (big game card + reasoning)
- [ ] Pytest with DummyLLM returning invalid UUID → test the reroll

### Definition of Done

- User answers 3 questions, sees a suggestion with reasoning within 15s
- User accepts → play session starts automatically
- If LLM returns a non-existent UUID, system rerolls and works
- "Empty library" scenario shows a decent message ("Add games first")

### Technical highlight

> **Constraint: LLM must pick from existing library.** The pick endpoint validates that the returned UUID exists in the user's eligible library entries. If not (the LLM hallucinated a UUID), reroll once, then 422. Same anti-hallucination pattern as recap, applied to structured output.

---

## Epic 7B — Async WrapUp Extraction with Taskiq (Weekend 8.5)

**Goal:** decouple LLM wrap-up extraction from the play session end flow. User gets an instant response; extraction happens in a background worker with retries.

### Context

When a user submits a wrap-up, `submit_wrap_up()` currently calls `extract_wrap_up_state()` synchronously — blocking the HTTP response while the LLM processes the text. The extracted state (location, next_action, level, current_quest) is only needed later, when generating a recap for the next play session on that game. There's no reason to make the user wait.

### Strategy

1. **WrapUp submission returns immediately.** Save the wrap-up text, end the play session, respond to the user. No LLM call in the request path.
2. **Async extraction via Taskiq worker.** A background task picks up the wrap-up and calls `extract_wrap_up_state()` with automatic retries on failure.
3. **Sync fallback at next recap.** When starting a new play session, if the previous play session has `wrap_up_text` but null `extracted_state` (extraction failed or hasn't run yet), do a synchronous extraction at that point with a friendly loading message. This is a rare edge case — the async worker will have succeeded in almost all cases.

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
- [ ] Create task `extract_wrap_up_state_task` that runs the LLM extraction + DB update
- [ ] Configure retry policy: 3 attempts with exponential backoff
- [ ] Modify `PlaySessionService.submit_wrap_up()`: save text, end play session, dispatch async task, return immediately
- [ ] Add sync fallback in `PlaySessionService.start_play_session()` / recap generation: if previous play session has `wrap_up_text` but null `extracted_state`, run extraction synchronously before generating the recap
- [ ] Frontend: add a short loading state when the sync fallback triggers ("Loading context from your last session...")
- [ ] Add Taskiq worker to `docker-compose.yml` as a separate service
- [ ] Pytest: test wrap-up submission returns instantly without LLM call, test extraction task runs correctly, test sync fallback path
- [ ] Update `ARCHITECTURE.md` with the async extraction pattern

### Definition of Done

- Submitting a wrap-up responds instantly (no LLM latency in the response)
- Extracted state appears on the play session within seconds (background worker)
- If the worker fails all retries, the next recap still works (sync fallback with friendly loading message)
- Taskiq worker runs as a separate process alongside the API
- Tests cover: happy path (async extraction succeeds), failure path (sync fallback triggers)

### Technical highlight

> **Async-first with sync fallback:** wrap-up extraction is fire-and-forget with retries. The system optimistically processes in the background, but never loses data — if all retries fail, the extraction runs on-demand when the data is actually needed (next recap). The user only experiences latency in the rare failure case, and even then gets a clear explanation of what's happening.

---

## Epic 8 — Stats and analytics (Weekend 9)

**Goal:** where the web really shines. Rich dashboard.

### Tasks

- [ ] Endpoints `/v1/stats/*`:
  - `overview` (total games, status counts, play sessions last 30d, avg play session duration)
  - `play-heatmap?from=&to=` (play sessions grouped by day)
  - `genres` (estimated time per genre)
  - `platforms` (distribution)
  - `timeline?limit=` (recent play sessions with wrap-ups)
- [ ] Web: `/analytics/overview` route with KPI cards (Mantine `<Card>`)
- [ ] Web: `/analytics/heatmap` with GitHub-contributions-style calendar
- [ ] Web: `/analytics/genres` with pie/donut
- [ ] Web: `/analytics/timeline` with chronological play session list
- [ ] Web: period filters (last 7d, 30d, 90d, 1y, custom)
- [ ] Pytest for each stats endpoint

### Definition of Done

- Heatmap shows 30 days with intensity by play session count
- Genre pie shows real data
- Timeline shows last 20 play sessions with expandable wrap-ups
- Performance: each endpoint < 500ms with 500 play sessions

### Technical highlight

> **Stats queries use materialized aggregations.** For users with > 1000 play sessions, naïve aggregation per request hits Postgres hard. A nightly cron pre-computes `daily_user_stats` materialized view. Hot path reads from the view; cold path falls back to raw query. Same pattern used in production Freeler dashboards.

This is the spot that connects Slate to Freeler narratively. A recruiter who reads both notices: *"this engineer applies the same performance pattern across different projects — not a one-off."*

---

## Epic 9 — Polish + Documentation + Launch (Weekend 10)

**Goal:** state of "vitrine ready to announce".

### Tasks

- [ ] Final README.md with:
  - Hook: demo GIF (voice capture → review → recap → pick)
  - Short problem/solution
  - Stack badges
  - "Why this exists" (vitrine + personal use)
  - Quickstart "clone + docker compose up + done"
  - Features list with checkboxes
  - Architecture diagram (mermaid)
  - Short self-hosting guide, link to docs/DEPLOYMENT.md
  - Short contributing section
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

## Epic 10 — Deep Research Recap (v1.1+)

**Goal:** augment play session recaps with web-researched, spoiler-free game knowledge using local deep research.

### Context

Epic 6 recaps use only the LLM's parametric knowledge and the user's own wrap-up data to suggest next steps. This works well for popular titles but produces vague suggestions for niche games or complex quest structures. Deep research bridging the gap between "what the user told us" and "what's actually available in the game world" would make recaps significantly more useful.

### Approach: build the research graph in LangGraph (don't just wire LDR)

[local-deep-research](https://github.com/LearningCircuit/local-deep-research) (LDR) is a privacy-first research agent on Ollama + SearXNG and a good reference — but it is itself built on LangGraph. For the showcase we build our **own** small LangGraph research graph instead of importing LDR wholesale. Same skill, but we own the graph and get a concrete "stateful agent in production" story. No cloud keys; runs alongside the existing stack.

The full design (state schema, node signatures, conditional edges, ports, validators-as-nodes, mermaid diagram) lives in [docs/DEEP_RESEARCH_RECAP.md](./docs/DEEP_RESEARCH_RECAP.md). This epic tracks the implementation tasks.

**Why LangGraph here (and not plain code):** the deep recap is genuinely multi-step with a bounded refine loop, a 30–60s long-running budget, cancellation, and a quick-recap fallback. That is exactly LangGraph's territory: durable execution, conditional edges, and (optionally) checkpointed resume. The existing single-shot `generate_recap` stays untouched as the `quick` path and the fallback.

### Module layout (hexagonal — same shape as `llm/`, `stt/`, `storage/`)

```text
infrastructure/
├── research/                # web search port
│   ├── base.py              # AbstractResearchClient.search(query) / fetch(url)
│   ├── searxng.py           # SearXNG client (local)
│   ├── dummy.py             # canned results for tests
│   └── factory.py           # RESEARCH_PROVIDER env
└── agent/                   # the LangGraph recap agent
    ├── base.py              # AbstractRecapAgent.deep_recap(req) -> RecapResult
    ├── langgraph_agent.py   # compiles + invokes the graph
    ├── dummy.py             # DummyRecapAgent for tests
    ├── factory.py           # AGENT_PROVIDER env
    └── graph/
        ├── state.py         # ResearchRecapState (TypedDict)
        ├── nodes.py         # build_query, search, grade, refine, synthesize, spoiler_filter, anti_hallucination, fallback_quick
        └── builder.py       # StateGraph wiring + checkpointer
```

### Tasks

- [x] Add `langgraph` + `langgraph-checkpoint` to API deps (LangChain not required here — nodes reuse the existing `AbstractLLMClient`)
- [x] Add SearXNG service to `docker-compose.yml` (local, no external search keys)
- [x] `infrastructure/research/`: abstract base + `SearxngResearchClient` + `DummyResearchClient` + factory
- [x] `infrastructure/agent/graph/state.py`: `ResearchRecapState` TypedDict (see design doc)
- [x] `infrastructure/agent/graph/nodes.py`: the 8 nodes (see design doc for signatures + model roles)
- [x] `infrastructure/agent/graph/builder.py`: `StateGraph` wiring, conditional router, `MemorySaver` checkpointer (Postgres saver later)
- [x] Expose a generic `complete(prompt, role, json=False)` on the LLM port so agent nodes can render their own Jinja prompts (`prompts/research_grade.j2`, `research_refine.j2`, `recap_research.j2`, `spoiler_filter.j2`)
- [x] Reuse the Epic 6 token-overlap validator as the `anti_hallucination` node (import from `core/play-session`, do not duplicate)
- [x] `AbstractRecapAgent` + `LangGraphRecapAgent` + `DummyRecapAgent` + factory
- [x] Wire `core/play-session/service.py`: when `mode='deep'`, call the agent port wrapped in `asyncio.wait_for(deadline)`; on timeout/empty, fall back to `generate_recap`
- [x] Env: `AGENT_PROVIDER`, `RESEARCH_PROVIDER`, `SEARXNG_BASE_URL`, `DEEP_RECAP_DEADLINE_SECONDS`, `DEEP_RECAP_MAX_REFINES`, `DEEP_RECAP_MAX_RESULTS`
- [x] Pytest: node unit tests (each node in isolation), graph integration test with `DummyResearchClient` + `DummyLLMClient`, fallback-on-timeout test, spoiler-leak regression test
- [x] Web/App: recap modal toggle "Quick" vs "Deep (slower, web-researched)" + progress indicator + cancel button

### Definition of Done

- User starts a play session with "deep recap" selected; within the deadline (60s) the recap includes web-grounded next steps
- Suggestions are spoiler-free: "explore the northwest passage", never "defeat the hidden boss there"
- Quick recap still works in 2–3s (default, no regression) and is the automatic fallback
- Graph falls back gracefully (and visibly) if SearXNG is down or the deadline is hit
- `anti_hallucination` node runs on the deep output exactly as in Epic 6
- Agent + research modules coverage ≥ 85% (dummies for both ports; no real LLM/search in CI)

### Technical highlight

> **Deterministic guards as graph nodes.** The deep recap is a LangGraph state machine where the probabilistic node (synthesize) is bracketed by deterministic ones: a bounded refine loop gated by an LLM `grade` node, a `spoiler_filter` pass, and the Epic 6 token-overlap `anti_hallucination` validator as the terminal gate. If the graph can't ground a spoiler-safe suggestion within the deadline, a conditional edge routes to the plain quick recap. No fine-tuning — orchestration plus guards on top of a local model.

In interviews: *"build a stateful, long-running agent with a refine loop, branching, and a hard correctness constraint, on a local model, with a graceful degradation path"* — concrete, not buzzword.

### Why this is a separate epic

It adds a Docker service (SearXNG), a new dependency (`langgraph`), two new hexagonal ports (`research/`, `agent/`), and a hard prompt-engineering problem (spoiler filtering). Folding it into Epic 6 would risk the anchor feature. Epic 6 ships actionable recaps from LLM knowledge; Epic 10 layers grounded web research on top, reusing Epic 6's validator unchanged.

---

## Epic 11 — Backlog Concierge (v1.1+)

**Goal:** an optional, conversational, tool-using agent — the agentic evolution of Daily Pick. Where the Pick (Epic 7) is a rigid 3-question → 1-pick form, the Concierge is a multi-turn chat: "I've got an hour, I'm tired, what should I play?" → it calls tools over the real library and reasons across turns.

### Product caveat (read before building)

The product thesis is *"you don't choose, the app picks"* — zero friction, indecision killed. A chatty agent **reintroduces** that friction. So the Concierge is **not** a replacement for the one-tap Pick; it is an opt-in "talk to the operator" mode for power users who want to discuss. The default home action stays the single-tap Pick. If this caveat ever feels wrong in practice, cut the epic — the Pick already covers the core need.

### Why LangGraph here

This is the genuinely agentic case: multi-turn, stateful (conversation threads via LangGraph persistence), tool-using (the LLM decides which tool to call), with branching (recommend / refine / compare / explain). The deterministic UUID-existence guard from Epic 7 becomes the terminal validation node.

### Tools (read-only over existing repositories — no new data model)

- `search_library(status, platform, genre)` — over `library_entries`
- `get_play_session_history(library_entry_public_id)` — last wrap-ups / `extracted_state` / `play_session_next_action`
- `get_play_stats(window)` — the Epic 8 stats endpoints
- `estimate_session_fit(library_entry_public_id, minutes)` — heuristic fit score

### Tasks

- [ ] Add `langchain-ollama` (for `ChatOllama` + `bind_tools` ergonomics — tool-calling is the one place LangChain earns its keep)
- [ ] New `OLLAMA_AGENT_MODEL` slot — **default `qwen3:8b`, not `gemma3`**: Gemma is weak at function-calling; Qwen3 is robust at tool-calling and is already a documented alternative in `docs/OLLAMA.md`
- [ ] `infrastructure/agent/concierge/`: tool definitions (thin wrappers over existing repositories/services), graph builder, conversation-thread checkpointer
- [ ] `core/concierge/service.py` + `api/v1/concierge.py`: a streaming chat endpoint (SSE) keyed by a thread id
- [ ] Terminal validation node: any `library_entry_public_id` the agent recommends must exist in the user's library (reuse Epic 7's guard); reroll once, else degrade to a non-committal answer
- [ ] App/Web: a simple chat UI gated behind a settings flag (off by default)
- [ ] Pytest: tool unit tests, a graph test with a scripted tool-calling DummyLLM, the UUID-existence guard test

### Definition of Done

- Power-user can chat multi-turn and get a grounded recommendation that exists in their library
- One-tap Pick remains the default and is untouched
- Tool calls only read existing data; no new tables
- Agent never recommends a non-existent entry (guard enforced)

### Technical highlight

> **Tool-calling agent on a local model, with the product's guard rails intact.** The Concierge uses `ChatOllama.bind_tools` over read-only library tools, but the recommendation is still validated against the real library before it reaches the user (same UUID-existence guard as Epic 7). The harder decision is restraint: keeping it an opt-in mode so it complements, rather than fights, the zero-friction Pick.

---

## Epic 12 — Unified PlaySession Pipeline (v1.1+)

**Goal:** make **PlaySession the single spine** of the play loop and turn "deciding what to play" and "getting a recap" into independent, **skippable** stages that all converge on one `start_play_session` orchestrator. Today the same end state — an active play session — is reachable through three divergent, inconsistent code paths; this epic consolidates them and reframes Pick and Concierge as *entrances* to the play session flow rather than separate destinations.

### The problem (what the code shows today)

A play session gets created three different ways, and they disagree:

| Path | Game chosen by | Recap |
| --- | --- | --- |
| `PickService.accept_pick` (`/v1/picks/{id}/accept`) | AI (3-question form) | **none** — creates an *empty* play session |
| `PlaySessionService.start_play_session` (`POST /v1/play-sessions`) | user (already knows) | optional `quick` / `deep` / skip |
| `submit_retroactive_wrap_up` (`/v1/play-sessions/retroactive-wrap-up`) | user | n/a (pre-ended "I played offline") |

Accepting a Pick yields a recap-less play session; starting one directly yields a recap — same outcome, two behaviours, duplicated active-play session guards. And the **Concierge dead-ends**: it recommends a game but cannot start it, recap it, or log a session, so it only *overlaps* Pick without doing any real work.

### The model

Every existing and desired flow is one point in a small cube:

```text
START A PLAY_SESSION = DECIDE (self | AI one-tap pick | conversational concierge)
                × RECAP  (none | quick | deep)
                × MODE   (live | retroactive)
```

`PlaySession` is the aggregate root. `Pick` stays a **decision record** (keep its accept-rate history + 24h auto-ignore), but its acceptance routes through the same orchestrator. The Concierge becomes the **conversational operator** of the whole pipeline, not a second recommender.

### Tasks

- [x] Extract a single `start_play_session` orchestrator (`core/play-session/start.py::create_play_session_for_entry`, free function over repos, mirroring `recap.py`'s pattern); it owns the one-active-play session guard (409 backstop) and `last_played_at` update.
- [x] Refactor `PlaySessionService.start_play_session` to delegate to it (no behaviour change — existing tests stay green).
- [x] Refactor `PickService.accept_pick` to delegate to it, gaining an **optional recap stage** (`recap_text` on `PickAcceptRequest`; backward-compatible default).
- [x] Add a "let the AI pick" path (`PickService.create_and_start` → `POST /v1/picks/start`): AI-pick a game and start a play session in one step, so DECIDE=AI and RECAP are independent.
- [x] Give the Concierge **write tools** — `start_play_session`, `generate_recap`, `submit_retroactive_wrap_up`, `set_status` (`infrastructure/agent/concierge/tools_write.py`); gated by `concierge_write_tools_enabled`. Each is UUID-validated and respects the one-active-play session guard.
- [x] Client nav restructure: collapsed Pick + Concierge into one **Play** hub (active play session front-and-centre; three doors: "What's the move?" one-tap, "I'll choose", "Ask") on both the web sidebar (`pages/PlayPage.tsx`, `App.tsx`) and Flutter shell (`features/play/view/play_page.dart`, `shell_page.dart`, `routes.dart`). Nav is **Play / Library / History / Stats** — the play session log is its own **History** tab (`/history`); start doors disable while a play session is active; the pick flow offers an optional recap before starting. Old paths redirect to `/play/*` / `/history`.
- [x] Tests: orchestrator unit tests (`test_play_session_start.py`); pick-accept-with-recap and `/start` (`test_pick.py`); concierge write-tool guards (`test_concierge_tools_write.py`).

### Definition of Done

- One `start_play_session` orchestrator; `accept_pick`, direct start, and the Concierge all funnel through it.
- Recap is a genuinely optional stage regardless of how the game was chosen.
- The Concierge can start/recap/log a session, not just recommend.
- Nav presents ~3 areas (Play / Library / Stats) instead of 5–6 tabs.
- **The zero-friction default is preserved:** "What's the move?" is still one tap → AI picks → quick recap → playing. Stages are skippable with smart defaults, never a forced wizard.

### Why this is a separate epic

It's a cross-cutting refactor (service consolidation + new write surface + nav on both clients) touching api, web, and app. Sequenced in phases — **(1) API orchestrator consolidation, (2) Concierge write tools, (3) client nav** — so each phase ships independently without breaking the others. The guard rails (one active play session per user; UUID-existence on every pick) and the product thesis ("you don't choose, the app picks") are invariants, not things this epic relaxes.

### Risks

- **Wizardisation.** Turning a one-tap action into a multi-step flow would betray the core promise. Mitigation: defaults collapse the common path to one action; steps are opt-in.
- **Losing Pick's analytics/auto-ignore.** Keep the `Pick` row as a decision record; only its *acceptance path* changes.

---

## Epic 13 — Firecrawl research provider (evaluate, v1.1+)

**Goal:** evaluate [Firecrawl](https://www.firecrawl.dev/) as a research source for the Deep Research Recap (Epic 10) — as a reliability fallback for SearXNG, a page-scrape enrichment step, or the **primary** search/scrape in the hosted build — without disturbing the self-host default.

**Status:** not committed. This is a *spike-then-decide* epic — build a small adapter behind the existing port, A/B the recap quality, then keep or drop it. Its ranking depends on the deployment target (see Epic 13).

### Context

Epic 10's research layer is a hexagonal port (`infrastructure/research/`, `AbstractResearchClient.search()`), with SearXNG as the local, zero-key default and `dummy` for tests. The graph currently grounds `synthesize` on SearXNG **snippets** only — it never fetches page bodies. Firecrawl's real value-add is **scraping** (URL → clean LLM-ready markdown), not search (its `/search` is just an upstream wrapper). Two distinct uses, evaluated separately.

### The dual-distribution model (decides Firecrawl's ranking)

Because LLM and research both live behind ports (Epic 13), one codebase ships two configurations selected by env. Firecrawl's role flips depending on which build you're optimizing:

| Build | LLM | Research | Firecrawl's role |
| --- | --- | --- | --- |
| **Self-host / OSS** | Ollama (local) | SearXNG (local) | optional fallback only; SearXNG stays default |
| **Hosted / production** | Bedrock / Vertex (Epic 13) | **Firecrawl** | sensible **primary** — once you're paying for cloud inference, SearXNG's "free + local" edge is gone and its ops cost (rate-limits, captchas, IP reputation) becomes a liability |

So the local-first objection that keeps Firecrawl optional only holds for the self-host build. In the hosted build, Firecrawl-as-primary (with SearXNG as fallback) is the natural choice. SearXNG **remains the default** for the OSS distribution; Firecrawl is opt-in via `RESEARCH_PROVIDER`/a flag either way.

### Option A — reliability fallback

A composite `FallbackResearchClient` wrapping primary (SearXNG) + secondary (Firecrawl) behind the same port — no graph changes. Decide the trigger policy: fall back on hard failure (HTTP error/timeout) **and/or empty results**, immediately or after N retries-with-backoff (the "after K attempts" knob). Note this sits *above* the existing degrade-to-quick fallback: it keeps the **deep** path alive when SearXNG flakes instead of dropping to the quick recap.

### Option B — scrape enrichment (higher value)

SearXNG finds URLs → Firecrawl `/scrape` turns the top 1–2 into markdown → richer `synthesize` grounding. This is where recap quality actually jumps (snippets are thin). **Risk to measure:** scraping full walkthrough pages increases spoiler surface (boss names, plot beats) — exactly what `spoiler_filter` + the overlap guard must catch. Gate behind a flag and add a spoiler-leak regression test before adopting.

### Tasks (spike)

- [ ] Add `firecrawl-py` as an **optional** dependency; env: `RESEARCH_PROVIDER=firecrawl` (or `FALLBACK_RESEARCH_PROVIDER`), `FIRECRAWL_API_KEY`, `FIRECRAWL_BASE_URL` (for self-hosted)
- [ ] `FirecrawlResearchClient(AbstractResearchClient)` + `DummyFirecrawlResearchClient`; wire into the research factory
- [ ] (Option A) `FallbackResearchClient` composite with a configurable trigger policy (failure and/or empty; immediate vs N-retries)
- [ ] (Option B) optional `scrape()` step in the `search`/`synthesize` path, flag-gated, with a **spoiler-leak regression test** on scraped content
- [ ] A/B: compare deep-recap quality (snippets-only vs scrape-enriched) on a handful of real games; record the verdict in this epic
- [ ] Decide: adopt as opt-in provider, adopt scrape step, or drop — keep SearXNG the default either way

### Definition of Done

- A working `RESEARCH_PROVIDER=firecrawl` (and/or fallback) behind the port, defaults unchanged (SearXNG/dummy)
- Documented verdict: measured quality delta, spoiler-safety result, and a keep/drop recommendation
- If kept: tests at parity with the SearXNG provider; if scrape is enabled, the spoiler-leak regression passes
- No regression to the local-first, zero-key default path

### Technical highlight

> **A provider you can adopt without a rewrite — or walk away from.** Because web search and scraping live behind one port with a dummy default, evaluating a cloud/self-hosted scraper is a contained spike: add an adapter, A/B the recap quality, keep or delete. The interesting tension is product, not plumbing — richer scraped content improves grounding but enlarges the spoiler surface the deterministic guards have to defend.

---

## Epic 14 — Cloud LLM adapters: Bedrock / Vertex (evaluate, v1.1+)

**Goal:** add cloud LLM providers behind the existing `AbstractLLMClient` port so the project can ship a **hosted** distribution (cloud inference) alongside the **self-host** one (local Ollama), choosing per deployment via `LLM_PROVIDER`. Keep Ollama the default for the OSS build; `dummy` stays the test default.

**Status:** not committed. Spike-then-decide — the README already lists "cloud provider adapters belong behind the existing LLM port" as planned. The actual provider choice (Bedrock-with-Claude vs an open-source/self-hosted model) is now **decided: AWS Bedrock** for the hosted distribution (see the Decision below). This epic is the prerequisite that makes Firecrawl-as-primary (Epic 12) sensible.

### Decision (2026-06): AWS Bedrock + in-house cost governance

**Provider — AWS Bedrock.** Ship the hosted distribution on **Bedrock** (Ollama stays the local-dev / OSS default; `dummy` the test default). Bedrock is chosen over a self-hosted OSS model or a managed gateway primarily for **portfolio value** — AWS is the broadest-demand cloud skill, and this repo is a portfolio piece — and the cost is trivial at portfolio scale anyway (a cheap tier ≈ a few $/month, bounded by the caps below). The open-serverless price advantage only matters at real multi-tenant scale, which a portfolio won't hit.

**Build vs. buy — call Bedrock directly, build the cost layer ourselves.** We deliberately do **not** route through an LLM gateway (LiteLLM proxy/SDK). Two reasons: (1) we already own the `AbstractLLMClient` port, so a gateway is a redundant second abstraction; (2) the cost-governance layer is the *differentiated, interview-worthy* part — offloading it to a tool would hide exactly the engineering worth showing.

- **Buy (don't build):** the Bedrock call itself → boto3 / Anthropic `AnthropicBedrock` SDK (commodity plumbing; also the "AWS / Bedrock" résumé keyword).
- **Build (the showcase):** a cost-governance layer on top — per-call cost from token usage (token→$), a per-user **monthly budget** and a **global spend kill-switch** with graceful degradation, backed by Redis counters, plus **AWS Budgets** as the provider-side outer alarm.

**Defense-in-depth — three independent tiers so Redis is not a single point of failure.** The in-house cost guard (PR #35) counts spend in Redis and **fails closed** (a Redis outage 503s every cost-bearing route), which makes Redis critical infra for anything that costs money. To remove that single point of failure we layer the controls so no one component being down can either run up cost *or* take the LLM features offline:

1. **Redis counters (primary, fast):** the existing global/per-user fixed-window kill-switch — the precise, low-latency tier.
2. **In-process degraded fallback:** when Redis is unreachable the guard drops to a conservative per-worker in-memory counter (global cap ÷ worker count) instead of hard-503-ing, so a Redis blip *degrades* the feature (tighter, less precise cap) rather than taking it down. Imprecise across workers by design — its job is to *bound* spend, not to be exact. **(Shipped ahead of this epic — see PR for the cost-guard fallback.)**
3. **AWS Budgets (provider-side backstop, independent):** a hard monthly budget on the AWS account with a **budget action that disables Bedrock access** (or revokes the inference role) on breach. Fully independent of the app — if every in-app guard fails (Redis *and* the fallback *and* a bug), the provider itself stops the spend. Coarse and billing-delayed, but the absolute last line. **Must be configured at deploy, before any public launch.**

The principle: the goal is not "remove Redis" but "never depend on a single component being up for the money to stay safe." Tier 3 alone removes the worst case (runaway bill); tier 2 removes the "LLM dies with Redis" case; together they cost little and cover the essentials.

This mirrors the rate-limiting call in PR #34: keep the solved commodity (`pyrate_limiter`), build the bespoke differentiated piece. The per-minute per-user limits already shipped (#34) bound bursts; this epic adds the **monthly + global $ caps** that bound *sustained* cost — a hard prerequisite before opening the app to the public (without them a scripted account can run up cost via the per-minute ceiling).

**Cheap-tier-first:** default the `fast`/`smart` roles to cheap models (Claude Haiku / Amazon Nova), escalate only where output quality is user-visible; prompt-cache the repeated deep-recap context. **Document the build-vs-buy reasoning in an ADR** — the decision itself is a portfolio signal.

### Context

Everything LLM-shaped already goes through `infrastructure/llm/` (`AbstractLLMClient`, `OllamaClient`, `DummyLLMClient`, factory by `LLM_PROVIDER`), including the `complete(prompt, *, role, json)` method the deep-research agent (Epic 10) relies on. Cloud providers are new implementations of that port — product code, the graph, and the guards don't change. This is the designed evolution path, not a pivot.

### The fast/smart split becomes a tuning lever

Our two model roles map cleanly onto cloud tiers — a cheap tier for the frequent calls, a premium tier only where output quality is user-visible. On **Claude via Bedrock** (model IDs carry an `anthropic.` prefix):

| Role | Used by | Bedrock-Claude model |
| --- | --- | --- |
| `fast` | `grade`, `refine`, wrap-up extraction, captures | `anthropic.claude-haiku-4-5` |
| `smart` | `synthesize`, `spoiler_filter`, quick recap, pick selection | `anthropic.claude-sonnet-4-6` |
| (optional max-quality `smart`) | recaps only, if quality demands | `anthropic.claude-opus-4-8` |

Vertex/Gemini has an equivalent Flash (cheap) / Pro (premium) split.

### Hosted vs. self-host — the actual decision

A deep recap fires up to ~4 LLM calls (`grade` → `refine`×0–2 → `synthesize` → `spoiler_filter`); a quick recap is one `smart` call. The build decision turns on volume and operational appetite, not on any single number:

- **At personal / low volume:** a cloud provider is pay-per-use with **zero infra/ops/GPU burden** — typically the lower total cost. A self-hosted open-source model only comes out ahead once a dedicated GPU's fixed running cost is justified by sustained volume.
- **At scale / multi-tenant:** a self-hosted OSS model on owned/rented GPU can win on marginal cost and keeps data local — at the cost of ops, capacity planning, and quality tuning.
- So: **cloud for launch and low volume; revisit OSS-local only if volume (or data-locality requirements) justify the fixed cost.** The ports make this an env flag, not a rewrite — you can start cloud and migrate later. Run the numbers privately before committing.

### API-shape work for the adapter (not just a URL swap)

- Use the Anthropic SDK's `AnthropicBedrock` / `AnthropicVertex` clients (Python `anthropic[bedrock]` / `[vertex]`); Gemini-on-Vertex would be its own client.
- **No `temperature`/`top_p`/`top_k`** on current Claude (Opus 4.7/4.8, Fable) — adaptive thinking only. Don't port Ollama's sampling knobs.
- **JSON mode differs:** Ollama uses `format: "json"`; Claude uses `output_config.format` (json_schema) or a `strict` tool. Our `complete(json=True)` abstraction holds — the adapter implements JSON-mode its own way.
- Bedrock-Claude lacks server-side tools, Managed Agents, and the Files API — **irrelevant here**, since our LangGraph agent only uses plain `messages`.
- **Prompt caching** to amortize the repeated system/context across the ~4 calls per deep recap — a real cost lever on cloud.

### Tasks (spike)

- [ ] Add `anthropic[bedrock]` (and/or `[vertex]` / a Gemini client) as **optional** deps
- [ ] `BedrockLLMClient(AbstractLLMClient)` (and/or `VertexLLMClient`) implementing all methods incl. `complete(prompt, role, json)`; map `role`→tier; JSON via `output_config.format`/strict tools; adaptive thinking
- [ ] Extend the LLM factory: `LLM_PROVIDER=bedrock|vertex|ollama|dummy`; env for creds (AWS region/IAM or GCP project/location/service account), per-tier model IDs
- [ ] Cost governance (built in-house, **no gateway**): token→$ metering from usage; per-user **monthly** budget + **global spend kill-switch** with graceful degradation (Redis counters); structured usage logging; prompt caching on the deep-research context. Prerequisite before any public launch.
- [x] **Tier 2 — degraded fallback:** cost guard drops to a conservative in-process counter when Redis is unreachable (no longer hard-503s every cost route on a Redis blip). *Shipped ahead of the epic.*
- [ ] **Tier 3 — AWS Budgets backstop (deploy-time):** monthly budget on the AWS account with a budget action that disables Bedrock / revokes the inference role on breach — provider-side, app-independent. Document the setup in `docs/DEPLOYMENT.md`. **Prerequisite before any public launch.**
- [ ] Tests with a mocked cloud client (no real cloud calls in CI; `dummy` stays the CI default)
- [ ] ADR: the build-vs-buy write-up (Bedrock-direct + in-house cost governance vs. an LLM gateway like LiteLLM; why we own the cost layer given the existing port) + measured per-recap cost on cheap-tier Bedrock

### Definition of Done

- `LLM_PROVIDER=bedrock` (or `vertex`) works end-to-end for captures, recaps (quick + deep), pick, and wrap-up extraction; Ollama remains the OSS default; `dummy` still used in tests
- All `AbstractLLMClient` methods implemented on the new provider, including `complete()` with JSON mode and adaptive thinking
- A documented cost comparison and a provider recommendation tied to expected volume
- No regression to the local-first default path; test coverage at parity with the Ollama client

### Technical highlight

> **Inference is an env flag, not a rewrite — and the model tier is a cost dial.** Because every LLM call goes through one port with `fast`/`smart` roles, swapping Ollama for Bedrock/Vertex is a new adapter plus config, and the role split doubles as a cost lever: cheap tier (Haiku/Flash) for the frequent `grade`/`refine`/extraction calls, premium tier (Sonnet/Opus/Pro) only where output quality is user-visible. The same codebase ships self-hosted (zero keys) and hosted (cloud inference) from one set of ports.

---

## Epic 15 — Frictionless Library Import: platform screenshot ingestion (v1.1+)

**Goal:** make bulk onboarding nearly frictionless — a user populates 50–100 games in one shot by photographing (or screenshotting) their existing library from the major platforms, with the per-import cost driven toward ~zero. Extends Epic 5 (photo capture) from "a shelf of a few games" into "my whole Steam/PSN/Xbox/Switch/GOG/Epic library at once."

**Status:** not committed. Spike-then-decide, like Epics 12–13. The platform-aware parsing and the local-first OCR path are each independently shippable; descope to "Steam list-view only" if the weekend runs short.

### Context

The single biggest onboarding cliff is the empty library. Epic 5 added multimodal photo capture (covers + shelves, limit 12), but bulk import has a different shape: dozens of titles in one frame, and the **expensive, one-time** moment in a user's lifecycle. Library *additions* are free and unlimited across all tiers (only `deep recap` is gated to Pro, and free tier is one recap + one pick/day), so the import path is pure CAC, not COGS — but only if it stays cheap. The cost spike here is OCR/vision, **not Whisper**: nobody dictates 100 games by voice, so STT (Epic 4) never enters this path. The thing that quietly turns cents into dollars is **retry from low accuracy** — bad extraction → user re-shoots and re-runs → multiplies both cost and friction. So accuracy is simultaneously the cost control and the friction control; they are the same problem.

### The decisive insight: text source beats image recognition

Most platform libraries *default* to a **cover-art grid**, and cover art is stylized logo, not clean text — exactly what OCR and vision models fumble (and hallucinate) on, especially for niche titles. Every major platform also exposes a **clean text representation** of the same list. Steering the user to that view before they capture turns a hard image-recognition problem into a trivial text-reading one — the single largest lever on accuracy, cost, and friction at once. This is UX, not ML.

For some platforms the cleanest text source is the **web account / purchase-history page**, not a console or launcher screenshot — worth guiding per platform:

| Platform | Best clean-text source | Notes |
| --- | --- | --- |
| Steam | Library → **list view** (left rail, vertical titles) | gold standard; near-perfect text extraction |
| Xbox | My games & apps / Full library → **list/details view** | titles render as text rows |
| GOG | GOG Galaxy **list view**, or web library list | clean text either way |
| PSN / PS5 | Game Library grid (title under tile), or **PS App** list | console grid is OK; web/app account list is cleaner |
| Epic | Launcher library is grid-only; **Account → Transactions** (web) is text | guide to the web purchase history for clean text |
| Nintendo Switch / Switch 2 | console is icon-grid (worst case); **Nintendo Account → Purchase history** (web) is text | strongly prefer the web purchase-history page over a console capture |

**Onboarding takeaway:** ship a per-platform capture hint (a small annotated screenshot per platform) that says "switch to list view" or "open your purchase history" *before* the camera/upload step. One instruction collapses the hardest cases.

### Pipeline (local-first, cloud only as low-confidence fallback)

```text
platform hint → user captures list-view / purchase-history screenshot(s)
   → local OCR (Tesseract + preprocessing)         [free, on the VPS]
   → confidence check ──low──► cloud vision model    [cents, capped]
   → fuzzy-match each line against canonical catalog  [no LLM, ~free]
   → checkbox confirmation list (user unticks the 3–4 wrong ones)
   → bulk-create library_entries
```

- **Local OCR first.** Tesseract with image preprocessing (grayscale, threshold, deskew, upscale) handles clean list-view text well at zero API cost — it just costs VPS CPU, run through the Taskiq worker so it never blocks a request (same discipline as Whisper in Epic 4).
- **Cloud vision only as fallback.** When local OCR confidence is low (grid art, glare, handwriting-grade noise), fall back to a cheap vision model for that image only, behind a per-day cap. Abuse (someone using us as a free OCR service or burning the vision budget with mass uploads) then costs CPU, not an open API tab.
- **Catalog fuzzy-match, not LLM.** Extracted lines are dirty (`Sid Meier's Civ VI`, OCR swaps `l`/`I`). Normalize and error-correct by fuzzy-matching against a canonical games catalog (reuse the **Epic 3 IGDB** client; RAWG or a local snapshot as alternates) — string distance / trigram / embeddings, no model call. This is where most "wrong title" errors die for free.
- **Confirmation over perfection.** Don't chase 100% extraction. Present a checkbox list of what was parsed; the user unticks the few wrong rows and taps confirm. Confirmation costs zero tokens and makes 95%-accurate extraction feel reliable.

### Does this violate the no-API-integration principle? No

The product rule is **no account sync** with Steam/PSN/Nintendo (no playtime, achievements, or library-sync via official APIs) — a deliberate independence choice. A **canonical games-metadata catalog** (IGDB/RAWG) is a reference database, not an account link: different category entirely. We read a *screenshot the user took*, then clean the strings against a metadata dictionary. No platform account is ever connected. Worth a sentence in `PRODUCT.md` so the distinction is explicit.

### Module layout (hexagonal — same shape as `llm/`, `stt/`, `research/`)

```text
infrastructure/
├── ocr/                     # new port: image → text lines
│   ├── base.py              # AbstractOCRClient.extract_lines(image) -> list[OcrLine] (text, confidence, bbox)
│   ├── tesseract.py         # local Tesseract + preprocessing (default)
│   ├── vision.py            # cloud vision fallback (reuses the Epic 13 LLM port where applicable)
│   ├── dummy.py             # canned lines for tests
│   └── factory.py           # OCR_PROVIDER env
└── catalog/                 # title normalization (reuses IGDB client from Epic 3)
    ├── matcher.py           # fuzzy match line -> canonical game (trigram/embedding), confidence score
    └── dummy.py
```

### Tasks (spike)

- [x] `infrastructure/ocr/`: `AbstractOCRClient.extract_lines()` + `TesseractOCRClient` (preprocessing) + `VisionOCRClient` fallback + `DummyOCRClient` + factory by `OCR_PROVIDER`/`OCR_FALLBACK_PROVIDER`
- [x] Image preprocessing (grayscale, autocontrast, upscale, binarize) with a tunable `ocr_confidence_threshold` that decides the Tesseract→vision fallback
- [x] `infrastructure/catalog/matcher.py`: fuzzy-match (rapidfuzz) OCR lines → canonical titles via the Epic 3 IGDB client, returning match confidence; no LLM call. Dummy matcher for CI.
- [x] New `workers/library_import_processor.py` `input_type='library_import'` path — OCR → confidence gate → catalog match → batch `capture_candidates` (cap lifted to `library_import_max_candidates`)
- [x] Endpoint `POST /v1/captures/library-import` (multipart, multiple images) → capture with a batch of candidates
- [x] Bulk confirm endpoint `POST /v1/captures/{public_id}/candidates/bulk-confirm` (confirm a list, reject the rest) — commits 50–100 entries in one call
- [x] **Per-day import cap** (images/day) → 429, plus a capped+logged vision-fallback, via a reusable `usage_counters` table
- [x] Per-platform capture hints + a platform picker (Steam/Xbox/GOG/PlayStation/Epic/Switch) that sets the right "switch to list view / open purchase history" hint and a default platform on both clients
- [x] App: `LibraryImportPage` (`features/library_import/`) — platform picker → hint → multi-image picker (`pickMultiImage`) → **checkbox confirmation list** (all checked) → bulk confirm; route `/library/import`, entry-point FAB on the library list
- [x] Web: `/library/import` 3-step flow (`pages/LibraryImportPage.tsx`) — picker → hint → multi-file input → checkbox confirmation list → bulk confirm; entry point in the QuickAdd menu
- [x] Pytest: `DummyOCRClient` 1/40/100 lines; low-confidence triggers the vision fallback (+ cap); catalog matcher corrects a dirty title; bulk-confirm commits N + rejects the rest; per-day cap returns 429
- [x] `PRODUCT.md`: paragraph clarifying "metadata catalog ≠ account integration"

### Definition of Done

- User picks "Steam", follows the list-view hint, uploads 2–3 screenshots, and within the import budget sees a checkbox list of ~50–100 parsed titles
- Unticking a few wrong rows and confirming bulk-creates the rest as `library_entries` in one action
- Clean list-view captures resolve entirely on **local OCR** (no cloud call); only noisy/grid captures hit the capped vision fallback
- Catalog fuzzy-match corrects common OCR errors without an LLM call
- Free-tier import cap enforced; vision-fallback usage logged and capped
- No official platform account is ever linked (principle intact); OCR + catalog modules coverage ≥ 85% (dummies for both ports; no real OCR/vision/IGDB in CI)

### Technical highlight

> **Local-first ingestion with a cloud fallback you rarely pay for.** Bulk library import routes clean list-view text through local Tesseract (CPU, zero API cost) and only escalates noisy images to a capped cloud vision model. Dirty titles are repaired by deterministic fuzzy-matching against a canonical catalog — no LLM in the loop — and the user confirms a checkbox list rather than trusting perfect extraction. The hardest part is product, not ML: a per-platform "switch to list view / open purchase history" nudge converts an image-recognition problem into a text-reading one, which is what actually drives cost and friction to near zero.

In interviews: *"minimize a one-time high-cost operation by pushing work to a free local path, escalating to paid compute only on a measured confidence signal, with deterministic post-correction and a human-in-the-loop confirm"* — concrete cost-engineering, not a model pick.

### Why this is a separate epic

It adds a new hexagonal port (`ocr/`), a catalog-matching layer, a batch capture/confirm flow, and a per-platform UX surface — none of which belong inside Epic 5's single-photo path. It also carries the product-principle nuance (metadata catalog vs account integration) and the abuse/cost guards, which deserve their own scrutiny rather than being smuggled into capture.

---

## Epic 16 — Live token-streaming Concierge (v1.1+)

**Goal:** upgrade the Backlog Concierge (Epic 11) from "buffer → validate → stream the guarded answer in chunks" to **true token-level streaming** — the chat types out live as the model generates — while keeping the Epic 7 UUID-existence guard intact.

> Builds on the **operator Concierge from Epic 12**: once the Concierge can start/recap/log play sessions (not just recommend), live streaming also means surfacing those write actions as they happen ("▶ starting your play session…"), not just text and read-only tool calls.

### Context

Epic 11 ships a deliberately simple streaming model: the agent runs its tool loop to completion, the service validates any recommended `library_entry_public_id` (reroll once, else degrade), and only the **guarded** final answer is streamed over SSE in chunks. That preserves the guarantee ("never surface a game that isn't in the library") but adds a pause before output begins and isn't real token streaming. This epic closes that gap.

### The hard part: streaming and the guard fight each other

To validate (and possibly reroll) a recommendation you need the **whole** answer; to stream live you emit tokens **before** the answer exists. Options to resolve, in order of preference:

- **Stream prose live, gate only the recommendation.** Stream every token as it arrives, but hold back the machine-readable `RECOMMEND: <id>` tail until the id is validated; if invalid, emit a corrected/degraded ending instead. The user sees the reasoning type out live; only the final pick is gated.
- **Speculative stream + correction event.** Stream everything, and if the post-hoc validation fails, emit an SSE `correction` event the client renders (strike-through + replacement). Simpler server-side, more client work.
- **Tool-aware event stream.** Use LangGraph's `astream_events` to surface `tool_call` / `tool_result` / `token` events so the UI can show "🔎 searching your library…" affordances mid-turn, not just text.

### Tasks

- [ ] Switch the LangGraph concierge agent to `astream` / `astream_events`; surface token, tool-call, and tool-result events
- [ ] SSE endpoint emits typed events (`token`, `tool`, `recommendation`, `correction`, `done`) instead of buffered chunks
- [ ] Re-implement the UUID guard as a streaming gate (hold the recommendation tail until validated; reroll-once or degrade in-stream)
- [ ] Durable threads: swap the in-memory `MemorySaver` for `AsyncPostgresSaver` against the existing PostgreSQL so conversations survive restarts and are resumable
- [ ] Cancellation: client can abort a turn mid-stream (drop the SSE connection → cancel the graph run)
- [ ] App/Web: token-by-token rendering + tool affordances + cancel button in the chat UI
- [ ] Pytest: streaming-gate test (valid recommendation streams through; invalid one is held and corrected), scripted-event dummy, resume-after-restart test with the Postgres saver

### Definition of Done

- Chat types out live, token by token, with visible tool affordances
- The UUID guard still holds: an invalid recommendation never reaches the user as a valid pick (held/corrected in-stream, not after the fact)
- Conversations are durable and resumable across restarts (Postgres checkpointer)
- A turn can be cancelled mid-stream

### Why this is a separate epic

Epic 11 is already useful with buffered streaming; the live path adds real complexity — event-typed SSE, an in-stream guard, a Postgres checkpointer, and cancellation — plus client work to render tokens and tool events. Folding it into Epic 11 would risk the guard guarantee for a UX nicety. Ship the guarded buffered version first; layer live streaming on top once it's proven.

---

## Epic 17 — IGDB hardening: caching + attribution (v1.1+)

**Goal:** make the optional IGDB integration *compliant* and *cheap*. The client itself is correct (verified against the v4 docs: Twitch OAuth `client_credentials`, `Client-ID` + `Authorization: Bearer` headers, `POST /v4/games` with an Apicalypse body, parsing `name`/`cover.image_id`/`summary`/`genres.name`/`first_release_date`), but two promised pieces were skipped: the **Redis cache** (ARCHITECTURE §2 "Redis 7 for IGDB cache"; Epic 3 "token cached in Redis") and **user-facing attribution**.

**Status:** attribution done; caching pending.

### Context

IGDB is opt-in via `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` — graceful `IGDBNotConfigured` when absent. The catalog matcher (Epic 15) and capture enrichment (Epic 3) both call `search_games`. Two gaps surfaced once Epic 15 started hammering IGDB on bulk import (up to ~N searches per import at 4 req/s):

- **No caching.** The OAuth token is cached **in-memory**, and the client is **instantiated per request** (`deps/capture.get_igdb_client_dep`), so every IGDB-using request re-authenticates with Twitch. No search-result cache, so popular titles are re-fetched on every import, for every user.
- **No attribution.** IGDB asks for visible, static, user-facing credit to IGDB.com wherever its data is shown.

### Tasks

- [x] **Attribution** — visible static "Game data from IGDB.com" credit (web sidebar, linked) + "Game data provided by IGDB.com" (Flutter library footer); README acknowledgement corrected. (Storing/caching IGDB fields is explicitly allowed/encouraged by IGDB; non-commercial use is free.)
- [x] **Dev smoke-test** — `scripts/check_igdb.py` + `make igdb-check q="…"` to verify live credentials without booting the app.
- [x] **Process-singleton client** (`deps.get_igdb_client_dep` memoised) so the Twitch token is reused across requests instead of re-authenticating per request.
- [x] **Redis result cache** for `search_games` via a new cache port (`infrastructure/cache/`: `AbstractCache` + `NullCache` + `RedisCache`, factory by `app_env`/`cache_enabled`) and a `CachedIGDBClient` decorator (`IGDBSearchClient` protocol), keyed by normalized query+limit, TTL `igdb_cache_ttl_seconds` (7d). Best-effort: cache miss/outage falls through to live. Verified live: 1479ms → 1ms on a repeat lookup. Dummy/no-IGDB paths unaffected; `RedisCache` omitted from coverage like other adapters.
- [ ] Optional: handle `429 Too Many Requests` with a short backoff (the 4 req/s limiter already avoids it under normal single-import load). *Folded into Epic 18.*
- [ ] Optional: share the Twitch token cross-process via Redis (the singleton already covers the single-process inline path; the worker doesn't currently call IGDB). *Folded into Epic 18.*

### Definition of Done

- IGDB-sourced data shows a visible IGDB.com credit on both clients.
- The Twitch token is fetched once and reused across requests (not per request).
- Repeat `search_games` for the same title is served from Redis; a cold import of popular titles is materially faster and makes far fewer IGDB calls.
- No regression to the optional/`dummy`/no-IGDB paths; coverage parity for the cache layer.

---

## Epic 18 — Application caching layer & strategy (v1.1+)

**Goal:** promote the throwaway cache primitive introduced in Epic 17 into a **first-class, app-wide caching strategy** that materially cuts latency and LLM/API cost across every expensive path — not just IGDB. The hard parts are *correctness* (what is safe to cache, and how it's invalidated) and *coherence* (one consistent mechanism, keyed, observable, degradable), not the Redis calls themselves.

**Status:** not started. Epic 17 shipped the seed: an `AbstractCache` port (`NullCache`/`RedisCache`) and one consumer (IGDB). This epic generalises that seed into a deliberate layer with an invalidation model, stampede protection, tiering, and observability.

### Why this deserves its own epic

The app has several genuinely expensive, repeat-heavy operations — a **deep research recap** fires ~4 LLM calls plus web research; **stats** aggregate every play session on each dashboard load; **IGDB/SearXNG** are rate-limited network hops. Today each is recomputed from scratch every time. Caching these is the single biggest lever on both **perceived latency** and **inference/API cost** (the same cost thesis behind Epics 13–15). But naive caching is dangerous here: recaps depend on *mutable* session state, and stats are *per-user* — cache the wrong key or skip an invalidation and you serve stale or, worse, another user's data. So the value is high and the failure modes are real: it warrants a designed layer, not ad-hoc `redis.get` calls sprinkled per feature.

### Scope — what to cache (highest value first)

| Target | Key | TTL / invalidation | Why |
|---|---|---|---|
| **Deep research recap** (Epic 10) | `(game_id, normalized session-state hash, mode)` | TTL (days) + **bust on new wrap-up** for that entry | The most expensive op (multi-LLM + web). Biggest single win. |
| **LLM completions** (capture parse, pick selection) | content-addressed `(model, prompt hash, json-mode)` | short TTL | De-dupes identical prompts; cheap correctness (idempotent inputs). |
| **Web research / SearXNG** (Epic 10) | `normalized query` | TTL (hours) | Network hop; queries repeat across recaps. |
| **Stats / analytics** (Epic 9) | `(user_id, window)` per overview/genre/platform | short TTL + **bust on play session start/end + wrap-up** | Recomputed on every dashboard load; per-user. |
| **IGDB search** (Epic 17) | done | — | Already shipped as the seed. |
| **Twitch/IGDB token** | `igdb:token` in Redis | `expires_in` | Cross-process sharing beyond the per-process singleton. |
| **Reference data** (platforms, genres) | static keys | long TTL + in-process LRU | Tiny, hot, read on most pages. |

### Cross-cutting mechanics

- [ ] **Key + namespace convention** — a typed key-builder and per-namespace prefixes (`igdb:`, `recap:`, `llm:`, `stats:<user_id>:`); **never** mix users into a shared key.
- [ ] **Invalidation model** — a documented map from domain events → busted keys (new wrap-up ⇒ that game's recap + that user's stats; play session start/end ⇒ stats). Event hooks live at the service layer, not scattered.
- [ ] **Single-flight / stampede protection** — a per-key in-flight guard so N concurrent identical requests (e.g. two tabs opening the same deep recap) trigger **one** computation and the rest await it. Critical for the LLM/recap paths.
- [ ] **Tiered cache** — optional in-process LRU in front of Redis for small, hot, shared data (platforms/genres) to skip a network round-trip; Redis for everything user- or size-significant.
- [ ] **Observability** — per-namespace hit/miss counters (structured logs + optional metrics) so TTLs can be tuned against real hit rates, plus a `make cache-stats`-style readout.
- [ ] **Safety & degradation** — every cache read is best-effort (outage ⇒ live); a global `cache_enabled` kill-switch; explicit opt-out per call where freshness must be guaranteed.
- [ ] **Ops** — per-namespace TTL config; document a Redis `maxmemory-policy` (e.g. `allkeys-lru`) and memory budget; optional warm-up of popular IGDB titles.
- [ ] **Tests** — invalidation correctness (event busts the right keys, never a cross-user key), single-flight (one compute under concurrency), tiered read-through, and graceful degradation when the cache is down. `RedisCache` stays integration-tested; the strategy/logic is unit-tested with a fake cache.

### Definition of Done

- Deep recaps, stats, LLM completions, and web research are cached through **one** mechanism with explicit, tested invalidation — no stale-data or cross-user leaks.
- A concurrent burst of identical expensive requests computes once (single-flight), not N times.
- Cache hit/miss is observable per namespace; TTLs are config-driven.
- Everything degrades to live on a cache outage; a single flag disables all caching; `dummy`/test paths are unaffected.

### Why this is a separate epic (not folded into Epic 17)

Epic 17 is a tactical fix for one adapter. This is a **cross-cutting architectural concern** touching the recap graph, the LLM port, stats, and research — with a real correctness surface (invalidation, per-user isolation, stampede control) that deserves its own design and review rather than being smuggled in feature-by-feature.

---

## Epic 19 — Social login / OAuth: Google, Apple, Twitch (v1.1+)

**Goal:** let users register & sign in via **Google, Apple, and Twitch** (Authorization Code + PKCE), in addition to email/password — behind the existing auth layer, issuing the same access/refresh tokens so the rest of the app is unchanged.

**Status:** in progress. Planned feature. Pairs naturally with the anti-abuse work — a verified social identity is a much stronger anti-abuse signal than an unverified email, and **Apple/Google logins arrive pre-verified**, sidestepping the email-verification + CAPTCHA cost for those users.

**Scope (this epic): Google + Twitch, on API + Web.** Both are standard Authorization Code + PKCE with no paid developer account. **Apple Sign In and the native Flutter app surface are split into [Epic 20](#epic-20--apple-sign-in--native-app-oauth-v11)** — Apple needs a paid Apple Developer account and an ES256-signed JWT client-secret, and the native mobile flow (Sign in with Apple/Google) needs iOS/Android platform config, so it is a deliberate follow-up rather than a blocker for the web rollout.

### Context

- There's already an `oauth_identities` table/provider scaffold and `GOOGLE_OAUTH_CLIENT_ID/SECRET` slots in settings — extend that, don't rebuild auth. The OAuth callback resolves/creates a `User` (linking by verified email when safe) and then issues our own JWT access + refresh tokens (cookie-mode for web, body-mode for app), so play sessions/library/concierge are untouched.
- **Twitch is a strategic fit** — it's the gaming identity, and the app already uses Twitch OAuth for IGDB (client-credentials), so the integration/ops surface is familiar (different grant: user Authorization Code vs the existing app-token).

### Tasks

- [ ] `oauth_identities` (provider, provider_uid, user_id, email) — confirm/extend the model; unique (provider, provider_uid) *(scaffold already exists)*
- [ ] Provider configs (**Google, Twitch**): client id/secret, redirect URIs, scopes
- [ ] `GET /v1/auth/oauth/{provider}/start` (PKCE + state) and `/callback` → resolve/link/create user → issue our tokens (reuse the cookie/body dual-mode)
- [ ] Account linking + collision policy: link to an existing account **only** on a provider-verified email match; otherwise create new — and **reject** (ask to log in + link) when an unverified provider email collides with an existing account (never silently merge / never enable takeover)
- [ ] Mark socially-authenticated users `email_verified = true` when the provider asserts a verified email (skips our email-verify gate)
- [ ] Web: provider buttons on login/register
- [ ] Tests: start/callback, state/PKCE validation, linking, collision, token issuance; mocked provider (no real OAuth in CI)

### Definition of Done

- A user can sign up / log in with **Google or Twitch** on the web and land authenticated with our tokens; email/password still works; linking is safe (no account takeover via unverified email); provider-verified users skip the email-verification gate. Coverage at parity with the password flow. *(Apple + native app: [Epic 20](#epic-20--apple-sign-in--native-app-oauth-v11).)*

### Technical highlight

> **One auth core, many front doors.** Social login resolves to the *same* `User` + JWT the rest of the app already speaks, so adding Google/Apple/Twitch is new adapters + a callback, not an auth rewrite — and it doubles as anti-abuse hardening (a verified Google/Apple/Twitch identity is far costlier to mass-create than throwaway emails).

---

## Epic 20 — Apple Sign In + native app OAuth (v1.1+)

**Goal:** add **Apple Sign In** to the OAuth core built in [Epic 19](#epic-19--social-login--oauth-google-apple-twitch-v11), and bring **all three providers (Google, Apple, Twitch) to the Flutter app** with the native mobile flows — reusing the same callback → our-JWT machinery, so it stays "new front doors, one auth core".

**Status:** not started. Split out of Epic 19 because both pieces carry external/platform dependencies that shouldn't block the web rollout:

- **Apple is materially more complex than Google/Twitch.** The "client secret" is not a static string — it's an **ES256-signed JWT** built from a private key (`.p8`), a Key ID, and the Team ID, re-minted before expiry (max 6 months). Apple also returns the user's name/email **only on first authorization** (must be captured then), supports a private-relay email, and requires the Sign in with Apple capability on a **paid Apple Developer account ($99/yr)**.
- **Native mobile is not just Dart.** `Sign in with Apple` (iOS) and native Google Sign-In require **iOS/Android platform configuration** (capabilities, URL schemes, OAuth client per platform, redirect/deep-link handling) on top of the Flutter code.

### Tasks

- [ ] Apple provider config: Team ID, Key ID, `.p8` private key; ES256 client-secret JWT minting (with safe re-mint/caching before the ≤6-month expiry)
- [ ] Apple specifics: capture name/email on first auth only; handle private-relay addresses; map Apple's `email_verified` semantics into our linking/collision policy
- [ ] `apple` provider behind the existing `OAuthProvider` abstraction + `/oauth/apple/start|callback`; web buttons
- [ ] App (Flutter): native **Sign in with Apple** + **Google Sign-In**; **Twitch** via the web Authorization Code flow in a web view / external browser with a deep-link return; exchange the provider result for our access/refresh tokens (body-mode)
- [ ] iOS/Android platform config: Sign in with Apple capability, Google OAuth clients per platform, custom URL scheme / deep-link callback handling
- [ ] Tests: Apple JWT secret minting + flow; app-side bloc/flow tests with a mocked provider/token exchange

### Definition of Done

- A user can sign up / log in with **Apple** on the web, and with **Google, Apple, and Twitch** in the Flutter app, landing authenticated with our tokens. Account linking/collision safety matches Epic 19. Apple's client-secret JWT is minted and refreshed correctly. Coverage at parity with the password + web-OAuth flows.

### Technical highlight

> **The hard provider, isolated.** By shipping Google/Twitch-on-web first (Epic 19) and quarantining Apple's JWT-secret ceremony + the native-mobile platform config here, the auth core proves itself before taking on the provider with a paid account and a signed-secret refresh loop — and Apple still lands as just one more adapter behind the same port.

---

## Epic 21 — Backoffice (admin panel) + dynamic operational config (v1.1+)

**Goal:** an internal **admin panel** to manage users, the game catalogue, and the data, plus a **dynamic operational config** layer so a curated set of operational knobs (kill-switches, abuse caps, feature flags) can be changed **at runtime without a redeploy** — backed by Postgres, surfaced as one screen of the backoffice.

**Status:** not started. Planned. The anti-abuse work (Epics 11–19) shipped incident-response *primitives* — ban (`scripts/ban_user.py`), catalogue demote (`scripts/demote_game.py`), token kill-switch, cost-guard caps — but they live in CLIs/env. This epic gives them a UI and makes the tunable ones live-editable, so reacting to abuse is a panel action, not an SSH + redeploy.

### Decision (2026-06): config split — env baseline + Postgres-backed dynamic overrides

Two kinds of config, two mechanisms (do **not** put everything in one place):

- **Secrets / infra** (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, OAuth secrets, SMTP, provider toggles, DB pool) → stay in **env / secret manager**. They change rarely and changing them *is* a deploy concern. (You also can't store `DATABASE_URL` in the DB you reach via `DATABASE_URL`.)
- **Operational knobs / flags** (a CURATED subset) → a **Postgres `app_config` table** the backoffice edits, with an optional short read-cache. Precedence: **runtime override (Postgres) > env var > code default**. `config.py` stays the baseline; the overlay only overrides the curated keys.

**Why Postgres, not Redis, as the source of truth:** with a backoffice that already CRUDs Postgres, config is just another table — **durable** (survives a Redis flush/restart) and **auditable** (who changed what, when), which a control panel needs. Redis stays a *cache* at most (read the Postgres value, cache it ~15–30s in-process, invalidate on write); it is never the source of truth for config. This also keeps Redis lean — its job stays rate-limit/cost counters + cache, not durable settings. A `maxmemory` + `allkeys-lru` policy on the VPS Redis bounds its RAM regardless (operational note, not part of this epic).

**Curated dynamic set (~10–12, not all ~120 settings):** kill-switches (`rate_limit_enabled`, `cost_guard_enabled`, `concierge_write_tools_enabled`), incident-tunable caps (`cost_user_per_day`, `cost_global_per_day`, `rate_limit_register_per_minute`, `igdb_user_budget_per_day`), product rules (`catalog_share_threshold`, `block_disposable_emails`), and future feature flags. Everything else stays env-only.

### Tasks (delivered in phases)

**API foundation (done):**

- [x] **Phase 1 — Admin authz** (#44): admin grant in a separate `admin_users` table (never on the user row, never a JWT claim), `require_admin` boundary, `/internal/v1` non-advertising prefix, `grant_admin.py` bootstrap.
- [x] **Phase 2 — Users + audit** (#45): `/internal/v1/users` list/search/detail + ban/unban/verify (reuses the session kill-switch; refuses to ban an admin), and the append-only `admin_audit_log` written on every mutation + `/internal/v1/audit`.
- [x] **Phase 3 — Dynamic operational config** (#46): `app_config` Postgres overlay (`override > env > default`) with a typed curated registry, short in-process cache + write-through invalidation; `/internal/v1/config` (list/set/clear, validated + audited); all 9 curated knobs wired live through the overlay; seed migration for the standard values.

**Backoffice web UI + domain expansion (in progress):**

- [x] **Phase 4 — Backoffice web foundation + ready domains** (#47): a distinct admin shell (separate `/backoffice` area reusing the existing auth/session, visually marked as a backoffice) + admin guard; **Dashboard** (`GET /internal/v1/dashboard` aggregate endpoint: user/ban/verify/admin counts, active play sessions, catalogue size, config overrides, recent admin actions); **Users**, **Config**, and **Audit** management screens over the existing APIs.
- [x] **Phase 5 — Games / catalogue admin** (this PR): `/internal/v1/games` (list/search with owner counts + provenance filters, detail, demote/promote — surfacing `demote_game.py` as a panel action — and metadata edit, all audited) + a **Catalogue** screen in the backoffice (table, source filters, demote/promote/edit, catalogue tallies). Catalogue *merge* (library-entry reassignment) deferred to a follow-up.
- [ ] **Phase 6 — Other domains (moderation & data browse)**: play sessions (browse/force-clamp), captures (browse/reprocess/purge), picks, and basic read-only data browse across domains — each behind the same audited admin boundary.

### Definition of Done

- An admin can manage users (ban/verify/sessions), curate the catalogue (demote/promote/edit), and flip the curated operational knobs **live without a redeploy**, with every change audited. Non-admins cannot reach any of it. Secrets/infra remain env-only. Coverage at parity with the rest of the API.

### Technical highlight

> **Incident response becomes a panel action, not a redeploy.** The kill-switches and caps already exist as code/CLIs; this epic gives them a durable, audited, runtime-editable home (Postgres overlay over the env baseline) and a UI — so tightening a rate limit or flipping the cost kill-switch mid-incident is a click, while secrets stay safely deploy-time.

---

## Epic 22 — Native iOS + Android apps with on-device LLM (v1.1+)

**Goal:** rebuild the mobile client as **two native apps** — **SwiftUI (iOS)** and **Kotlin / Jetpack Compose (Android)** — so each can run a **local, on-device LLM** for the fast, private, free inference path, falling back to the existing backend LLM (Ollama self-host / Bedrock hosted, [Epic 14](#epic-14--cloud-llm-adapters-bedrock--vertex-evaluate-v11)) for the heavy, multi-step work. This is the mobile counterpart to the server-side `fast`/`smart` split: **on-device = fast**, **backend = smart**.

**Status:** not started. The largest client undertaking in the roadmap — phased, and only sensible once the v1.0 feature set is stable. The native apps must reach **parity** with today's Flutter app before it is retired.

### Why native (the forcing function)

Today `packages/mobile` is a single Flutter codebase — efficient for shipping one app to both stores. But the on-device LLM frameworks that make free/private/offline inference possible are **platform-native and not reachable from Flutter**:

- **iOS — Apple Foundation Models** (the on-device ~3B model behind Apple Intelligence, iOS 26+) is a **Swift-only framework** (`import FoundationModels`) with guided generation (`@Generable`) and tool-calling. There is no first-party Flutter binding; a plugin would be a brittle method-channel wrapper around a fast-moving API.
- **Android — Gemini Nano / on-device GenAI** via **ML Kit GenAI APIs** + AICore (device-gated: Pixel 8+/Galaxy S24+…), plus the more portable **MediaPipe LLM Inference API** (bring-your-own small model, e.g. Gemma 3 1B) — both native Kotlin paths.

A thin Flutter wrapper *could* be built, but the platform AI surfaces are exactly where native pays off (model lifecycle, streaming, guided generation, tool-calling, on-device privacy guarantees). So the decision is to **go native** and treat each platform's on-device model as a first-class capability. This is the [ReadUp](https://apps.apple.com/br/app/readup-track-your-reading/id6753879837) insight ("Apple Foundation Models on-device, Llama backend fallback") applied to a gaming companion — and it reinforces the brand's **local-first / privacy** stance.

### The hybrid model — on-device first, backend fallback

Mirror the server `fast`/`smart` roles on the client. A small **on-device** model handles the high-frequency, low-context, latency- and privacy-sensitive tasks; the **backend** keeps the multi-step, large-context, tool-using work it already owns.

| Task | On-device (fast / private / free) | Backend (Ollama / Bedrock) |
| --- | --- | --- |
| Capture text → game candidates | ✅ primary | fallback when device unsupported |
| Wrap-up state extraction | ✅ primary | fallback |
| Quick pick reasoning (already-shortlisted) | ✅ where supported | fallback |
| Deep research recap ([Epic 10](#epic-10--deep-research-recap-v11), web + ~4 calls) | ❌ | ✅ stays backend |
| Concierge tool-calling agent ([Epic 11](#epic-11--backlog-concierge-v11)/[16](#epic-16--live-token-streaming-concierge-v11), LangGraph) | ❌ (Nano/MediaPipe tool-calling too weak) | ✅ stays backend |
| Vision capture (photo → titles) | △ where on-device vision exists | ✅ backend default |

The **UUID-existence guard** and the token-overlap anti-hallucination check stay authoritative on the **backend** for anything that commits data — the on-device model *proposes*, the server still *validates*. Graceful degradation is mandatory: devices without Apple Intelligence / Gemini Nano fall back to the backend path transparently, so no user is blocked.

### Monorepo shape

```text
packages/
├── ios/         # SwiftUI app — @Observable, async/await, Keychain, FoundationModels
├── android/     # Kotlin + Jetpack Compose — ML Kit GenAI / MediaPipe LLM
└── mobile/      # Flutter (retired once parity is reached; kept shipping until then)
```

Both native apps speak the **same API contract** (the FastAPI `/v1/*` surface) — no backend changes required for the apps themselves. A small **client-side LLM abstraction per app** (`OnDeviceLLM` protocol/interface with a `BackendLLM` fallback impl) mirrors the server's `AbstractLLMClient` philosophy, so the on-device/fallback choice is one switch, not scattered conditionals.

### Tasks (phased — parity before retirement)

**Phase 1 — iOS native MVP**

- [ ] Scaffold `packages/ios` (SwiftUI, `@Observable`, async/await, Keychain for the refresh token, the existing dual-mode JWT exchange)
- [ ] Port core flows to parity: auth, library, capture, play session + recap, Play hub (Pick/Concierge), history, stats
- [ ] `OnDeviceLLM` Swift protocol + `FoundationModelsLLM` impl (guided generation for capture-parse + wrap-up extraction) with a `BackendLLM` fallback; a capability check (Apple Intelligence available?) routes per task
- [ ] Native **Sign in with Apple** (synergy with [Epic 20](#epic-20--apple-sign-in--native-app-oauth-v11))

**Phase 2 — Android native MVP**

- [ ] Scaffold `packages/android` (Kotlin, Jetpack Compose, DataStore/Keystore for tokens)
- [ ] Same parity port of core flows
- [ ] `OnDeviceLLM` Kotlin interface + impls: ML Kit GenAI / Gemini Nano where available, **MediaPipe LLM Inference** (bundled Gemma 3 1B) as the portable fallback, `BackendLLM` below that
- [ ] Native Google Sign-In ([Epic 20](#epic-20--apple-sign-in--native-app-oauth-v11))

**Phase 3 — On-device polish & rollout**

- [ ] Token-level streaming of on-device generation in the UI where the framework supports it
- [ ] Telemetry (opt-in, privacy-safe): on-device vs backend hit rate per task, latency, fallback reasons
- [ ] Store submissions; deprecate `packages/mobile` only once both native apps reach parity and pass store review
- [ ] `docs/ONDEVICE_LLM.md`: device-support matrix, model choices, fallback policy

### Definition of Done

- Native iOS and Android apps reach **feature parity** with today's Flutter app and are accepted on their stores.
- On a supported device, capture-parse and wrap-up extraction run **fully on-device** (no network LLM call, works offline); on an unsupported device the same flows fall back to the backend transparently.
- Deep recap and the Concierge agent continue to run on the backend (unchanged), still gated by the UUID-existence guard.
- `packages/mobile` is retired only after parity is verified; until then `main` always has a working mobile client.

### Technical highlight

> **Same fast/smart split, now spanning device and cloud.** The server already routes cheap, frequent calls to a `fast` model and reserves `smart` for quality-critical work; this epic extends that dial onto the client — an on-device model (Apple Foundation Models / Gemini Nano / MediaPipe) handles capture-parse and wrap-up extraction with near-zero latency, zero cost, and full privacy, while the backend keeps the multi-step agentic work. The product's guard rails don't move: the device proposes, the server's UUID-existence and anti-hallucination checks still decide.

In interviews: *"run an on-device LLM for the hot path with a graceful cloud fallback, keep the correctness guards server-authoritative, and ship two native apps because the platform AI frameworks aren't reachable from a cross-platform toolkit"* — a concrete architecture trade-off, not a framework preference.

### Why this is a separate epic

It's the biggest client investment in the roadmap: two new native codebases, a per-platform on-device-LLM integration, a capability/fallback policy, and the careful retirement of the Flutter app — none of which can be smuggled into a feature epic. It depends on the OAuth core ([Epics 19](#epic-19--social-login--oauth-google-apple-twitch-v11)–[20](#epic-20--apple-sign-in--native-app-oauth-v11)) and pairs with the hosted-LLM work ([Epic 14](#epic-14--cloud-llm-adapters-bedrock--vertex-evaluate-v11)) as the backend fallback.

### Risks

- **2× client maintenance.** Trading one Flutter codebase for two native apps multiplies ongoing work; justified by the on-device-LLM payoff, at the cost of slower cross-platform feature velocity. Mitigation: keep business logic thin and server-driven; consider Kotlin Multiplatform / shared client generation later if duplication hurts.
- **Device fragmentation.** Apple Foundation Models need Apple-Intelligence-capable devices (iOS 26+); Gemini Nano is gated to a handful of Androids. The backend fallback is **not optional** — it's the path for most devices on day one.
- **Parity regression.** Retiring Flutter before the native apps truly match would break the "never broken on `main`" rule. Mitigation: keep `packages/mobile` shipping until both native apps pass parity + store review.
- **On-device tool-calling is weak.** Don't push the Concierge agent on-device — Nano/MediaPipe function-calling isn't reliable; it stays a backend LangGraph capability.

---

## Descope guide if time runs short

If at some point you feel you're pushing, these are the epics to defer to **v1.1** without destroying the vitrine:

1. **Epic 5 (photo capture).** Keeping text + voice is already strong. Photo goes to v1.1.
2. **Epic 7 (pick).** Recap alone is already the anchor AI feature. Pick can wait.
3. **Epic 8 (stats).** Web can ship with just the library data table for v1; stats moves to v1.1.

**Don't skip:** Foundation, Auth, Library, Capture Text (Epic 3), PlaySession + Recap (Epic 6), Polish (Epic 9). These are the **core of the vitrine**.

---

## Optional decisions you can still make

1. **Weekly LinkedIn updates?** Could become a "Building Slate in public" series — visibility for each epic. More work, but valuable if you want growth.

2. **Private beta with friends during Epic 9?** Not required for the vitrine, but generates real feedback and testimonials for the README.

3. **Versioning from Epic 0?** Tags `v0.1.0`, `v0.2.0` per epic make the repo's evolution easy to inspect. Recommended.

---

## Final note

The 10 weekends are not a contract. Life happens, Trezya happens, family happens. If an epic takes two weekends, that's fine — the order is what matters, not the calendar.

What you must defend: **the repo must never be in a broken state on `main`.** Every merge is a stable point in the narrative. If you're not done with an epic, finish what you started before merging, even if smaller. PR your own draft, leave it open, come back.

That discipline is half the vitrine.
