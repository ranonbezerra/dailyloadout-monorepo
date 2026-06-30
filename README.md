# Slate

![Slate](./docs/brand/readme-hero.png)

> *Less deciding. More playing.* A self-hosted gaming companion and production-AI systems showcase. Voice/photo/text capture, structured play session state, "previously on..." recaps before each session, and a 3-question daily Pick that selects one game for you.

[![CI – API](https://img.shields.io/badge/CI-API-blue)](https://github.com/ranonbezerra/slate-monorepo/actions/workflows/ci-api.yml)
[![CI – Mobile](https://img.shields.io/badge/CI-Mobile-blue)](https://github.com/ranonbezerra/slate-monorepo/actions/workflows/ci-mobile.yml)
[![CI – Web](https://img.shields.io/badge/CI-Web-blue)](https://github.com/ranonbezerra/slate-monorepo/actions/workflows/ci-web-app.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

---

## What problem this solves

You own 60 games. You play 2. Every time you sit down, half the session is spent deciding what to play — and when you come back to a game after 3 weeks, you've forgotten where you stopped.

Slate treats the backlog as a **decision problem**, not a cataloging problem. Three ideas:

1. **Frictionless capture.** Speak "got Hollow Knight on Switch" and the app fills the metadata. No forms.
2. **PlaySession recaps.** Before each session, the app generates a "previously on..." paragraph from your past wrap-ups — like a TV show recap.
3. **Daily Pick.** Three quick questions (mood, time, mental energy) → one suggested game with reasoning. You don't choose; the app does.

No streaks. No "X days without playing" guilt. Dropping a game is a legitimate decision, not a failure.

---

## Why This Repo Exists

Slate is a production-style AI application wrapped in a real product I use: a full-stack, self-hosted system for turning messy player input into structured state, recommendations, and play session recaps. It runs entirely on your own hardware and uses **local LLMs via Ollama** instead of requiring cloud APIs.

This is not a prompt demo. The interesting parts are the reliability boundaries around probabilistic systems:

- **Local-first AI with provider boundaries.** The API talks to an `AbstractLLMClient`; Ollama is the real local backend and `DummyLLMClient` keeps tests deterministic. Faster-Whisper handles speech-to-text locally.
- **Structured outputs with deterministic guards.** Capture parsing, wrap-up extraction, and Pick selections are treated as untrusted model output. The app validates JSON shape, candidate IDs, user ownership, and context overlap before persisting or showing results.
- **Anti-hallucination as a product feature.** Recaps are checked against the user's actual play session context. Suspicious output is flagged instead of silently trusted. Pick suggestions must reference an existing library entry; invalid UUIDs trigger a reroll path.
- **State machines for AI workflows.** Captures cross three systems (LLM, optional IGDB, user review). They're modeled as an explicit state machine (`queued → processing → review → committed/partially_committed/failed/cancelled`), making retries and partial commits safe.
- **Failure handling over happy paths.** Background wrap-up extraction has retry/backoff behavior and synchronous fallback before recap generation. Capture processing degrades to review/failed states instead of corrupting the library.

The repo also includes versioned AI-engineering workflow files (`CLAUDE.md`, `.claude/`, `.mcp.json`) that document how agents, project conventions, review flows, and MCP tools are expected to work against this codebase.

### Agentic AI — shipped, and what's next

The LangGraph **Deep Research Recap** (a local SearXNG + Ollama graph that searches, grades, refines, synthesizes, spoiler-filters, and then reuses the anti-hallucination validator) and the tool-using **Backlog Concierge** (now an operator of the play-session pipeline, not just a recommender) are **shipped**. The single-shot recap remains the fast path and fallback. Those designs live in [docs/DEEP_RESEARCH_RECAP.md](./docs/DEEP_RESEARCH_RECAP.md) and [ROADMAP.md](./ROADMAP.md).

The current track is **LLM Platform Hardening** ([ROADMAP.md](./ROADMAP.md), Epics 23–28) — the engineering *around* the models rather than more features:

- **Evaluation harness + observability/tracing (Epic 23)** — a golden-dataset eval with deterministic checks plus a **model-agnostic, kappa-calibrated** LLM-as-judge, gating prompt/model changes via `make quality` (`--real --gate` against a committed baseline), with per-call and per-graph-node spans (tokens / latency / cost / cache-hit) and redacted prompt/completion capture. Answers *"how do you know a prompt change didn't regress quality?"* with a number. **(shipped)**
- **RAG over PlaySession history** — embed the player's own wrap-ups (Ollama + pgvector) and retrieve semantically to ground recaps, instead of the last 3 by SQL.
- **Reranking** in the deep-research pipeline; **prompt-injection guardrails** on the agent's untrusted surfaces (chat + capture, with a tool-arg allowlist); a **semantic completion cache**; and **resumable batch re-inference** for embedding/prompt changes.

---

## Quickstart

```bash
# Clone
git clone https://github.com/ranonbezerra/slate-monorepo.git
cd slate-monorepo

# Configure
cp .env.example .env
# (edit .env — defaults are sane for local dev)

# Start infrastructure
make up
```

That starts:

- **PostgreSQL 18** on `:5433`
- **Redis 7** on `:6380`
- **Ollama** on `:11434`

Then run the services on the host:

```bash
make api          # FastAPI on :8100
make web          # React on :3200
make app          # Flutter (macOS by default)
```

Open `http://localhost:3200` for the web dashboard, `http://localhost:8100/docs` for the API reference.

Run `make help` to see all available commands.

---

## Stack at a glance

| Package | Stack |
| --- | --- |
| `packages/api/` | Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2 async · PostgreSQL 18 · Redis · Taskiq · Poetry |
| `packages/mobile/` | Flutter 3.27+ · BLoC · go_router · dio · faster-whisper (server-side) |
| `packages/web/` | Bun · Vite · React 19 · TypeScript · Mantine v8 · TanStack Query |
| AI | `AbstractLLMClient` port · **Ollama** backend · deterministic dummy backend for tests · **faster-whisper** local |
| Infra | Docker Compose · GitHub Actions · AGPL-3.0 |

Detailed architecture in [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Features

### v1.0 (current)

- [x] Email + password auth with JWT rotation
- [x] Manual game entry (no API dependency)
- [x] Library with status workflow (backlog · playing · paused · completed · dropped)
- [x] **Capture by text** — type freely, LLM extracts game candidates
- [x] **Capture by voice** — record up to 60s, transcribed locally with faster-whisper
- [x] **Capture by photo** — single cover or shelf, processed by multimodal LLM
- [x] **IGDB enrichment** (optional) — cover art, genres, release dates
- [x] **PlaySession lifecycle** — start a session, write a wrap-up at the end
- [x] **Recap generation** — LLM-generated "previously on..." with anti-hallucination validation
- [x] **Structured wrap-up extraction** — async LLM extraction of next actions, location, quest, level, and notes
- [x] **Daily Pick** — 3 questions → 1 suggested game with reasoning
- [x] **Analytics dashboard** (web + mobile) — play heatmap, genre/platform distribution, play session timeline
- [x] Single-user mode for personal self-hosting
- [x] Mobile: iOS, Android

### Shipped beyond v1.0

- [x] **Deep Research Recap** — LangGraph graph over local SearXNG + Ollama: bounded search/refine loops, reranked grounding (planned, Epic 25), spoiler filtering, the anti-hallucination validator as the terminal gate, and quick-recap fallback.
- [x] **Backlog Concierge** — tool-using conversational agent over the real library; an operator of the play-session pipeline (start / recap / log), with write tools gated and UUID-validated.
- [x] **Unified PlaySession pipeline** — one `start_play_session` spine; Pick, direct start, and the Concierge all funnel through it (recap is an optional stage).
- [x] **Bulk library import** — local-first OCR (Tesseract) of platform list-view/purchase-history screenshots, fuzzy-matched to a canonical catalog, with a capped cloud-vision fallback.
- [x] **Cost governance** — per-call token→$ metering, per-user/global spend kill-switch with a degraded in-process fallback (Redis-outage safe).
- [x] **Application caching layer** — `AbstractCache` port (Redis/null) with IGDB result + token caching; broader strategy in progress.
- [x] **Backoffice / admin panel** — users (ban/verify/sessions), catalogue moderation, and runtime operational config (Postgres overlay over env), every change audited.
- [x] **Social login** — Google & Twitch (Authorization Code + PKCE) on web, behind the existing auth core.
- [x] **Account recovery** — forgot / reset / change password with single-use, session-invalidating reset tokens.
- [x] **Two-factor auth (TOTP)** — authenticator-app MFA with encrypted-at-rest secrets and single-use recovery codes, behind the existing auth core.
- [x] **LLM evaluation harness** — a golden dataset with deterministic checks (grounding / spoiler-safety / mentions / JSON-validity) and a **model-agnostic LLM-as-judge calibrated against human labels** (quadratic-weighted kappa ≈ 0.83). Gates prompt/model changes via `make quality` against a committed score baseline.
- [x] **LLM observability / tracing** — a span per LLM call and per LangGraph node (tokens / latency / cost / cache-hit) with redacted prompt+completion capture for offline debugging.
- [x] **Structured operational logging** — JSON structured logs with request/trace correlation across the API and worker.
- [x] **RAG over PlaySession history** — embed each wrap-up (Ollama + pgvector) and ground the recap on the *semantically* most relevant prior sessions, scoped per `(user, game)`, behind a `recap_retrieval` flag. A recall@k A/B shows semantic surfaces buried-but-relevant context the chronological last-N misses.
- [x] **Semantic LLM cache** — a two-layer cache on capture-parse (exact Redis → semantic pgvector): near-duplicate game-name spellings the hash misses reuse the parse above a cosine threshold. A `--cache` threshold sweep reports the honest trade-off — hit-rate gain vs the false-hit rate on confusable inputs.
- [x] **Prompt-injection guardrails** — defense-in-depth over the two untrusted surfaces (Concierge chat + captures): edge sanitization (control/bidi/zero-width strip + `<user_data>` fencing), a high-precision injection detector that blocks + logs override/jailbreak/tool-abuse turns, and PII redaction on echoed output. The load-bearing layer is the deterministic tool allowlist — a hijacked prompt physically can't drive an unsafe write (adversarially tested).

### In Design / Next

- [ ] **LLM Platform Hardening** (Epics 25, 28) — eval + tracing + RAG + semantic cache + injection guardrails **shipped** (Epics 23–24, 26–27); next: research reranking and resumable batch re-inference.
- [ ] **Cloud LLM adapters** — Bedrock/Vertex behind the existing LLM port for a hosted distribution; Ollama stays the local default.
- [ ] **Apple Sign In + native iOS/Android apps** — with on-device LLMs for the fast path, backend fallback for the heavy work.

### Out of scope (deliberate)

- No Steam/PSN/Nintendo API integration — backlog imports defeat the curation premise.
- No streaks, no "you haven't played in N days", no leaderboards. The tone is neutral, not aggressive.
- No social features. Not a review site, not Backloggd.
- No achievement/trophy tracking.

### Future

- Multi-device offline sync with conflict resolution
- Push notifications (paused game reminders)
- Live Activities on iOS (play session timer)
- Plugin system for custom prompts

---

## Self-hosting

The Docker Compose setup is the recommended way to run Slate. For deploying to a VPS or PaaS, see [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) (Fly.io, Railway, Hetzner).

For Ollama model configuration and hardware requirements, see [docs/OLLAMA.md](./docs/OLLAMA.md).

---

## Development Workflow

This repo is built with AI-assisted engineering as a first-class workflow, not an afterthought:

- `CLAUDE.md` captures project architecture, safety rules, and command conventions.
- `.claude/agents/` contains role-specific agents for FastAPI, React, Flutter, architecture, testing, review, and release work.
- `.claude/skills/` captures repeatable repo-specific procedures such as API testing and Alembic migrations.
- `.mcp.json` documents MCP integration points for local development.

PRs are welcome for bug fixes, documentation, and the items on the "Future" list. For larger changes, open an issue first.

---

## License

AGPL-3.0. See [LICENSE](./LICENSE).

---

## Acknowledgements

- **IGDB** for game metadata (optional integration). A "Game data provided by IGDB.com" credit (linking to igdb.com) is shown in the web sidebar and the app's library, per IGDB's attribution requirement.
- **Ollama** team for making local LLM deployment frictionless.
- **faster-whisper** for efficient on-device speech-to-text.
