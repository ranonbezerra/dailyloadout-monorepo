# DailyLoadout — Agents & Skills Guide

How Claude Code uses the artifacts in this `.claude/` directory to assist with DailyLoadout development.

## Architecture

```
.claude/
├── settings.json                    # Team permissions, hooks, claudeFlow (committed)
├── settings.local.json              # Personal tokens, MCP access (gitignored)
├── dailyloadout-agents-guide.md     # This file
├── agents/                          # Specialized subagents
│   ├── fastapi-engineer.md          # Backend: FastAPI, SQLAlchemy, Alembic, Taskiq
│   ├── react-engineer.md            # Web dashboard: React, Mantine, TanStack Query
│   ├── flutter-engineer.md          # Mobile app: Flutter, BLoC, go_router, dio
│   ├── devops-engineer.md           # Infra: Docker, CI/CD, deployment, observability
│   └── dailyloadout-architect.md    # Cross-system architect (Opus model)
├── commands/                        # Slash commands (workflow automation)
│   ├── start.md                     # /start <issue-ref> — begin GitHub/Linear issue
│   ├── ship.md                      # /ship — commit, push, PR, update Linear
│   ├── new-domain.md                # /new-domain <name> — scaffold domain
│   ├── new-migration.md             # /new-migration <desc> — Alembic
│   ├── new-issue.md                 # /new-issue — create GitHub/Linear issue
│   ├── test-api.md                  # /test-api [pattern] — pytest
│   ├── coverage.md                  # /coverage [module] — coverage gaps
│   ├── lint-fix.md                  # /lint-fix — ruff + mypy + biome
│   ├── review-pr.md                 # /review-pr [#] — code review
│   └── impact-check.md             # /impact-check <change> — cross-system
└── skills/                          # Domain knowledge (auto or on-demand)
    ├── dailyloadout-conventions/    # Auto-loaded: patterns, naming, rules
    ├── alembic-migrations/          # Migration patterns, schema conventions
    └── api-testing/                 # pytest patterns, coverage targets
```

## Agents — When to Use Each

### fastapi-engineer (default for API work)
**Trigger**: implementing endpoints, services, repositories, tests, migrations, Taskiq tasks, LLM prompts
**Model**: sonnet (default)
**Scope**: `packages/api/` only

### react-engineer (for Web dashboard)
**Trigger**: implementing dashboard pages, Mantine components, TanStack Query hooks, charts
**Model**: sonnet (default)
**Scope**: `packages/web/` only

### flutter-engineer (for Mobile app)
**Trigger**: implementing screens, BLoC state management, go_router navigation, dio API calls, captures, tests
**Model**: sonnet (default)
**Scope**: `packages/app/` only

### devops-engineer (for Infrastructure)
**Trigger**: Docker, docker-compose, CI/CD, deployment, health checks, monitoring, Taskiq worker config
**Model**: sonnet (default)
**Scope**: Dockerfiles, docker-compose.yml, .github/workflows/, infra/

### dailyloadout-architect (for planning & decisions)
**Trigger**: feature planning, architecture decisions, API contract design, cross-system impact
**Model**: opus (complex reasoning)
**Scope**: read-only across entire monorepo
**Note**: Use for planning BEFORE implementation. Does not write code.

## Skills — Loading Rules

| Skill | Auto-loaded? | Load when... |
|-------|-------------|--------------|
| `dailyloadout-conventions` | YES | Always available |
| `alembic-migrations` | No | Creating/modifying migrations |
| `api-testing` | No | Writing or fixing tests |

## Slash Commands — Quick Reference

| Command | What it does |
|---------|-------------|
| `/start #42` or `/start DL-24` | Read issue (GitHub/Linear), create branch, plan, begin work |
| `/ship` | Scan for secrets, commit, push, create PR, update Linear status |
| `/new-domain capture` | Scaffold full domain (router + service + repo + schema + model + tests) |
| `/new-migration add_playtime` | Generate Alembic migration |
| `/new-issue` | Create GitHub or Linear issue interactively |
| `/test-api mission` | Run filtered pytest |
| `/coverage` | Full coverage report with gap analysis |
| `/lint-fix` | ruff format + ruff check + mypy + biome |
| `/impact-check add mood tracking` | Analyze cross-system impact |
| `/review-pr 42` | Structured code review of PR |

## Claude Flow Configuration

The `settings.json` includes a `claudeFlow` configuration that enables:

- **Agent Teams**: auto-assignment, pattern training, shared memory namespace
- **Swarm**: hierarchical-mesh topology, max 15 concurrent agents
- **Memory**: hybrid backend with HNSW indexing, memory graph, agent scopes
- **Neural**: neural network integration for pattern recognition
- **Daemon**: background workers for audit (4h) and optimize (2h) cycles
- **Learning**: auto-training on coordination, optimization, and prediction patterns
- **Security**: auto-scan on edits, CVE checking, threat modeling

## Best Practices

### Parallelism
Launch multiple Task agents in parallel when exploring unrelated systems:
```
Task(fastapi-engineer: "implement mission endpoints")
Task(react-engineer: "create mission page")
Task(flutter-engineer: "implement mission BLoC")
```

### Model Routing
- **Opus**: architecture decisions, complex planning, cross-system design
- **Sonnet**: implementation, testing, standard development
- **Haiku**: quick file lookups, simple searches via Explore

### Linear MCP Integration
- Use `/start DL-XX` to begin working on a Linear issue
- `/ship` automatically updates Linear status to "In Review" and adds PR link
- `/new-issue --linear` creates issues directly in Linear
- Read Linear comments before implementation — they may contain decisions

### Context Management
- CLAUDE.md is always loaded (project constitution)
- Skills auto-load or load on-demand based on task
- Use ARCHITECTURE.md and PRODUCT.md as references for domain questions
