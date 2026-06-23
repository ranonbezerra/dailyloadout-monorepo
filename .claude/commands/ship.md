# /ship

Review the full diff (checking for secrets), commit, push, and create a PR. Update Linear issue status if applicable.

## Usage
```
/ship
```

## Steps

### 1. Identify context
- `git branch --show-current` -> extract issue identifier
- Detect tracker: `DL-\d+` -> Linear, `\d+` -> GitHub
- Read issue for PR context:
  - **GitHub**: `gh issue view <number> --json title`
  - **Linear**: `mcp__linear-server__get_issue` -> read title and context

### 2. Check repository state
Run in parallel:
```bash
git status
git diff --stat HEAD
git log main..HEAD --oneline
```

### 3. SECRET SCAN — CRITICAL BLOCKING STEP

Analyze ALL content to be committed:
```bash
git diff HEAD
git diff --cached
```

Look for:
- API keys: `sk-`, `pk_`, long hardcoded strings
- Complete JWT tokens
- AWS credentials: `AKIA[A-Z0-9]{16}`
- Private keys: `-----BEGIN PRIVATE KEY-----`
- URLs with passwords: `postgresql://user:pass@host`
- Files: `.env`, `*.pem`, `*.key`, `*.p8`
- Ollama tokens, IGDB secrets, Google OAuth secrets

**If ANY secret is found:**
```
SECRET DETECTED — COMMIT BLOCKED

Found potential secret in [file:line].
Resolve before continuing.
```

Only proceed if no secrets found or user confirms false positive.

### 4. Diff review
Also check for:
- Leftover `print()` debug statements
- Unresolved critical `TODO`s
- Unused imports
- Temporary files (`.DS_Store`, `*.log`)

### 5. Determine commit type

| Prefix | When |
|--------|------|
| `feat:` | New functionality |
| `fix:` | Bug fix |
| `chore:` | Build, config, CI/CD |
| `refactor:` | Refactoring without behavior change |
| `test:` | Tests only |
| `docs:` | Documentation only |

### 6. Write commit message

Format: `<type>: description`
- Main line: max 72 characters
- Imperative present tense ("add", "fix", "remove")
- Reference issue if applicable: `(#42)` for GitHub, `[DL-24]` for Linear

### 7. Stage and commit
**DO NOT use `git add .`** — add specific files:
```bash
git add <relevant files>
git commit -m "$(cat <<'EOF'
<type>: description

[optional body]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

If pre-commit hook fails: fix the problem, DO NOT use `--no-verify`.

### 8. Push
```bash
git push -u origin <current-branch>
```

### 9. Create Pull Request

**Title:** `<type>: description` (max 70 chars)

**Body:**
```markdown
## Summary
- [bullet points of main changes]

## Issue
Resolves #42 / Resolves [DL-24]

## Test plan
- [ ] pytest passing (>= 90% coverage)
- [ ] ruff + mypy clean
- [ ] biome + tsc clean (if web changes)
- [ ] flutter analyze clean (if app changes)
- [ ] [specific manual test scenario if needed]

Generated with [Claude Code](https://claude.com/claude-code)
```

```bash
gh pr create --title "<type>: description" --body "..."
```

### 10. Update Linear status (if Linear issue)
- `mcp__linear-server__list_issue_statuses` -> get "In Review" status ID
- `mcp__linear-server__save_issue` -> update state
- `mcp__linear-server__save_comment` -> add PR link as comment

### 11. Confirm

```
## Shipped!

**Commit:** <type>: description
**Branch:** feat/<id>-description
**PR:** <URL>
**Linear:** In Review (if applicable)
```

## Non-negotiable rules
- **NEVER commit secrets**
- **NEVER use `--no-verify`**
- **NEVER use `git add .`**
- **NEVER force push to main**
- **NEVER amend already-pushed commits**
