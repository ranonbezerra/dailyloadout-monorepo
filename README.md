<p align="center">
  <img src="./docs/brand/readme-hero.png" alt="DailyLoadout" width="100%" />
</p>

# DailyLoadout

> *Less deciding. More playing.* A personal gaming backlog manager with local AI. No streaks, no guilt, no Steam integration. Voice/photo/text capture, "previously on..." briefings before each session, and a 3-question daily loadout that picks one game for you.

[![CI – API](https://img.shields.io/badge/CI-API-blue)]() [![CI – App](https://img.shields.io/badge/CI-App-blue)]() [![CI – Web](https://img.shields.io/badge/CI-Web-blue)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What problem this solves

You own 60 games. You play 2. Every time you sit down, half the session is spent deciding what to play — and when you come back to a game after 3 weeks, you've forgotten where you stopped.

DailyLoadout treats the backlog as a **decision problem**, not a cataloging problem. Three ideas:

1. **Frictionless capture.** Speak "got Hollow Knight on Switch" and the app fills the metadata. No forms.
2. **Mission briefings.** Before each session, the app generates a "previously on..." paragraph from your past debriefs — like a TV show recap.
3. **Daily Loadout.** Three quick questions (mood, time, mental energy) → one suggested game with reasoning. You don't choose; the app does.

No streaks. No "X days without playing" guilt. Dropping a game is a legitimate decision, not a failure.

---

## Why this repo exists

DailyLoadout is a personal app I use daily **and** my engineering showcase. The full app is open source, runs entirely on your own hardware, and uses **local LLMs via Ollama** instead of cloud APIs.

Three things make this repo worth reading as code:

- **Local-first AI.** No OpenAI key, no Anthropic key, no cloud bill. Ollama runs Gemma/Llama locally for parsing, briefings, and loadout reasoning. Faster-Whisper runs local for speech-to-text.
- **Anti-hallucination as a feature.** Every LLM output is validated against context before being shown to the user. Briefings flag themselves as "suspicious" when output drifts too far from input. Loadout suggestions are validated against the user's actual library — UUIDs that don't exist trigger a reroll.
- **State machines for AI workflows.** Captures cross three systems (LLM, optional IGDB, user review). They're modeled as an explicit state machine (`queued → processing → review → committed/partially_committed/failed/cancelled`), making retries and partial commits safe.

---

## Quickstart

```bash
# Clone
git clone https://github.com/ranonbezerra/dailyloadout-monorepo.git
cd dailyloadout-monorepo

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
make web          # React on :3000
make app          # Flutter (macOS by default)
```

Open `http://localhost:3000` for the web dashboard, `http://localhost:8100/docs` for the API reference.

Run `make help` to see all available commands.

---

## Stack at a glance

| Package | Stack |
|---|---|
| `packages/api/` | Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2 async · PostgreSQL 18 · Redis · arq · Poetry |
| `packages/app/` | Flutter 3.27+ · BLoC · go_router · dio · faster-whisper (server-side) |
| `packages/web/` | Bun · Vite · React 19 · TypeScript · Mantine v8 · TanStack Query |
| AI | **Ollama** (Gemma 3 4B + 12B, configurable) · **faster-whisper** local |
| Infra | Docker Compose · GitHub Actions · MIT |

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
- [x] **Mission lifecycle** — start a session, write a debrief at the end
- [x] **Briefing generation** — LLM-generated "previously on..." with anti-hallucination validation
- [x] **Daily Loadout** — 3 questions → 1 suggested game with reasoning
- [x] **Analytics dashboard** (web) — play heatmap, genre distribution, mission timeline
- [x] Single-user mode for personal self-hosting
- [x] Mobile: iOS, Android

### Out of scope (deliberate)

- No Steam/PSN/Nintendo API integration — backlog imports defeat the curation premise.
- No streaks, no "you haven't played in N days", no leaderboards. The tone is neutral, not aggressive.
- No social features. Not a review site, not Backloggd.
- No achievement/trophy tracking.

### Future (issues are open)

- Multi-device offline sync with conflict resolution
- Push notifications (paused game reminders)
- Live Activities on iOS (mission timer)
- Plugin system for custom prompts

---

## Self-hosting

The Docker Compose setup is the recommended way to run DailyLoadout. For deploying to a VPS or PaaS, see [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) (Fly.io, Railway, Hetzner).

For Ollama model configuration and hardware requirements, see [docs/OLLAMA.md](./docs/OLLAMA.md).

---

## Contributing

This is primarily a personal project, but PRs are welcome for bug fixes, documentation, and the items on the "Future" list. For larger changes, open an issue first.

---

## License

MIT. See [LICENSE](./LICENSE).

---

## Acknowledgements

- **IGDB** for game metadata (optional integration). "Powered by IGDB" shown in app settings when enabled.
- **Ollama** team for making local LLM deployment frictionless.
- **faster-whisper** for efficient on-device speech-to-text.
