---
name: security-audit
description: Read-only security audit of the Slate codebase. Use when the user asks to audit, scan for vulnerabilities, do a security review, or check a specific dimension (auth, llm, injection, web, infra, data, dos, io) or the current branch diff. Orchestrates parallel read-only auditor subagents, verifies findings, and offers to implement fixes.
---

# Security Audit — Slate

Runs the versioned audit prompts in `audits/*.md` as parallel **read-only**
auditor subagents from THIS session, then synthesizes + verifies the findings.
Same prompt definitions as `make audit` (which shells out to headless `claude`
for CI/cron) — this skill is the interactive, in-session path.

## 1. Resolve scope

From the user's request:
- **No dimension named** → run ALL modules. Discover them: the module names are
  the `audits/*.md` files except `_preamble.md` and `README.md`
  (`auth llm injection web infra data dos io`).
- **Specific dimension(s) named** (e.g. "audit auth and the LLM tool boundary")
  → run only those modules.
- **"regression" / "review the diff" / "did my change introduce a vuln"** → run
  an extra ad-hoc auditor over `git diff <base>...HEAD` (base = `main` unless the
  user says otherwise), adversarial about the change itself.

Scale to the ask: a quick check = the 1–2 relevant modules; "deep/thorough/full
audit" = all modules, and prefer more finder coverage.

## 2. Dispatch auditors (parallel, read-only)

For each in-scope module, spawn one `general-purpose` subagent (run them in the
SAME message so they run concurrently; for many modules use `run_in_background`).
Build each agent's prompt as: the contents of `audits/_preamble.md` followed by
the contents of `audits/<module>.md`. Tell each agent explicitly: **read-only —
do not modify files**; return concise findings (title, severity, `file:line`,
why-exploitable, fix, confidence) plus a short "well-defended" list.

Do NOT re-implement the prompts here — read the files so the skill and
`make audit` never drift.

## 3. Synthesize + VERIFY (do this yourself, don't trust blindly)

When the auditors return:
1. Collect findings; dedupe overlaps across modules.
2. For every **exploitable** finding (High/Med), open the cited `file:line`
   yourself and confirm it's real. Drop false positives; downgrade the theoretical.
3. Produce ONE consolidated report:
   - A `VERDICT: N findings — X High, Y Med, Z Low` line.
   - Findings ordered by severity, each with the verified `file:line`, the
     concrete exploit, and the fix.
   - A "well-defended (confirmed)" list so the reader knows what was checked.
   - Note anything deferred and why.

Be honest about diminishing returns: if a dimension is clean, say so plainly.

## 4. Offer to implement

Ask before writing code (unless the user already said "audit and fix"). On
confirmation, implement on a NEW branch following repo conventions:
- Group fixes into thematic commits; conventional-commit messages; end each with
  the `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` trailer.
- Files ≤300 lines (`make api-file-sizes`); add tests for each fix.
- `make quality-api` (and `make quality-web-*` for web changes) must pass GREEN
  before pushing. Refresh `.secrets.baseline` if a migration adds secret-like
  strings. Never `git add .`, never `--no-verify`.
- One PR summarizing the verified findings, the fixes, and what was deferred.

## Modules

| Module | Focus |
| ------ | ----- |
| `auth` | authn/authz, JWT & token lifecycle, OAuth/session/MFA, IDOR, admin boundary |
| `llm` | prompt injection, agent tool boundary (LLM06), RAG/embedding (LLM08), cache poisoning |
| `injection` | SQL/ORM query construction, SSRF, command/template/path injection, input bounds |
| `web` | frontend XSS/CSRF/CSP, token storage, open redirect, bundle secrets |
| `infra` | GitHub Actions, Docker/compose, secrets hygiene, supply chain, dependency CVEs |
| `data` | logging/PII, error leakage, response over-serialization, mass-assignment |
| `dos` | rate limiting (per-IP + per-account), cost/LLM spend, resource bounds, races |
| `io` | media/upload pipeline, Redis/cache keys, Taskiq worker, email/SMTP |

## Notes
- This skill spends real tokens (one subagent per module). For a hands-off /
  scheduled run outside a session, use `make audit` instead (see `audits/README.md`).
- Add a new dimension by dropping `audits/<name>.md` — both this skill and
  `make audit-<name>` pick it up automatically.
