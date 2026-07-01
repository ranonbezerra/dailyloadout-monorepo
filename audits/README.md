# Security audits

LLM-driven, **read-only** security audits, runnable from `make`. Each audit
module is a prompt in this directory that a headless Claude Code agent runs
against the codebase; it reads and greps only (a read-only tool allowlist, edits
disallowed) and writes a Markdown report to `audits/reports/<module>.md`.

These codify the ad-hoc security scans done during development into repeatable,
version-controlled checks. They are **advisory** — an LLM auditor, not a
deterministic gate — so treat findings as leads to verify, not build failures.

Two entry points, same prompt files:

- **`make audit`** (this doc) — headless `claude -p` subprocesses, for CI/cron or
  a hands-off run outside a session.
- **`/security-audit` skill** (`.claude/skills/security-audit/`) — the
  interactive, in-session path: orchestrates the auditors as subagents, verifies
  findings against the code, and offers to implement fixes.

## Usage

```bash
make audit              # run every module
make audit-list         # list module names
make audit-auth         # run one module (auth, llm, injection, web, infra, data, dos, io)
make audit-llm          # ... etc

# knobs
AUDIT_MODEL=opus make audit        # deeper (and pricier) than the default sonnet
AUDIT_PARALLEL=1 make audit        # run modules concurrently
AUDIT_MAX_BUDGET=5 make audit-auth # cap USD spend per module
```

Reports are written to `audits/reports/` (gitignored). Each starts with a
`VERDICT:` line summarising counts; the `make` run prints a summary table.

## Modules

| Module      | Covers |
| ----------- | ------ |
| `auth`      | authn/authz, JWT & token lifecycle, OAuth/session/MFA, IDOR, admin boundary |
| `llm`       | prompt injection, agent tool boundary (LLM06), RAG/embedding (LLM08), cache poisoning |
| `injection` | SQL/ORM query construction, SSRF, command/template/path injection, input bounds |
| `web`       | frontend XSS/CSRF/CSP, token storage, open redirect, bundle secrets |
| `infra`     | GitHub Actions, Docker/compose, secrets hygiene, supply chain, dependency CVEs |
| `data`      | logging/PII, error leakage, response over-serialization, mass-assignment |
| `dos`       | rate limiting (per-IP + per-account), cost/LLM spend, resource bounds, races |
| `io`        | media/upload pipeline, Redis/cache keys, Taskiq worker, email/SMTP |

## Adding a module

Drop a new `audits/<name>.md` prompt file — `make audit-<name>` and the `audit`
run pick it up automatically (the runner discovers `audits/*.md`). Keep the
shared output/severity rules in `_preamble.md`; put only the focus in the module
file.

## Requirements

The [`claude`](https://claude.com/claude-code) CLI on `PATH`. Runs incur API
cost (~8 agent sessions for a full `make audit`); use `AUDIT_MODEL=sonnet` (the
default) and `AUDIT_MAX_BUDGET` to bound it.
